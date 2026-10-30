import json
from pathlib import Path

from shadow import evidence, exporters, passes
from shadow.muse import extract_json
from shadow.schemas import Event, Playbook, Step, Timeline

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def sample():
    tl = Timeline.model_validate_json((FIX / "sample_timeline.json").read_text(encoding="utf-8"))
    draft = passes.parse_playbook(json.loads((FIX / "sample_playbook_draft.json").read_text(encoding="utf-8")), tl.duration)
    return draft, tl


def test_sample_counts_after_check():
    draft, tl = sample()
    pb = evidence.check(draft, tl)
    by = {s.id: s for s in pb.steps}
    assert by["s1"].source == "inferred"            # narration/screen conflict stays inferred
    assert by["s3"].source == "said"                # 30-day rule was heard
    assert by["s4"].source == "inferred"            # claimed quote was never said -> downgraded
    assert "weren't heard" in by["s4"].downgraded_reason
    assert by["s4"].quote == ""                     # unheard words are never shown as a quote
    assert by["s5"].source == "said"
    assert pb.counts() == {"seen": 3, "said": 2, "inferred": 2, "to_confirm": 2, "open_questions": 3}


def test_said_quote_fuzzy_match():
    assert evidence.quote_matches("over five hundred pounds goes to my manager",
                                  "Anything over five hundred pounds I send to my manager first")
    assert not evidence.quote_matches("make sure they're not asking for more than they paid",
                                      "Anything over five hundred pounds I send to my manager first")


def test_unsupported_step_becomes_open_question():
    tl = Timeline(duration=100, events=[Event(id="e1", t=10, source="seen", action="click")])
    pb = Playbook(title="t", steps=[
        Step(id="s1", t_start=10, text="Click it", source="seen", evidence_event_ids=["e1"]),
        Step(id="s2", t_start=60, text="Phone the customer", source="seen"),
        Step(id="s3", t_start=500, text="Out of range", source="seen"),
    ])
    out = evidence.check(pb, tl)
    assert [s.id for s in out.steps] == ["s1"]
    assert len(out.open_questions) == 2
    assert any("Phone the customer" in q.question for q in out.open_questions)


def test_seen_without_seen_event_is_downgraded():
    tl = Timeline(duration=100, events=[Event(id="e1", t=10, source="said", quote="I check the date")])
    pb = Playbook(title="t", steps=[Step(id="s1", t_start=10, text="Check date", source="seen")])
    out = evidence.check(pb, tl)
    assert out.steps[0].source == "inferred"


def test_seen_step_citing_only_said_event_still_finds_nearby_seen():
    tl = Timeline(duration=100, events=[
        Event(id="e1", t=10, source="said", quote="I check the date"),
        Event(id="e2", t=11, source="seen", action="point at date")])
    pb = Playbook(title="t", steps=[Step(id="s1", t_start=10, text="Check date", source="seen",
                                         evidence_event_ids=["e1"])])
    out = evidence.check(pb, tl)
    assert out.steps[0].source == "seen"


def test_dangling_branch_becomes_open_question():
    draft, tl = sample()
    draft.steps = [s for s in draft.steps if s.id != "s4"]   # remove the Yes target
    pb = evidence.check(draft, tl)
    d1 = next(d for d in pb.decisions if d.id == "d1")
    yes = next(b for b in d1.branches if b.label == "Yes")
    assert yes.next_step_id is None and yes.open_question_id


def test_exporters():
    draft, tl = sample()
    pb = evidence.check(draft, tl)
    md = exporters.markdown(pb)
    assert "Unconfirmed" in md and "## Open questions" in md and "02:40" in md
    mm = exporters.mermaid(pb)
    assert mm.startswith("flowchart TD") and "class s4 inferred" in mm and "? What happens if the customer refuses" in mm


def test_extract_json_tolerates_fences():
    assert extract_json('Here you go:\n```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('blah {"a": [1, 2]} trailing') == {"a": [1, 2]}


def test_number_words_match_digits():
    assert evidence.quote_matches("That goes back on their card in three to five days",
                                  "that goes back on their card in 3-5 days.")


def test_said_events_snap_to_transcript_turns():
    from shadow.schemas import Turn
    from shadow.transcribe import align_said_events
    tl = Timeline(duration=90, events=[Event(id="e1", t=82, source="said", quote="Last thing, the confirmation email."),
                                       Event(id="e2", t=83, source="seen", action="template")],
                  turns=[Turn(start=72.8, end=75.3, text="last thing the confirmation email")])
    assert align_said_events(tl) == 1
    assert tl.events[0].t == 72.8 and tl.events[0].source == "said"
