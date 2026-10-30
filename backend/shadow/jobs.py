"""Job store on disk: data/jobs/<id>/{video.mp4, status.json, timeline.json, playbook.json}."""
import json
import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Optional

from . import evidence, passes, pointer, providers, transcribe
from .config import Settings
from .muse import MuseClient
from .schemas import Playbook, Timeline

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
STAGES = ["uploaded", "timeline", "playbook", "evidence", "done"]


class JobStore:
    def __init__(self, s: Settings):
        self.s = s
        self.root = s.data_dir / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.ensure_sample()

    # ---------- paths and status ----------
    def dir(self, job_id: str) -> Path:
        if not job_id.replace("-", "").isalnum():
            raise KeyError(job_id)
        return self.root / job_id

    def status(self, job_id: str) -> dict:
        p = self.dir(job_id) / "status.json"
        if not p.exists():
            raise KeyError(job_id)
        return json.loads(p.read_text(encoding="utf-8"))

    def _set(self, job_id: str, **kw) -> None:
        with self._lock:
            p = self.dir(job_id) / "status.json"
            st = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
            st.update(kw, updated=time.time())
            p.write_text(json.dumps(st, indent=2), encoding="utf-8")

    def list(self) -> list[dict]:
        out = []
        for d in sorted(self.root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if (d / "status.json").exists():
                st = self.status(d.name)
                pb = self.playbook(d.name)
                if pb:
                    st["counts"] = pb.counts()
                    st["title"] = pb.title
                out.append(st)
        return out

    def playbook(self, job_id: str) -> Optional[Playbook]:
        p = self.dir(job_id) / "playbook.json"
        return Playbook.model_validate_json(p.read_text(encoding="utf-8")) if p.exists() else None

    def save_playbook(self, job_id: str, pb: Playbook) -> None:
        (self.dir(job_id) / "playbook.json").write_text(pb.model_dump_json(indent=2), encoding="utf-8")

    def timeline(self, job_id: str) -> Optional[Timeline]:
        p = self.dir(job_id) / "timeline.json"
        return Timeline.model_validate_json(p.read_text(encoding="utf-8")) if p.exists() else None

    def video(self, job_id: str) -> Optional[Path]:
        p = self.dir(job_id) / "video.mp4"
        return p if p.exists() else None

    def replay(self, job_id: str) -> Optional[dict]:
        p = self.dir(job_id) / "replay_log.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def replay_shot(self, job_id: str, name: str) -> Optional[Path]:
        if not name.startswith("step_") or not name.endswith(".png") or "/" in name or "\\" in name:
            return None
        p = self.dir(job_id) / "replay" / name
        return p if p.exists() else None

    # ---------- sample job (works with no API key and no recording) ----------
    def ensure_sample(self) -> None:
        d = self.root / "sample"
        if (d / "playbook.json").exists():
            return
        d.mkdir(parents=True, exist_ok=True)
        tl = Timeline.model_validate_json((FIXTURES / "sample_timeline.json").read_text(encoding="utf-8"))
        draft = passes.parse_playbook(json.loads((FIXTURES / "sample_playbook_draft.json").read_text(encoding="utf-8")), tl.duration)
        (d / "timeline.json").write_text(tl.model_dump_json(indent=2), encoding="utf-8")
        self.save_playbook("sample", evidence.check(draft, tl, self.s.evidence_slack))
        sample_video = FIXTURES / "sample.mp4"
        if sample_video.exists():
            (d / "video.mp4").write_bytes(sample_video.read_bytes())
        self._set("sample", id="sample", filename="sample (synthetic refund walkthrough)", stage="done",
                  state="done", detail="", sample=True, created=time.time())

    # ---------- running a job ----------
    def create(self, filename: str, data_stream, provider: str = "muse") -> str:
        job_id = uuid.uuid4().hex[:12]
        d = self.dir(job_id)
        d.mkdir(parents=True)
        limit = self.s.max_upload_mb * 1_000_000
        size = 0
        try:
            with open(d / "video.mp4", "wb") as f:
                while chunk := data_stream.read(1 << 20):
                    size += len(chunk)
                    if size > limit:
                        raise ValueError(f"File exceeds the {self.s.max_upload_mb} MB upload limit.")
                    f.write(chunk)
        except Exception:
            shutil.rmtree(d, ignore_errors=True)
            raise
        self._set(job_id, id=job_id, filename=filename, provider=provider, stage="uploaded",
                  state="running", detail="", created=time.time())
        threading.Thread(target=self._run, args=(job_id, provider), daemon=True).start()
        return job_id

    def _run(self, job_id: str, provider_name: str = "muse") -> None:
        d = self.dir(job_id)
        video = d / "video.mp4"
        notes: list[str] = []
        try:
            if provider_name not in providers.available(self.s):
                raise RuntimeError("This mode isn't configured on the server (set MODEL_API_KEY, or "
                                   "SHADOW_OPEN_BASE_URL + SHADOW_OPEN_API_KEY for open weights).")
            provider = providers.get_provider(provider_name, self.s)
            meta = MuseClient(self.s) if self.s.api_key else None

            self._set(job_id, stage="timeline", detail="watching and listening")
            tl = passes.build_timeline(provider, video, d, self.s, lambda msg: self._set(job_id, detail=msg))

            if meta and self.s.use_transcribe:
                self._set(job_id, detail="transcribing the narration")
                try:
                    turns = transcribe.narration_turns(meta, video, d, self.s.transcribe_model)
                    tl.turns = turns or []
                    transcribe.align_said_events(tl)
                except Exception as e:
                    notes.append(f"Narration transcript unavailable, so “Said” steps were checked against the timeline only ({str(e)[:120]}).")
            (d / "timeline.json").write_text(tl.model_dump_json(indent=2), encoding="utf-8")

            self._set(job_id, stage="playbook", detail=f"{len(tl.events)} moments found")
            draft = passes.build_playbook(provider, tl, d, self.s)
            (d / "playbook_draft.json").write_text(draft.model_dump_json(indent=2), encoding="utf-8")

            self._set(job_id, stage="evidence", detail="checking every step against the recording")
            pb = evidence.check(draft, tl, self.s.evidence_slack)

            if meta and self.s.use_pointer:
                self._set(job_id, detail="adding visual pointers")
                notes += pointer.add_pointers(meta, video, pb, d, self.s.sam_model, self.s.locate_model)

            pb.notes = pb.notes + notes
            self.save_playbook(job_id, pb)
            self._set(job_id, stage="done", state="done", detail="")
        except Exception as e:  # surface the error in the UI rather than failing silently
            (d / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            self._set(job_id, state="error", detail=str(e)[:500])
