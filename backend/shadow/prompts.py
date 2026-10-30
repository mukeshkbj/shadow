TIMELINE = """You are watching a screen recording of someone doing a task at work while they narrate.
Your job is to LOG WHAT HAPPENED, not to interpret it.

Return JSON only (no markdown), exactly this shape:
{{
  "duration": <video length in seconds>,
  "transcript": "<verbatim narration, as heard>",
  "events": [
    {{"t": <seconds from the start of THIS clip>, "t_end": <seconds or null>,
      "source": "seen" | "said",
      "action": "<what happened, short>",
      "screen": "<which screen or panel>",
      "field": "<exact on-screen label of the element involved, or empty>",
      "quote": "<verbatim words spoken at that moment, or empty>"}}
  ]
}}

Rules:
- "seen": an action visible on screen (click, typing, selecting, opening a screen, pointing at a field).
- "said": a rule, reason or intention spoken aloud. Put the exact words in "quote".
- Also log visible settings that matter as "seen" events when they first appear or change: sort order, filters,
  the selected item, and values shown in key fields (e.g. "Inbox sorted Newest first", "Approver set to Sam K.").
- If narration and screen disagree, log both as separate events. Do not reconcile them.
- Timestamps must be when it happens in the video, to the nearest second. {window_note}
- Do not invent events you did not see or hear. Fewer, accurate events are better.
"""

WINDOW_NOTE = "This clip is a {length:.0f}-second window; use times relative to the start of this clip (0 to {length:.0f})."

PLAYBOOK = """You are turning a timestamped log of a screen recording into a step-by-step playbook that an expert will REVIEW.
Being honest about evidence matters more than being complete.

The log (JSON; each event has an id, time in seconds, source "seen" or "said"):
{timeline}

Return JSON only (no markdown), exactly this shape:
{{
  "title": "<task name, e.g. Processing a refund request>",
  "steps": [
    {{"id": "s1", "t_start": <sec>, "t_end": <sec or null>, "text": "<imperative step>",
      "detail": "<one short line>", "kind": "step" | "decision",
      "source": "seen" | "said" | "inferred",
      "evidence": "<what in the log supports this, in plain English>",
      "quote": "<verbatim quote if source is said, else empty>",
      "evidence_event_ids": ["<event ids>"],
      "field": "<on-screen label involved, or empty>"}}
  ],
  "decisions": [
    {{"id": "d1", "step_id": "<step id where the decision is made>", "question": "<e.g. Bought within 30 days?>",
      "branches": [{{"label": "Yes", "next_step_id": "<id or null>", "open_question_id": "<id or null>",
                    "source": "seen" | "said" | "inferred", "t": <sec or null>}}]}}
  ],
  "open_questions": [
    {{"id": "q1", "question": "<what the recording did not show>", "why": "<what made you notice the gap>", "related_t": <sec or null>}}
  ]
}}

Rules:
- Write the playbook a new starter needs: usually 5-10 steps. One step per business action.
  Merge low-level clicks into the action they serve (open + search + click = "Look up the order").
  Never add a step for merely looking at a screen or for something loading.
- Combine an on-screen action with the narration that explains it into ONE step, citing both events.
- source "seen": the step is an on-screen action in the log. "said": the step's rule or reason is quoted in the log.
  "inferred": your interpretation (e.g. two fields compared but no reason given), or the screen and narration disagree.
- If the narration states a habit the screen contradicts (e.g. "oldest first" while the list is sorted newest first
  and the top item is opened), the step is "inferred" and "evidence" must name both sides of the conflict.
- Every step MUST cite at least one event id and use that event's time.
- A spoken rule with a condition ("if X, then Y"; "anything over £500...") is a decision: set kind "decision" on its step
  and add a decision whose branches cover each outcome. A branch the recording showed points to the next step.
  A branch it did not show points to an open question. Never invent steps for unshown branches.
- Open questions: 2-5, one short sentence each, about exceptions or branches the recording did not cover.
  Don't ask about things the recording clearly showed.
"""
