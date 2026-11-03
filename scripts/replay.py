"""Replay a confirmed playbook on the demo prop, with an agent driving the browser.

    python scripts/replay.py <job_id_or_playbook.json> [--url PATH_OR_URL] [--headless] [--auto]

Needs: pip install playwright && playwright install chromium, and MODEL_API_KEY set.
--auto answers every expert prompt with "s" (skip) so the run never blocks.
Screenshots land in the job's replay/ folder alongside replay_log.json.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from shadow.config import settings  # noqa: E402
from shadow.muse import MuseClient  # noqa: E402
from shadow.replay import run  # noqa: E402
from shadow.schemas import Playbook  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("job", help="job id under backend/data/jobs, or a path to a playbook.json")
ap.add_argument("--url", default=str(ROOT / "demo-prop" / "index.html"),
                help="app to drive (default: the demo prop)")
ap.add_argument("--headless", action="store_true")
ap.add_argument("--auto", action="store_true", help="answer every expert prompt with 's' (skip)")
ap.add_argument("--provider", default="muse", choices=["muse", "open"],
                help="muse = Muse Spark 1.3 on the Meta Model API; open = Muse Spark Open on SHADOW_OPEN_BASE_URL")
a = ap.parse_args()

pb_path = Path(a.job)
if not pb_path.exists():
    pb_path = ROOT / "backend" / "data" / "jobs" / a.job / "playbook.json"
pb = Playbook.model_validate_json(pb_path.read_text(encoding="utf-8"))
work = pb_path.parent

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("pip install playwright && playwright install chromium")

url = a.url if "://" in a.url else Path(a.url).resolve().as_uri()
if a.provider == "open":
    from shadow.providers import OpenChatClient  # noqa: E402
    client, model = OpenChatClient(settings), settings.open_model
else:
    client, model = MuseClient(settings), settings.locate_model

def cli_ask(q: str) -> str:
    if a.auto:
        print(f"? {q}\n> s (auto)")
        return "s"
    try:
        return input(f"\n? {q}\n> ")
    except EOFError:
        return ""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=a.headless)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(url)
    log = run(client, page, pb, work, ask=cli_ask, model=model)
    browser.close()

n_ok = sum(1 for x in log["actions"] if x.get("ok"))
print(f"\nDone: {n_ok} actions · {len(log['asked'])} asked · stopped: {log['stopped'] or 'no'}")
print(f"Log + screenshots: {work / 'replay'}")
