"""FastAPI app. Run: uvicorn shadow.api:app --reload  (from the backend folder)."""
import hmac
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import exporters, providers
from .config import settings
from .jobs import STAGES, JobStore

app = FastAPI(title="Shadow")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
store = JobStore(settings)


def _pb(job_id: str):
    try:
        pb = store.playbook(job_id)
    except KeyError:
        pb = None
    if pb is None:
        raise HTTPException(404, "playbook not ready")
    return pb


@app.get("/api/health")
def health():
    return {"live": settings.live, "providers": providers.available(settings),
            "timeline_model": settings.timeline_model, "playbook_model": settings.playbook_model,
            "open_model": settings.open_model if settings.open_base_url else None,
            "window_seconds": settings.window_seconds,
            "transcribe": settings.live and settings.use_transcribe, "pointer": settings.live and settings.use_pointer,
            "passcode_required": bool(settings.upload_passcode)}


@app.get("/api/jobs")
def list_jobs():
    return store.list()


@app.post("/api/jobs")
def create_job(file: UploadFile, provider: str = Form("muse"), passcode: str = Form("")):
    if settings.upload_passcode and not hmac.compare_digest(passcode.strip(), settings.upload_passcode):
        raise HTTPException(403, "Wrong passcode. Uploads are limited because each one uses API credits; the sample playbooks are open to everyone.")
    if not (file.filename or "").lower().endswith(".mp4"):
        raise HTTPException(400, "Please upload an MP4 (the Meta API accepts video/mp4 only).")
    if provider not in ("muse", "open"):
        raise HTTPException(400, "provider must be 'muse' or 'open'")
    if settings.max_upload_mb and file.size and file.size > settings.max_upload_mb * 1_000_000:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_mb} MB upload limit.")
    if settings.max_jobs and len([j for j in store.list() if not j.get("sample")]) >= settings.max_jobs:
        raise HTTPException(429, "This demo has reached its upload limit. The sample playbook is always available.")
    try:
        job_id = store.create(file.filename or "recording.mp4", file.file, provider)
    except ValueError as e:
        raise HTTPException(413, str(e))
    return {"id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    try:
        st = store.status(job_id)
    except KeyError:
        raise HTTPException(404, "no such job")
    st["stages"] = STAGES
    st["has_video"] = store.video(job_id) is not None
    return st


@app.get("/api/jobs/{job_id}/playbook")
def get_playbook(job_id: str):
    pb = _pb(job_id)
    return {**pb.model_dump(), "counts": pb.counts()}


@app.get("/api/jobs/{job_id}/timeline")
def get_timeline(job_id: str):
    tl = store.timeline(job_id)
    if tl is None:
        raise HTTPException(404, "timeline not ready")
    return tl


class StepEdit(BaseModel):
    confirmed: Optional[bool] = None
    text: Optional[str] = None


@app.patch("/api/jobs/{job_id}/steps/{step_id}")
def edit_step(job_id: str, step_id: str, edit: StepEdit):
    pb = _pb(job_id)
    step = next((s for s in pb.steps if s.id == step_id), None)
    if step is None:
        raise HTTPException(404, "no such step")
    if edit.text is not None and edit.text.strip():
        step.text = edit.text.strip()
        step.confirmed = True  # the expert wrote it, so it's theirs
    if edit.confirmed is not None:
        step.confirmed = edit.confirmed
    store.save_playbook(job_id, pb)
    return {**pb.model_dump(), "counts": pb.counts()}


class Answer(BaseModel):
    answer: str


@app.post("/api/jobs/{job_id}/questions/{qid}")
def answer_question(job_id: str, qid: str, body: Answer):
    pb = _pb(job_id)
    q = next((q for q in pb.open_questions if q.id == qid), None)
    if q is None:
        raise HTTPException(404, "no such question")
    q.answer = body.answer.strip()
    store.save_playbook(job_id, pb)
    return {**pb.model_dump(), "counts": pb.counts()}


@app.get("/api/jobs/{job_id}/export.md", response_class=PlainTextResponse)
def export_md(job_id: str):
    return exporters.markdown(_pb(job_id))


@app.get("/api/jobs/{job_id}/export.mmd", response_class=PlainTextResponse)
def export_mermaid(job_id: str):
    return exporters.mermaid(_pb(job_id))


@app.get("/api/jobs/{job_id}/replay")
def get_replay(job_id: str):
    try:
        log = store.replay(job_id)
    except KeyError:
        log = None
    if log is None:
        raise HTTPException(404, "no replay for this job")
    return log


@app.get("/api/jobs/{job_id}/replay/shots/{name}")
def replay_shot(job_id: str, name: str):
    try:
        p = store.replay_shot(job_id, name)
    except KeyError:
        p = None
    if p is None:
        raise HTTPException(404, "no such replay screenshot")
    return FileResponse(p, media_type="image/png")


@app.get("/api/jobs/{job_id}/video")
def video(job_id: str):
    try:
        p = store.video(job_id)
    except KeyError:
        p = None
    if p is None:
        raise HTTPException(404, "no video for this job")
    return FileResponse(p, media_type="video/mp4")


_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
