import json
import os
import sys
import time

import requests

_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.exists(_env):  # same .env the app uses; a real env var wins
    for _line in open(_env, encoding="utf-8"):
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))

BASE_URL = "https://api.meta.ai/v1"
API_KEY = os.environ["MODEL_API_KEY"]
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

PROMPT = """You are analyzing a screen recording with narration.
Return JSON only, no markdown fences:
{
  "actions": [{"t": <seconds into video>, "action": "<what the person did>", "field": "<UI field or element>"}],
  "transcript": "<verbatim narration>",
  "video_duration_seconds": <number>
}"""


def upload(path):
    with open(path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/files",
            headers=HEADERS,
            files={"file": (os.path.basename(path), f, "video/mp4")},
            data={"purpose": "user_data"},
            timeout=300,
        )
    if r.status_code != 200:
        print(f"UPLOAD FAILED {r.status_code}: {r.text[:500]}")
        sys.exit(1)
    return r.json()["id"]


def probe(file_id, model):
    start = time.time()
    r = requests.post(
        f"{BASE_URL}/responses",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={
            "model": model,
            "max_output_tokens": 8000,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT},
                        {"type": "input_file", "file_id": file_id},
                    ],
                }
            ],
        },
        timeout=600,
    )
    elapsed = time.time() - start
    print(f"\n===== {model} ({elapsed:.0f}s) status={r.status_code} =====")
    if r.status_code != 200:
        print(r.text[:1000])
        return
    body = r.json()
    for item in body.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                print(part["text"][:4000])
    usage = body.get("usage")
    if usage:
        print(f"usage: {json.dumps(usage)}")


def main():
    path = sys.argv[1]
    models = sys.argv[2:] or ["muse-spark-1.2", "muse-wonder-1.0"]
    size_mb = os.path.getsize(path) / 1e6
    print(f"uploading {path} ({size_mb:.1f} MB)")
    file_id = upload(path)
    print(f"file_id={file_id}")
    for m in models:
        probe(file_id, m)


if __name__ == "__main__":
    main()
