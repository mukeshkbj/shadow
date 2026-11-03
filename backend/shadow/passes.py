"""Pass 1 (timeline) and Pass 2 (playbook draft). Pass 3 lives in evidence.py."""
import json
from pathlib import Path
from typing import Callable, Optional

from pydantic import ValidationError

from . import media, prompts
from .config import Settings
from .muse import extract_json
from .schemas import Branch, Decision, Event, OpenQuestion, Playbook, Step, Timeline

Progress = Callable[[str], None]


def _events_from(raw: dict, offset: float, limit: Optional[float]) -> list[Event]:
    events = []
    for e in raw.get("events", []) or []:
        try:
            ev = Event(
                t=max(0.0, float(e.get("t", 0))) + offset,
                t_end=(float(e["t_end"]) + offset) if e.get("t_end") not in (None, "") else None,
                source="said" if str(e.get("source", "")).lower() == "said" else "seen",
                action=str(e.get("action", "")), screen=str(e.get("screen", "")),
                field=str(e.get("field", "")), quote=str(e.get("quote", "")),
            )
        except (TypeError, ValueError, ValidationError):
            continue
        if limit is not None and ev.t - offset > limit + 1:  # time outside the clip: untrustworthy, drop
            continue
        events.append(ev)
    return events


REPAIR = "Your previous reply was not valid JSON. Reply again with ONLY the JSON object, no prose, no code fences.\n\n"


def _json_with_retry(call, prompt: str, raw_path: Path):
    """Call a model, parse JSON; on a parse failure, ask once more for JSON only."""
    text = call(prompt)
    raw_path.write_text(text, encoding="utf-8")
    try:
        return extract_json(text)
    except (ValueError, json.JSONDecodeError):
        text = call(REPAIR + prompt)
        raw_path.with_suffix(".retry.txt").write_text(text, encoding="utf-8")
        return extract_json(text)


def build_timeline(provider, video: Path, work: Path, s: Settings, progress: Progress, turns=None) -> Timeline:
    total = media.duration(video)
    window = s.window_seconds
    if provider.needs_windows:
        window = window or s.open_window_seconds
    clips: list[tuple[float, Path]]
    if window and total > window:
        progress(f"slicing into {window}s windows")
        clips = media.slice_windows(video, work / "windows", window, total)
    else:
        clips = [(0.0, video)]

    events: list[Event] = []
    transcripts = []
    for n, (offset, clip) in enumerate(clips, 1):
        progress(f"watching {n}/{len(clips)}")
        length = min(window, total - offset) if len(clips) > 1 else total
        note = prompts.WINDOW_NOTE.format(length=length) if len(clips) > 1 else ""
        prompt = prompts.TIMELINE.format(window_note=note)
        if turns and not getattr(provider, "hears_audio", True):
            heard = [t for t in turns if t.end > offset and t.start < offset + length]
            lines = "\n".join(f"[{max(t.start - offset, 0):.1f}s] {t.text}" for t in heard) or "(no narration in this clip)"
            prompt += prompts.NARRATION_NOTE.format(lines=lines)
        raw = _json_with_retry(lambda p: provider.watch(clip, p), prompt, work / f"pass1_raw_{n:03d}.txt")
        events += _events_from(raw, offset, length)
        if raw.get("transcript"):
            transcripts.append(str(raw["transcript"]))

    events.sort(key=lambda e: e.t)
    for i, e in enumerate(events, 1):
        e.id = f"e{i}"
    return Timeline(duration=total, events=events, transcript="\n".join(transcripts))


def _lenient(model, items, **extra):
    out = []
    for it in items or []:
        try:
            out.append(model(**{**it, **extra}) if isinstance(it, dict) else None)
        except (ValidationError, TypeError):
            continue
    return [o for o in out if o is not None]


def parse_playbook(raw: dict, duration: float) -> Playbook:
    steps = []
    for st in raw.get("steps", []) or []:
        if not isinstance(st, dict):
            continue
        st = dict(st)
        src = str(st.get("source", "inferred")).lower()
        st["source"] = src if src in ("seen", "said", "inferred") else "inferred"
        if st.get("kind") not in ("step", "decision"):
            st["kind"] = "step"
        st["evidence_event_ids"] = [str(x) for x in (st.get("evidence_event_ids") or [])]
        for k in ("detail", "evidence", "quote", "field"):
            st[k] = st.get(k) or ""
        try:
            steps.append(Step(**st))
        except (ValidationError, TypeError):
            continue
    decisions = []
    for d in raw.get("decisions", []) or []:
        if not isinstance(d, dict):
            continue
        branches = []
        for b in d.get("branches", []) or []:
            if isinstance(b, dict):
                b = dict(b)
                if b.get("source") not in ("seen", "said", "inferred"):
                    b["source"] = "inferred"
                try:
                    branches.append(Branch(**b))
                except (ValidationError, TypeError):
                    pass
        try:
            decisions.append(Decision(id=str(d.get("id")), step_id=str(d.get("step_id")),
                                      question=str(d.get("question", "")), branches=branches))
        except ValidationError:
            pass
    questions = _lenient(OpenQuestion, raw.get("open_questions"))
    return Playbook(title=str(raw.get("title") or "Untitled task"), duration=duration,
                    steps=steps, decisions=decisions, open_questions=questions)


def build_playbook(provider, timeline: Timeline, work: Path, s: Settings) -> Playbook:
    log = json.dumps({"duration": timeline.duration,
                      "events": [e.model_dump(exclude_none=True) for e in timeline.events]}, ensure_ascii=False)
    raw = _json_with_retry(provider.think, prompts.PLAYBOOK.format(timeline=log), work / "pass2_raw.txt")
    return parse_playbook(raw, timeline.duration)
