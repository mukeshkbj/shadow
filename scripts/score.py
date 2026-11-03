"""Score a job's timestamps against a scripted recording's ground truth.

    python scripts/score.py <job_id> recordings/<take>.ground_truth.json

Screen actions: nearest "seen" event in Muse Spark's raw timeline.
Spoken lines: nearest "said" event, raw (Muse Spark) and after snapping to Voice Transcribe turns.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
job, gt_path = sys.argv[1], Path(sys.argv[2])
d = ROOT / "backend" / "data" / "jobs" / job
gt = json.loads(gt_path.read_text())
raw = json.loads((d / "timeline_raw.json").read_text())["events"]
aligned = json.loads((d / "timeline.json").read_text())["events"]


def errs(truth, guesses):
    return [min(abs(t - g) for g in guesses) for t in truth] if guesses else []


def row(name, e):
    print(f"{name:<34} avg {sum(e) / len(e):5.2f} s   worst {max(e):5.2f} s   (n={len(e)})")


acts = [t for t, what in gt["act"] if what.split()[0] in ("click", "type", "select", "choose")]
says = [s[0] for s in gt["say"]]
row("screen actions (Muse Spark)", errs(acts, [e["t"] for e in raw if e["source"] == "seen"]))
row("spoken lines, raw (Muse Spark)", errs(says, [e["t"] for e in raw if e["source"] == "said"]))
row("spoken lines, snapped (Transcribe)", errs(says, [e["t"] for e in aligned if e["source"] == "said"]))
