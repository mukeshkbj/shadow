from pathlib import Path

from shadow import passes
from shadow.config import Settings
from shadow.schemas import Turn


class DeafProvider:
    name = "open"
    needs_windows = False
    hears_audio = False

    def __init__(self):
        self.prompts = []

    def watch(self, clip, prompt):
        self.prompts.append(prompt)
        return '{"duration": 10, "transcript": "", "events": [{"t": 3, "source": "said", "action": "rule", "quote": "over 500 pounds"}]}'


def test_deaf_provider_gets_transcript_as_text(tmp_path, monkeypatch):
    monkeypatch.setattr(passes.media, "duration", lambda p: 10.0)
    prov = DeafProvider()
    turns = [Turn(start=2.5, end=4.0, text="Anything over 500 pounds goes to my manager.")]
    tl = passes.build_timeline(prov, Path("x.mp4"), tmp_path, Settings(window_seconds=0), lambda m: None, turns=turns)
    assert "[2.5s] Anything over 500 pounds" in prov.prompts[0]
    assert tl.events and tl.events[0].source == "said"


def test_open_chat_client_maps_parts():
    import json as _json
    from dataclasses import replace
    import httpx
    from shadow.providers import OpenChatClient
    seen = {}

    def handler(req):
        seen["body"] = _json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"action": "none"}'}}]})

    s = replace(Settings(), open_base_url="https://example.test/v1", open_api_key="k")
    c = OpenChatClient(s, httpx.MockTransport(handler))
    text, _ = c.respond_parts("m", [{"type": "input_text", "text": "hi"}, {"type": "input_image", "image_url": "data:image/png;base64,AA"}])
    assert text == '{"action": "none"}'
    assert [p["type"] for p in seen["body"]["messages"][0]["content"]] == ["text", "image_url"]
