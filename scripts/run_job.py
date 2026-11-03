"""Run the full pipeline on a recording from the command line, one stage per call if needed.

    python scripts/run_job.py recordings/take-a.mp4 [job_id] [--provider muse|open]

Each stage saves its output into backend/data/jobs/<job_id>/ and is skipped next time,
so the command can simply be re-run if it stops part-way. The finished job appears in the UI.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from shadow import evidence, passes, pointer, providers, transcribe  # noqa: E402
from shadow.config import settings  # noqa: E402
from shadow.jobs import JobStore  # noqa: E402
from shadow.muse import MuseClient  # noqa: E402
from shadow.schemas import Playbook, Timeline  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("job_id", nargs="?")
ap.add_argument("--provider", default="muse")
ap.add_argument("--only", help="stop after this stage: timeline|transcribe|playbook|evidence|pointers")
ap.add_argument("--redo", help="re-run from this stage onward (overwrites its output)")
a = ap.parse_args()

store = JobStore(settings)
job_id = a.job_id or Path(a.video).stem.replace("_", "-").replace(".", "-")
d = store.root / job_id
d.mkdir(parents=True, exist_ok=True)
if not (d / "video.mp4").exists():
    shutil.copy(a.video, d / "video.mp4")
store._set(job_id, id=job_id, filename=Path(a.video).name, provider=a.provider, state="running", created=time.time())
log = lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
prov = providers.get_provider(a.provider, settings)
meta = MuseClient(settings) if settings.api_key else None
video = d / "video.mp4"

ORDER = ["timeline", "transcribe", "playbook", "evidence", "pointers"]
redo_from = ORDER.index(a.redo) if a.redo else len(ORDER)

def stage(name, out, fn):
    if (d / out).exists() and ORDER.index(name) < redo_from:
        log(f"{name}: already done")
        return
    t = time.time(); store._set(job_id, stage=name, detail=name)
    fn(); log(f"{name}: done in {time.time() - t:.0f}s")
    if a.only == name:
        sys.exit(0)

def do_timeline():
    turns = None
    if not getattr(prov, "hears_audio", True) and meta:
        turns = transcribe.narration_turns(meta, video, d, settings.transcribe_model)
        log(f"{prov.name} can't hear audio: giving it {len(turns or [])} transcribed narration turns as text")
    tl = passes.build_timeline(prov, video, d, settings, log, turns=turns)
    (d / "timeline_raw.json").write_text(tl.model_dump_json(indent=2), encoding="utf-8")

def do_transcribe():
    tl = Timeline.model_validate_json((d / "timeline_raw.json").read_text(encoding="utf-8"))
    if meta and settings.use_transcribe:
        tl.turns = transcribe.narration_turns(meta, video, d, settings.transcribe_model) or []
        log(f"aligned {transcribe.align_said_events(tl)} spoken events to transcript turns")
    (d / "timeline.json").write_text(tl.model_dump_json(indent=2), encoding="utf-8")

def do_playbook():
    tl = Timeline.model_validate_json((d / "timeline.json").read_text(encoding="utf-8"))
    draft = passes.build_playbook(prov, tl, d, settings)
    (d / "playbook_draft.json").write_text(draft.model_dump_json(indent=2), encoding="utf-8")

def do_evidence():
    tl = Timeline.model_validate_json((d / "timeline.json").read_text(encoding="utf-8"))
    draft = Playbook.model_validate_json((d / "playbook_draft.json").read_text(encoding="utf-8"))
    (d / "playbook_checked.json").write_text(evidence.check(draft, tl, settings.evidence_slack).model_dump_json(indent=2), encoding="utf-8")

def do_pointers():
    pb = Playbook.model_validate_json((d / "playbook_checked.json").read_text(encoding="utf-8"))
    if meta and settings.use_pointer:
        pb.notes += pointer.add_pointers(meta, video, pb, d, settings.sam_model, settings.locate_model)
    store.save_playbook(job_id, pb)

stage("timeline", "timeline_raw.json", do_timeline)
stage("transcribe", "timeline.json", do_transcribe)
stage("playbook", "playbook_draft.json", do_playbook)
stage("evidence", "playbook_checked.json", do_evidence)
stage("pointers", "playbook.json", do_pointers)
store._set(job_id, stage="done", state="done", detail="")
pb = store.playbook(job_id)
print(json.dumps(pb.counts()))
for s in pb.steps:
    print(f"  {s.t_start:6.1f}s  {s.source:8s} {'Q' if s.quote_check else ' '} {'P' if s.pointer else ' '}  {s.text}")
for q in pb.open_questions:
    print(f"  ? {q.question}")
for n in pb.notes:
    print(f"  note: {n}")
