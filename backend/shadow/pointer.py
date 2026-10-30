"""Visual pointer: outline the on-screen element a step refers to.

Two models, one job each (found in testing: SAM segments objects but can't read text labels):
  1. Muse Spark reads the screenshot and returns a rough box for the element with that label.
  2. SAM 3.1 takes that box as a prompt and returns a precise outline of the element.
A pointer helps the reviewer find the field. It is NOT evidence: the timestamped recording is.
Failures are non-fatal; the step simply has no pointer.
"""
import base64
import re
from pathlib import Path
from typing import Optional

from . import media
from .muse import MuseClient, extract_json
from .schemas import Playbook, Pointer

BOX = re.compile(r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)")

LOCATE = ('This is a {w}x{h} screenshot of an app. Find the on-screen element labelled "{label}" '
          '(the input, dropdown, list item or button itself, not just its label text). '
          'Return JSON only: {{"found": true|false, "x1": int, "y1": int, "x2": int, "y2": int}} in pixels of this image.')


def parse_first_box(text: str) -> Optional[tuple[int, ...]]:
    m = BOX.search(text or "")
    return tuple(int(x) for x in m.groups()) if m else None


def locate(client: MuseClient, model: str, image_url: str, label: str, w: int, h: int) -> Optional[tuple[int, int, int, int]]:
    text, _ = client.respond_parts(model, [
        {"type": "input_text", "text": LOCATE.format(w=w, h=h, label=label)},
        {"type": "input_image", "image_url": image_url},
    ])
    try:
        r = extract_json(text)
    except ValueError:
        return None
    if not r.get("found"):
        return None
    x1, y1, x2, y2 = (int(r[k]) for k in ("x1", "y1", "x2", "y2"))
    # SAM rejects boxes touching the frame edge ("lies outside the image"), so keep a 1 px margin.
    x1, x2 = sorted((max(1, min(w - 2, x1)), max(1, min(w - 2, x2))))
    y1, y2 = sorted((max(1, min(h - 2, y1)), max(1, min(h - 2, y2))))
    return (x1, y1, x2, y2) if x2 - x1 > 3 and y2 - y1 > 3 else None


def refine(client: MuseClient, model: str, image_url: str, box: tuple[int, int, int, int], w: int, h: int) -> Optional[tuple[int, ...]]:
    x1, y1, x2, y2 = box
    prompt = f"<0f>0<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={w};h={h}|>"
    text, _ = client.respond_parts(model, [
        {"type": "input_text", "text": prompt},
        {"type": "input_image", "image_url": image_url},
    ])
    return parse_first_box(text)


def add_pointers(client: MuseClient, video: Path, pb: Playbook, work: Path, sam_model: str,
                 locate_model: str = "muse-spark-1.3") -> list[str]:
    notes = []
    for step in pb.steps:
        if not step.field:
            continue
        t = step.t_start + 0.5 if step.t_end is None else min(step.t_start + 0.5, step.t_end)
        try:
            frame = media.frame_at(video, max(0.0, t), work / "frames" / f"{step.id}.jpg")
            w, h = media.frame_size(frame)
            url = "data:image/jpeg;base64," + base64.b64encode(frame.read_bytes()).decode()
            rough = locate(client, locate_model, url, step.field, w, h)
            if not rough:
                continue
            fine = refine(client, sam_model, url, rough, w, h)
            x1, y1, x2, y2 = fine[:4] if fine else rough
            step.pointer = Pointer(t=t, x1=x1, y1=y1, x2=x2, y2=y2, w=w, h=h, label=step.field)
        except Exception as e:  # pointer is a nicety; never fail the job for it
            notes.append(f"No pointer for “{step.text}”: {str(e)[:120]}")
    return notes
