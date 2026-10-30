"""Minimal client for the Meta Model API (Responses + Files), matching scripts/probe.py."""
import json
import re
from pathlib import Path
from typing import Any, Optional

import httpx

from .config import Settings


class MuseError(RuntimeError):
    pass


class MuseClient:
    def __init__(self, s: Settings, transport: Optional[httpx.BaseTransport] = None):
        if not s.api_key:
            raise MuseError("MODEL_API_KEY is not set")
        self.s = s
        self.http = httpx.Client(
            base_url=s.base_url,
            headers={"Authorization": f"Bearer {s.api_key}"},
            timeout=httpx.Timeout(600, connect=30),
            transport=transport,
        )

    def upload(self, path: Path, mime: str = "video/mp4") -> str:
        with open(path, "rb") as f:
            r = self.http.post("/files", files={"file": (path.name, f, mime)}, data={"purpose": "user_data"})
        if r.status_code != 200:
            raise MuseError(f"upload failed {r.status_code}: {r.text[:400]}")
        return r.json()["id"]

    def respond(self, model: str, text: str, file_id: Optional[str] = None,
                reasoning: Optional[str] = None) -> tuple[str, dict]:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
        if file_id:
            content.append({"type": "input_file", "file_id": file_id})
        extra = {"reasoning": {"effort": reasoning}} if reasoning else {}
        text_out, data = self.respond_parts(model, content, **extra)
        if not text_out:
            # Most common cause: reasoning used the whole output budget.
            raise MuseError(f"{model} returned no text (status: {data.get('status')}, "
                            f"incomplete: {data.get('incomplete_details')}). Try raising SHADOW_MAX_OUTPUT_TOKENS.")
        return text_out, data.get("usage", {})

    def respond_parts(self, model: str, content: list[dict[str, Any]], **extra) -> tuple[str, dict]:
        body: dict[str, Any] = {
            "model": model,
            "max_output_tokens": self.s.max_output_tokens,
            "input": [{"type": "message", "role": "user", "content": content}],
            **extra,
        }
        r = self.http.post("/responses", json=body)
        if r.status_code != 200:
            raise MuseError(f"{model} failed {r.status_code}: {r.text[:600]}")
        data = r.json()
        out = []
        for item in data.get("output", []):
            for part in item.get("content", []) or []:
                if part.get("type") == "output_text":
                    out.append(part.get("text", ""))
        return "".join(out).strip(), data

    def transcribe(self, wav: Path, model: str, mode: str = "ENDPOINTING") -> dict:
        req = {"model": model, "audioEncoding": "WAV", "mode": mode}
        with open(wav, "rb") as f:
            r = self.http.post("/asr/transcribe", headers={"Accept": "application/json"}, files={
                "request": (None, json.dumps(req), "application/json"),
                "audio": (wav.name, f, "audio/wav"),
            })
        if r.status_code != 200:
            raise MuseError(f"transcribe failed {r.status_code}: {r.text[:400]}")
        return r.json()


def extract_json(text: str) -> Any:
    """Parse JSON from a model reply, tolerating code fences and leading prose."""
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if fence:
        t = fence.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    start = min([i for i in (t.find("{"), t.find("[")) if i != -1], default=-1)
    if start == -1:
        raise ValueError("no JSON found in model output")
    opener = t[start]
    closer = "}" if opener == "{" else "]"
    end = t.rfind(closer)
    return json.loads(t[start:end + 1])
