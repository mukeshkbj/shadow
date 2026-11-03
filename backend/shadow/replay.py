"""Replay: an agent re-runs a confirmed playbook on the live app the recording was made in.

For each step, Muse sees the current screen (screenshot + DOM snapshot) plus the rules
the expert said aloud, and picks one action from a tiny set. Steps the expert never
confirmed and branches the recording never showed stop and ask instead of guessing.

`page` is duck-typed (a Playwright Page in production, a stub in tests): it needs
screenshot(), evaluate(), click(), fill(), select_option() and goto().
"""
import base64
import json
import re
from pathlib import Path
from typing import Callable, Optional

from .muse import MuseClient, extract_json
from .schemas import Playbook, Step

Ask = Callable[[str], str]
MAX_ACTIONS_PER_STEP = 3
Progress = Callable[[str], None]

SNAPSHOT_JS = """() => {
  const vis = el => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && !el.closest(".hidden,[hidden]");
  };
  const out = [];
  document.querySelectorAll("button,input,select,textarea,option,.msg,[role=alert],[id*=banner],[class*=banner]")
    .forEach(el => {
      if (!vis(el)) return;
      const lab = el.closest("label");
      out.push({tag: el.tagName.toLowerCase(), id: el.id || "",
                text: (el.innerText || el.value || el.placeholder || el.getAttribute("aria-label") || "").trim().slice(0, 100),
                label: lab && lab !== el ? lab.innerText.trim().slice(0, 80) : ""});
    });
  return out;
}"""

ACTION = """You are re-running a recorded task inside a web app, one step at a time.

Step to perform: "{text}"
{detail_line}
Rules the expert said aloud while recording:
{rules}
Expert notes from this run:
{notes}
Actions already taken for this step:
{taken}
Interactive elements currently on the page (JSON):
{elements}

Return JSON only, exactly one next action:
{{"action": "click" | "fill" | "select" | "check" | "none",
  "by": "css" | "text",
  "selector": "<css selector, or visible text when by=text>",
  "value": "<text to type, or option label for select>",
  "done": true | false,
  "why": "<one line>"}}

A step can need several actions (e.g. type an order number, then click Search). Set "done": true
when this action completes the step; false if another action is still needed after it.

- click: click an element. by="css" uses a selector like #issue; by="text" matches visible text like "Alex Morgan".
- fill: clear the field and type the value.
- select: choose a <select> option by its label text.
- check: nothing to do - the step is a comparison or reading you perform from the page state shown.
- none: the step needs no action on screen.
If nothing on the page matches the step, return {{"action": "none", "why": "no matching element"}}.
Never invent selectors: only use an id or text that appears in the elements list."""

DECISION = """You are at a decision point while re-running a task.

Question: "{question}"
Rules the expert said aloud while recording:
{rules}
Expert notes from this run:
{notes}
Current page elements and field values (JSON):
{elements}

Options:
{options}

Return JSON only: {{"choice": <option number, 1-based>, "why": "<one line>"}}
Pick the option that matches the rules and what the page actually shows.
If the page does not show enough to decide, pick the option numbered 0 ("stop and ask")."""


def _json(call, *args) -> dict:
    text, _ = call(*args)
    try:
        r = extract_json(text)
        return r if isinstance(r, dict) else {}
    except (ValueError, json.JSONDecodeError):
        return {}


def _snapshot(page) -> list:
    try:
        return page.evaluate(SNAPSHOT_JS) or []
    except Exception:
        return []


def _shot_b64(page) -> Optional[str]:
    try:
        return "data:image/png;base64," + base64.b64encode(page.screenshot()).decode()
    except Exception:
        return None


def _propose(client: MuseClient, model: str, step: Step, elements: list,
             rules: list[str], notes: list[str], shot: Optional[str], taken: Optional[list] = None) -> dict:
    prompt = ACTION.format(
        taken="\n".join(f"- {t}" for t in (taken or [])) or "(none yet)",
        text=step.text,
        detail_line=f"Detail: {step.detail}\n" if step.detail else "",
        rules="\n".join(f"- {r}" for r in rules) or "(none)",
        notes="\n".join(f"- {n}" for n in notes) or "(none)",
        elements=json.dumps(elements, ensure_ascii=False)[:6000],
    )
    content = [{"type": "input_text", "text": prompt}]
    if shot:
        content.append({"type": "input_image", "image_url": shot})
    return _json(client.respond_parts, model, content)


def _decide(client: MuseClient, model: str, question: str, branches: list,
            elements: list, rules: list[str], notes: list[str], shot: Optional[str]) -> dict:
    options = "\n".join(f"{i+1}. {b.label}" for i, b in enumerate(branches))
    options += "\n0. Stop and ask (not enough information)"
    prompt = DECISION.format(question=question,
                             rules="\n".join(f"- {r}" for r in rules) or "(none)",
                             notes="\n".join(f"- {n}" for n in notes) or "(none)",
                             elements=json.dumps(elements, ensure_ascii=False)[:6000],
                             options=options)
    content = [{"type": "input_text", "text": prompt}]
    if shot:
        content.append({"type": "input_image", "image_url": shot})
    return _json(client.respond_parts, model, content)


def _execute(page, act: dict) -> tuple[bool, str]:
    kind = str(act.get("action", "none"))
    by = str(act.get("by", "css"))
    sel = str(act.get("selector", ""))
    val = str(act.get("value", ""))
    try:
        if kind == "check" or kind == "none" or not sel:
            return True, ""
        if kind == "click":
            if by == "text":
                page.locator(f"text={sel}").first.click(timeout=5000)
            else:
                page.click(sel, timeout=5000)
        elif kind == "fill":
            page.fill(sel, val, timeout=5000)
        elif kind == "select":
            page.select_option(sel, label=val, timeout=5000)
        else:
            return False, f"unknown action {kind!r}"
        page.wait_for_timeout(400)
        return True, ""
    except Exception as e:
        return False, re.sub(r"\s+", " ", str(e))[:200]


def run(client: MuseClient, page, pb: Playbook, work: Path,
        ask: Ask, progress: Progress = print, model: str = "muse-spark-1.3",
        shots_dir: Optional[Path] = None) -> dict:
    """Drive `page` through the playbook. Returns the replay log."""
    work = Path(work)
    if shots_dir is None:
        shots_dir = work / "replay"
    shots_dir.mkdir(parents=True, exist_ok=True)

    rules = [s.quote for s in pb.steps if s.source == "said" and s.quote]
    decisions = {d.step_id: d for d in pb.decisions}
    questions = {q.id: q for q in pb.open_questions}
    index_of = {s.id: i for i, s in enumerate(pb.steps)}
    notes: list[str] = []
    log = {"title": pb.title, "model": model, "actions": [], "asked": [], "stopped": ""}

    i = 0
    while 0 <= i < len(pb.steps):
        step = pb.steps[i]
        n = i + 1

        if step.source == "inferred" and not step.confirmed:
            ans = ask(f"Step {n} is unconfirmed: “{step.text}”. "
                      "Enter = run it anyway · s = skip · or type the correction:")
            log["asked"].append({"step": step.id, "question": "unconfirmed step", "answer": ans})
            if ans.strip().lower() == "s":
                log["actions"].append({"step": step.id, "text": step.text, "skipped": True})
                i += 1
                continue
            if ans.strip():
                notes.append(f"On step {n} the expert corrected: {ans.strip()}")

        elements = _snapshot(page)
        shot = _shot_b64(page)

        dec = decisions.get(step.id)
        if dec:
            choice = _decide(client, model, dec.question, dec.branches, elements, rules, notes, shot)
            try:
                k = int(choice.get("choice") or 0) - 1
            except (TypeError, ValueError):
                k = -1
            branch = dec.branches[k] if 0 <= k < len(dec.branches) else None
            if branch is None:
                ans = ask(f"Decision “{dec.question}” — I can't tell which way from the page. "
                          "Type the answer, or Enter to stop:")
                log["asked"].append({"step": step.id, "question": dec.question, "answer": ans})
                if not ans.strip():
                    log["stopped"] = f"decision at step {n} needed the expert"
                    break
                notes.append(f"{dec.question} → {ans.strip()}")
                i += 1
                continue
            log["actions"].append({"step": step.id, "decision": dec.question,
                                   "chose": branch.label, "why": choice.get("why", "")})
            progress(f"step {n}: decision “{dec.question}” → {branch.label}")
            if branch.open_question_id and branch.open_question_id in questions:
                q = questions[branch.open_question_id]
                ans = ask(f"“{dec.question}” → {branch.label}: {q.question} "
                          "The recording never showed this. Answer it, or Enter to stop:")
                log["asked"].append({"step": step.id, "question": q.question, "answer": ans})
                if not ans.strip():
                    log["stopped"] = f"unshown branch at step {n}"
                    break
                notes.append(f"{q.question} → {ans.strip()}")
                i += 1
                continue
            if branch.next_step_id and branch.next_step_id in index_of:
                i = index_of[branch.next_step_id]
                continue
            i += 1
            continue

        # A step may need a few actions (fill, then click). Re-read the page between them.
        taken: list[str] = []
        failed = False
        for _ in range(MAX_ACTIONS_PER_STEP):
            act = _propose(client, model, step, elements, rules, notes, shot, taken)
            ok, err = _execute(page, act)
            entry = {"step": step.id, "text": step.text, "action": act.get("action"),
                     "selector": act.get("selector"), "value": act.get("value"),
                     "why": act.get("why"), "ok": ok}
            if not ok:
                entry["error"] = err
                log["actions"].append(entry)
                failed = True
                break
            log["actions"].append(entry)
            progress(f"step {n}: {act.get('action')} {act.get('selector') or ''} — {str(act.get('why', ''))[:60]}")
            taken.append(f"{act.get('action')} {act.get('selector') or ''} {act.get('value') or ''}".strip())
            if act.get("done", True) or act.get("action") in ("check", "none", None):
                break
            elements = _snapshot(page)
            shot = _shot_b64(page)
        after = _shot_b64(page)   # what the screen looks like once the step is done
        try:
            (shots_dir / f"step_{n:02d}.png").write_bytes(base64.b64decode((after or shot or "").split(",", 1)[-1] or "iVBORw0KGgo="))
        except Exception:
            pass
        if failed:
            ans = ask(f"Step {n} failed (“{step.text}”): {err}\nType a hint, or Enter to stop:")
            log["asked"].append({"step": step.id, "question": "action failed", "answer": ans})
            if not ans.strip():
                log["stopped"] = f"step {n} failed"
                break
            notes.append(f"On step {n} the expert hinted: {ans.strip()}")
            continue
        i += 1

    (work / "replay_log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    return log
