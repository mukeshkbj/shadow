"""Deterministic exporters: cited Markdown playbook and Mermaid flow."""
from .schemas import Playbook

LABEL = {"seen": "Seen", "said": "Said", "inferred": "Unconfirmed"}


def ts(sec: float | None) -> str:
    if sec is None:
        return "--:--"
    sec = int(round(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _label(step) -> str:
    if step.source == "inferred" and step.confirmed:
        return "Confirmed"
    return LABEL[step.source]


def markdown(pb: Playbook, video_url: str | None = None) -> str:
    c = pb.counts()
    lines = [f"# {pb.title}", "",
             f"_From a {ts(pb.duration)} screen recording. "
             f"{c['seen']} seen · {c['said']} said · {c['inferred']} inferred "
             f"({c['to_confirm']} unconfirmed) · {c['open_questions']} open questions._", "",
             "**Seen** = visible on screen · **Said** = stated in the narration · "
             "**Unconfirmed** = Shadow's interpretation, not yet checked by the expert", "",
             "## Steps", ""]
    for i, s in enumerate(pb.steps, 1):
        stamp = ts(s.t_start)
        link = f"[{stamp}]({video_url}#t={int(s.t_start)})" if video_url else stamp
        lines.append(f"{i}. **{s.text}** — {_label(s)} · {link}")
        if s.detail:
            lines.append(f"   - {s.detail}")
        if s.quote:
            lines.append(f"   - > “{s.quote}”")
        if s.source == "inferred" and not s.confirmed and s.evidence:
            lines.append(f"   - Why unconfirmed: {s.evidence}")
    open_q = [q for q in pb.open_questions if not q.answer]
    answered = [q for q in pb.open_questions if q.answer]
    if open_q:
        lines += ["", "## Open questions", ""]
        lines += [f"- {q.question}" + (f" _({q.why})_" if q.why else "") for q in open_q]
    if answered:
        lines += ["", "## Answered by the expert", ""]
        lines += [f"- **{q.question}** {q.answer}" for q in answered]
    return "\n".join(lines) + "\n"


def _esc(s: str) -> str:
    return s.replace('"', "'").replace("\n", " ")


def mermaid(pb: Playbook) -> str:
    out = ["flowchart TD"]
    steps = pb.steps
    decisions = {d.step_id: d for d in pb.decisions}
    q_by_id = {q.id: q for q in pb.open_questions}
    for s in steps:
        label = f"{_esc(s.text)}<br/><small>{_label(s)} · {ts(s.t_start)}</small>"
        if s.id in decisions:
            out.append(f'  {s.id}{{"{_esc(decisions[s.id].question)}<br/><small>{ts(s.t_start)}</small>"}}')
        else:
            out.append(f'  {s.id}["{label}"]')
    targeted = set()
    for d in pb.decisions:
        for b in d.branches:
            if b.next_step_id:
                targeted.add(b.next_step_id)
    for a, b in zip(steps, steps[1:]):
        if a.id in decisions:
            continue  # decision edges come from its branches
        out.append(f"  {a.id} --> {b.id}")
    for d in pb.decisions:
        for i, b in enumerate(d.branches):
            if b.next_step_id:
                out.append(f'  {d.step_id} -- "{_esc(b.label)}" --> {b.next_step_id}')
            elif b.open_question_id and b.open_question_id in q_by_id:
                qn = f"{d.step_id}_{b.open_question_id}"
                out.append(f'  {qn}["? {_esc(q_by_id[b.open_question_id].question)}"]')
                out.append(f'  {d.step_id} -- "{_esc(b.label)}" --> {qn}')
                out.append(f"  class {qn} open")
    for s in steps:
        if s.source == "inferred" and not s.confirmed:
            out.append(f"  class {s.id} inferred")
    out.append("  classDef inferred stroke:#C2410C,stroke-dasharray:5 3")
    out.append("  classDef open stroke:#8A91A0,stroke-dasharray:5 3,fill:#FAFAFB")
    return "\n".join(out) + "\n"
