from fastapi.testclient import TestClient

from shadow.api import app

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
