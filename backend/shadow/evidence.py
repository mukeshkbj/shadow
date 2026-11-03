"""Pass 3: deterministic evidence check. No model calls.

Rules
- A step must sit inside the video and be backed by at least one timeline event near its time.
  Otherwise it is removed and turned into an open question (never kept as a confident step).
- "seen" needs a seen event in the window; "said" needs a said event whose words match the quote.
  Unsupported claims are downgraded to "inferred" with the reason recorded.
- A decision branch that leads nowhere becomes an open question.
"""
import re
from typing import Iterable, Optional

from .schemas import Conflict, Event, OpenQuestion, Playbook, QuoteCheck, Step, Timeline

_WORD = re.compile(r"[a-z0-9£$]+")
_NUM = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}
_NUM.update({"thirty": "30", "forty": "40", "fifty": "50", "hundred": "100", "twelfth": "12th"})
_FILLER = {"the", "a", "an", "to", "and", "i", "it", "it's", "s", "of", "uh", "um"}


def _words(s: str) -> set[str]:
    return {_NUM.get(w, w) for w in _WORD.findall(s.lower().replace("’", "'"))} - _FILLER


def quote_matches(claimed: str, heard: str, threshold: float = 0.6) -> bool:
    a, b = _words(claimed), _words(heard)
    if not a or not b:
        return False
    return len(a & b) / len(a) >= threshold


def _window(step: Step, slack: float) -> tuple[float, float]:
    end = step.t_end if step.t_end is not None and step.t_end >= step.t_start else step.t_start
    return step.t_start - slack, end + slack


def _near(events: Iterable[Event], lo: float, hi: float) -> list[Event]:
    return [e for e in events if lo <= e.t <= hi or (e.t_end is not None and e.t <= hi and e.t_end >= lo)]


def _next_qid(pb: Playbook) -> str:
    n = len(pb.open_questions) + 1
    ids = {q.id for q in pb.open_questions}
    while f"q{n}" in ids:
        n += 1
    return f"q{n}"


def conflict(step: Step, tl: Timeline) -> Optional[Conflict]:
    """The model marks a step inferred and cites both sides when screen and narration disagree
    (prompts.py). A step the check itself downgraded is a missing-evidence case, not a conflict."""
    if step.source != "inferred" or step.downgraded_reason:
        return None
    by_id = {e.id: e for e in tl.events}
    cited = [by_id[i] for i in step.evidence_event_ids if i in by_id]
    seen = [e for e in cited if e.source == "seen"]
    said = next((e for e in cited if e.source == "said"), None)
    if not seen or said is None:
        return None
    shown = next((e for e in seen if step.field and step.field in e.action), seen[0])
    turn = next((u for u in tl.turns if u.start - 0.5 <= said.t <= u.end + 0.5), None)
    return Conflict(seen_t=shown.t, seen=shown.action,
                    said_t=turn.start if turn else said.t, said_end=turn.end if turn else None,
                    said=said.quote or (turn.text if turn else said.action))


def check(pb: Playbook, tl: Timeline, slack: float = 4.0) -> Playbook:
    pb = pb.model_copy(deep=True)
    by_id = {e.id: e for e in tl.events}
    duration = tl.duration or pb.duration
    kept: list[Step] = []
    notes: list[str] = []

    for step in sorted(pb.steps, key=lambda s: s.t_start):
        if duration and (step.t_start < 0 or step.t_start > duration + 1):
            pb.open_questions.append(OpenQuestion(
                id=_next_qid(pb), question=f"Where does this happen: “{step.text}”?",
                why="Shadow proposed it, but its time is outside the recording."))
            notes.append(f"Removed “{step.text}”: timestamp {step.t_start:.0f}s is outside the video.")
            continue
        if step.t_end is not None and duration:
            step.t_end = min(step.t_end, duration)

        lo, hi = _window(step, slack)
        cited = [by_id[i] for i in step.evidence_event_ids if i in by_id]
        cited_in_window = [e for e in cited if lo <= e.t <= hi]
        nearby = _near(tl.events, lo, hi)
        cited_ids = {e.id for e in cited_in_window}
        support = cited_in_window + [e for e in nearby if e.id not in cited_ids]

        if not support:
            pb.open_questions.append(OpenQuestion(
                id=_next_qid(pb), question=f"Is this part of the job: “{step.text}”?",
                why="Shadow couldn't find it in the recording, so it isn't in the playbook.",
                related_t=step.t_start))
            notes.append(f"Removed “{step.text}”: no event in the recording near {step.t_start:.0f}s.")
            continue

        if step.source == "seen" and not any(e.source == "seen" for e in support):
            step.source = "inferred"
            step.downgraded_reason = "Nothing matching was seen on screen at this time."
        elif step.source == "said":
            said = [e for e in support if e.quote]
            match = next((e for e in said if not step.quote or quote_matches(step.quote, e.quote)), None)
            if match is None:
                step.source = "inferred"
                claimed = f" “{step.quote}”" if step.quote else ""
                step.downgraded_reason = f"The draft quoted{claimed}, but those words weren't heard at this time."
                step.quote = ""  # never show unheard words as a quote
            else:
                if not step.quote:
                    step.quote = match.quote
                if tl.turns:  # second, independent check against the narration transcript
                    turn = next((u for u in tl.turns
                                 if u.start - slack <= hi and u.end + slack >= lo and quote_matches(step.quote, u.text)), None)
                    if turn is None:
                        step.source = "inferred"
                        step.downgraded_reason = (f"The narration transcript doesn't contain “{step.quote}” "
                                                  "near this time.")
                        step.quote = ""
                    else:
                        step.quote_check = QuoteCheck(start=turn.start, end=turn.end, text=turn.text)
        if step.downgraded_reason:
            notes.append(f"“{step.text}” marked inferred: {step.downgraded_reason}")

        if not step.evidence_event_ids:
            step.evidence_event_ids = [e.id for e in support]
        if not step.field:
            step.field = next((e.field for e in support if e.field), "")
        kept.append(step)

    kept_ids = {s.id for s in kept}
    for d in pb.decisions:
        for b in d.branches:
            if b.next_step_id and b.next_step_id not in kept_ids:
                b.next_step_id = None
            if not b.next_step_id and not b.open_question_id:
                qid = _next_qid(pb)
                pb.open_questions.append(OpenQuestion(
                    id=qid, question=f"{d.question} {b.label} — what happens next?",
                    why="This branch wasn't shown in the recording."))
                b.open_question_id = qid
                b.source = "inferred"
    pb.decisions = [d for d in pb.decisions if d.step_id in kept_ids]

    pb.steps = kept
    pb.duration = duration
    pb.notes = notes
    return pb
