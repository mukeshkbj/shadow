"""Runs the passes against fake Meta / open-weights APIs and a generated video."""
import json
import shutil
import subprocess
import time
from dataclasses import replace

import httpx
import pytest

from shadow import evidence, passes, pointer, providers, transcribe
from shadow.config import Settings
from shadow.muse import MuseClient
from shadow.schemas import Event, Playbook, Step, Timeline, Turn

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")

TIMELINE_REPLY = lambda n: {"duration": 30, "transcript": f"clip {n}",
                            "events": [{"t": 5, "source": "seen", "action": f"click {n}", "field": "Search"},
                                       {"t": 6, "source": "said", "quote": f"I always check thing {n}"},
                                       {"t": 99, "source": "seen", "action": "bogus time"}]}
PLAYBOOK_REPLY = {"title": "Fake task", "steps": [
    {"id": "s1", "t_start": 5, "text": "Click search", "source": "seen", "evidence_event_ids": ["e1"], "field": "Search"},
    {"id": "s2", "t_start": 36, "text": "Check thing 2", "source": "said", "quote": "I always check thing 2"},
    {"id": "s3", "t_start": 50, "text": "Invented step", "source": "seen"}],
    "decisions": [], "open_questions": []}


def make_video(path, seconds=70, audio=True):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=size=320x240:rate=10:duration={seconds}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "aac", "-shortest"]
    subprocess.run(cmd + ["-c:v", "libx264", "-preset", "ultrafast", str(path)], check=True)


def fake_meta():
    calls = {"uploads": 0, "responses": [], "transcribe": 0, "sam": 0}

    def handler(req: httpx.Request):
        path = req.url.path
        if path.endswith("/files"):
            calls["uploads"] += 1
            return httpx.Response(200, json={"id": f"file-{calls['uploads']}"})
        if path.endswith("/asr/transcribe"):
            calls["transcribe"] += 1
            assert b'"audioEncoding": "WAV"' in req.content
            return httpx.Response(200, json={"transcript": "...", "turns": [
                {"turnId": 1, "startMs": 35000, "endMs": 38000, "transcript": "I always check thing 2", "speaker": ""}]})
        body = json.loads(req.content)
        calls["responses"].append(body)
        if body["model"] == "sam-3.1":
            calls["sam"] += 1
            assert body["input"][0]["content"][0]["text"].startswith("<0f>0<|box;x1=12;")   # box prompt from Spark
            text = "<0f>0<|box;x1=10;y1=20;x2=110;y2=60;w=320;h=240|><|mask;x=0;y=0;data=4,4,~abc|>"
        elif body["model"] == "muse-spark-1.3":
            calls["locate"] = calls.get("locate", 0) + 1
            text = '{"found": true, "x1": 12, "y1": 22, "x2": 108, "y2": 58}'
        else:
            assert body["max_output_tokens"] >= 4000
            prompt = body["input"][0]["content"][0]["text"]
            if "LOG WHAT HAPPENED" in prompt:
                # first answer for clip 2 is broken JSON, to exercise the retry
                n = calls["uploads"]
                if n == 2 and "not valid JSON" not in prompt:
                    text = "Sure! Here is the log: {broken"
                else:
                    text = "```json\n" + json.dumps(TIMELINE_REPLY(n)) + "\n```"
            else:
                text = json.dumps(PLAYBOOK_REPLY)
        return httpx.Response(200, json={"output": [{"content": [{"type": "output_text", "text": text}]}], "usage": {}})

    return calls, httpx.MockTransport(handler)


def test_windowed_pipeline_with_transcript_and_pointer(tmp_path):
    video = tmp_path / "v.mp4"
    make_video(video)
    s = replace(Settings(), api_key="test", window_seconds=30)
    calls, transport = fake_meta()
    prov = providers.MuseProvider(s, transport=transport)

    tl = passes.build_timeline(prov, video, tmp_path, s, lambda m: None)
    assert calls["uploads"] == 3                                   # 0-30, 30-60, 60-70
    assert [e.t for e in tl.events if e.source == "seen"] == [5, 35, 65]   # window offsets applied
    assert all(e.action != "bogus time" for e in tl.events)        # time outside its clip dropped
    assert (tmp_path / "pass1_raw_002.retry.txt").exists()         # broken JSON was retried

    meta = MuseClient(s, transport=transport)
    tl.turns = transcribe.narration_turns(meta, video, tmp_path, s.transcribe_model)
    assert calls["transcribe"] == 1 and tl.turns[0].start == 35.0

    draft = passes.build_playbook(prov, tl, tmp_path, s)
    pb = evidence.check(draft, tl)
    assert [st.id for st in pb.steps] == ["s1", "s2"]
    assert pb.steps[1].source == "said" and pb.steps[1].quote_check.start == 35.0
    assert any("Invented step" in q.question for q in pb.open_questions)

    notes = pointer.add_pointers(meta, video, pb, tmp_path, s.sam_model, s.locate_model)
    assert notes == [] and calls["sam"] == 2 and calls["locate"] == 2   # Spark locates, SAM refines
    assert pb.steps[0].pointer.x1 == 10 and pb.steps[0].pointer.w == 320


def test_transcript_disagreement_downgrades_said():
    tl = Timeline(duration=100, events=[Event(id="e1", t=40, source="said", quote="over five hundred goes to my manager")],
                  turns=[Turn(start=10, end=14, text="something else entirely")])
    pb = Playbook(title="t", steps=[Step(id="s1", t_start=40, text="Approval", source="said",
                                         quote="over five hundred goes to my manager")])
    out = evidence.check(pb, tl)
    assert out.steps[0].source == "inferred" and out.steps[0].quote == ""
    assert "transcript" in out.steps[0].downgraded_reason


def test_open_weights_provider_sends_video_and_audio_parts(tmp_path):
    video = tmp_path / "v.mp4"
    make_video(video, seconds=40)
    seen = []

    def handler(req: httpx.Request):
        body = json.loads(req.content)
        assert req.url.path.endswith("/chat/completions") and body["model"] == s.open_model
        parts = body["messages"][0]["content"]
        seen.append([p["type"] for p in parts])
        text = parts[0]["text"]
        reply = TIMELINE_REPLY(len(seen)) if "LOG WHAT HAPPENED" in text else PLAYBOOK_REPLY
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reply)}}]})

    s = replace(Settings(), open_base_url="https://example.test/v1", open_api_key="k", window_seconds=0)
    prov = providers.OpenProvider(s, transport=httpx.MockTransport(handler))
    tl = passes.build_timeline(prov, video, tmp_path, s, lambda m: None)
    assert seen[0] == ["text", "video_url", "audio_url"]           # audio sent separately
    assert len(seen) == 2                                          # open mode forces 30 s windows
    pb = passes.build_playbook(prov, tl, tmp_path, s)
    assert pb.title == "Fake task"


def test_box_parse():
    assert pointer.parse_first_box("<3f>7<|box;x1=1;y1=2;x2=3;y2=4;w=5;h=6;c=0.9|>") == (1, 2, 3, 4, 5, 6)
    assert pointer.parse_first_box("") is None


def test_job_runs_end_to_end(tmp_path, monkeypatch):
    """JobStore._run with fake transports injected: status goes to done and the playbook is saved."""
    from shadow import jobs
    video = tmp_path / "in.mp4"
    make_video(video, seconds=40)
    calls, transport = fake_meta()
    s = replace(Settings(), api_key="test", window_seconds=0, data_dir=tmp_path / "data")
    monkeypatch.setattr(jobs.providers, "get_provider", lambda name, st: providers.MuseProvider(st, transport=transport))
    real_client = jobs.MuseClient
    monkeypatch.setattr(jobs, "MuseClient", lambda st: real_client(st, transport=transport))
    store = jobs.JobStore(s)
    with open(video, "rb") as f:
        job_id = store.create("in.mp4", f, "muse")
    for _ in range(100):
        st = store.status(job_id)
        if st["state"] != "running":
            break
        time.sleep(0.1)
    assert st["state"] == "done", (store.dir(job_id) / "error.txt").read_text() if st["state"] == "error" else st
    pb = store.playbook(job_id)
    assert pb.title == "Fake task" and calls["transcribe"] == 1
