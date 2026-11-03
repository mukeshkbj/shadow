import io
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

import shadow.api as api_mod
from shadow.api import app
from shadow.jobs import JobStore

c = TestClient(app)


def test_sample_job_end_to_end():
    assert c.get("/api/health").json()["live"] is False
    jobs = c.get("/api/jobs").json()
    assert any(j["id"] == "sample" for j in jobs)
    pb = c.get("/api/jobs/sample/playbook").json()
    assert pb["counts"]["to_confirm"] == 2
    pb = c.patch("/api/jobs/sample/steps/s4", json={"confirmed": True}).json()
    assert pb["counts"]["to_confirm"] == 1
    pb = c.post("/api/jobs/sample/questions/q2", json={"answer": "The duty manager on the rota."}).json()
    assert pb["counts"]["open_questions"] == 2
    md = c.get("/api/jobs/sample/export.md").text
    assert "Answered by the expert" in md


def test_upload_rejects_non_mp4():
    r = c.post("/api/jobs", files={"file": ("clip.mov", b"x", "video/quicktime")})
    assert r.status_code == 400


def test_job_cap_returns_429(monkeypatch):
    api_mod.store.create("occupant.mp4", io.BytesIO(b"x" * 10))
    monkeypatch.setattr(api_mod, "settings", replace(api_mod.settings, max_jobs=1))
    r = c.post("/api/jobs", files={"file": ("clip.mp4", b"x" * 10, "video/mp4")})
    assert r.status_code == 429


def test_upload_size_cap_removes_job_dir(tmp_path):
    store = JobStore(replace(api_mod.settings, data_dir=tmp_path, max_upload_mb=1))
    with pytest.raises(ValueError):
        store.create("big.mp4", io.BytesIO(b"x" * 2_000_000))
    assert all(d.name == "sample" for d in (tmp_path / "jobs").iterdir())


def test_replay_endpoints():
    d = api_mod.store.dir("sample")
    (d / "replay").mkdir(exist_ok=True)
    (d / "replay_log.json").write_text('{"title":"t","actions":[],"asked":[],"stopped":""}', encoding="utf-8")
    (d / "replay" / "step_01.png").write_bytes(b"\x89PNG")
    assert c.get("/api/jobs/sample/replay").status_code == 200
    assert c.get("/api/jobs/sample/replay/shots/step_01.png").status_code == 200
    assert c.get("/api/jobs/sample/replay/shots/..status.json").status_code == 404
    assert c.get("/api/jobs/sample/replay/shots/status.json").status_code == 404


def test_upload_needs_passcode_when_set(monkeypatch):
    from dataclasses import replace
    import shadow.api as api_mod
    monkeypatch.setattr(api_mod, "settings", replace(api_mod.settings, upload_passcode="lamp-42"))
    r = c.post("/api/jobs", files={"file": ("a.mp4", b"x", "video/mp4")}, data={"passcode": "nope"})
    assert r.status_code == 403
    assert c.get("/api/health").json()["passcode_required"] is True


def test_index_is_not_cached():
    r = c.get("/api/health")
    assert "no-cache" not in r.headers.get("cache-control", "")
    r = c.get("/")   # 404 without a built UI is fine; the header still applies to page routes
    assert r.headers.get("cache-control") == "no-cache"


def test_public_deploy_keeps_each_visitors_review_private(monkeypatch):
    monkeypatch.setattr(api_mod, "settings", replace(api_mod.settings, upload_passcode="lamp-42"))
    base = c.get("/api/jobs/sample/playbook").json()
    before = base["counts"]
    step = next(s["id"] for s in base["steps"] if s["source"] == "inferred" and not s["confirmed"])
    judge_a, judge_b = {"X-Shadow-Review": "judgeaaaa1"}, {"X-Shadow-Review": "judgebbbb2"}
    pb = c.patch(f"/api/jobs/sample/steps/{step}", json={"confirmed": True}, headers=judge_a).json()
    assert pb["counts"]["to_confirm"] == before["to_confirm"] - 1
    c.post("/api/jobs/sample/questions/q3", json={"answer": "Ask the manager."}, headers=judge_a)
    assert "Ask the manager." in c.get("/api/jobs/sample/export.md", headers=judge_a).text
    assert c.get("/api/jobs/sample/playbook", headers=judge_a).json()["counts"]["to_confirm"] == before["to_confirm"] - 1
    assert c.get("/api/jobs/sample/playbook", headers=judge_b).json()["counts"] == before
    assert c.get("/api/jobs/sample/playbook").json()["counts"] == before
    assert c.get("/api/jobs/sample/playbook", headers={"X-Shadow-Review": "../../x"}).status_code == 404
    assert c.patch(f"/api/jobs/sample/steps/{step}", json={"confirmed": True}).status_code == 400
    assert c.post("/api/jobs/sample/questions/q3", json={"answer": "x"}).status_code == 400
    assert c.get("/api/jobs/sample/playbook").json()["counts"] == before


def test_conflict_resolution_is_recorded_and_exported():
    pb = c.get("/api/jobs/sample/playbook").json()
    assert "s1" in pb["conflicts"] and pb["conflicts"]["s1"]["said"]
    assert c.patch("/api/jobs/sample/steps/s1", json={"resolution": "nonsense"}).status_code == 422
    pb = c.patch("/api/jobs/sample/steps/s1", json={"text": "Take the newest request", "resolution": "screen"}).json()
    s1 = next(s for s in pb["steps"] if s["id"] == "s1")
    assert s1["confirmed"] and s1["resolution"] == "screen" and "s1" in pb["conflicts"]
    md = c.get("/api/jobs/sample/export.md").text
    assert "The expert followed the screen" in md and "#/job/sample?t=" in md
