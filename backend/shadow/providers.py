"""Model providers for Pass 1 ("watch") and Pass 2 ("think").

- MuseProvider: Meta Model API (Responses + Files). Video is uploaded once per clip; the
  model hears the embedded audio itself (muse-spark-1.2).
- OpenProvider: Muse Spark Open on an OpenAI-compatible host (Baseten, Fireworks, Modal...).
  Hosts ignore the audio inside a video, so each clip is sent as a video part plus a separate
  WAV audio part. Clips must be short (Baseten: video <= 300 s, audio <= 5 min), so this mode
  always uses windows.
"""
import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Protocol

import httpx

from . import media
from .config import Settings
from .muse import MuseClient, MuseError


class Provider(Protocol):
    name: str
    needs_windows: bool

    def watch(self, clip: Path, prompt: str) -> str: ...
    def think(self, prompt: str) -> str: ...


class MuseProvider:
    name = "muse"
    needs_windows = False

    def __init__(self, s: Settings, transport: Optional[httpx.BaseTransport] = None):
        self.s = s
        self.client = MuseClient(s, transport=transport)
        self._uploaded: dict[Path, str] = {}  # a retry reuses the upload

    def watch(self, clip: Path, prompt: str) -> str:
        file_id = self._uploaded.get(clip) or self.client.upload(clip)
        self._uploaded[clip] = file_id
        text, _ = self.client.respond(self.s.timeline_model, prompt, file_id=file_id)
        return text

    def think(self, prompt: str) -> str:
        text, _ = self.client.respond(self.s.playbook_model, prompt)
        return text


def _data_url(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


class OpenProvider:
    name = "open"
    needs_windows = True

    def __init__(self, s: Settings, transport: Optional[httpx.BaseTransport] = None):
        if not (s.open_base_url and s.open_api_key):
            raise MuseError("Open-weights mode needs SHADOW_OPEN_BASE_URL and SHADOW_OPEN_API_KEY")
        self.s = s
        self.http = httpx.Client(base_url=s.open_base_url, transport=transport,
                                 headers={"Authorization": f"Bearer {s.open_api_key}"},
                                 timeout=httpx.Timeout(600, connect=30))

    def _chat(self, content) -> str:
        r = self.http.post("/chat/completions", json={
            "model": self.s.open_model,
            "max_tokens": self.s.max_output_tokens,
            "messages": [{"role": "user", "content": content}],
        })
        if r.status_code != 200:
            raise MuseError(f"{self.s.open_model} failed {r.status_code}: {r.text[:600]}")
        msg = r.json()["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text:
            raise MuseError(f"{self.s.open_model} returned no text. Try raising SHADOW_MAX_OUTPUT_TOKENS.")
        return text

    def watch(self, clip: Path, prompt: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            wav = media.extract_wav(clip, Path(tmp) / "audio.wav", rate=16000)
            content = [
                {"type": "text", "text": prompt},
                {"type": "video_url", "video_url": {"url": _data_url(clip, "video/mp4")}},
            ]
            if wav is not None:
                content.append({"type": "audio_url", "audio_url": {"url": _data_url(wav, "audio/wav")}})
            return self._chat(content)

    def think(self, prompt: str) -> str:
        return self._chat([{"type": "text", "text": prompt}])


def get_provider(name: str, s: Settings) -> Provider:
    if name == "open":
        return OpenProvider(s)
    return MuseProvider(s)


def available(s: Settings) -> list[str]:
    out = []
    if s.api_key:
        out.append("muse")
    if s.open_base_url and s.open_api_key:
        out.append("open")
    return out
