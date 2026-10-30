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
