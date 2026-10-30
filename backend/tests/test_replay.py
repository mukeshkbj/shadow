import json

from shadow import replay
from shadow.schemas import Branch, Decision, OpenQuestion, Playbook, Step


class FakePage:
    def __init__(self):
        self.calls = []

    def evaluate(self, js):
        return [{"tag": "button", "id": "go", "text": "Go", "label": ""}]

    def screenshot(self):
        return b"\x89PNG"

    def locator(self, sel):
        class L:
            def click(self, timeout=0):
                pass
        return L()

    def click(self, sel, timeout=0):
        self.calls.append(("click", sel))

    def fill(self, sel, val, timeout=0):
        self.calls.append(("fill", sel, val))

    def select_option(self, sel, label="", timeout=0):
        self.calls.append(("select", sel, label))

    def wait_for_timeout(self, ms):
        pass


class FakeClient:
    def __init__(self, replies):
        self.replies = iter(replies)

    def respond_parts(self, model, content, **kw):
        return json.dumps(next(self.replies)), {}


def test_replay_skips_unconfirmed_step(tmp_path):
    pb = Playbook(title="t", steps=[
        Step(id="s1", t_start=0, text="Safe step", source="seen"),
        Step(id="s2", t_start=5, text="Risky guess", source="inferred")])
    client = FakeClient([{"action": "none", "why": "read-only"}])
    asked = []
    log = replay.run(client, FakePage(), pb, tmp_path, ask=lambda q: asked.append(q) or "s")
    assert asked and "unconfirmed" in asked[0]
    assert log["actions"][-1]["skipped"] is True
    assert (tmp_path / "replay_log.json").exists()


def test_replay_stops_at_unshown_branch(tmp_path):
    pb = Playbook(title="t", steps=[
        Step(id="s1", t_start=0, text="Click Go", source="seen"),
        Step(id="s2", t_start=5, text="Decide refund vs credit", source="seen")],
        decisions=[Decision(id="d1", step_id="s2", question="Within 30 days?", branches=[
            Branch(label="Yes", open_question_id="q1"),
            Branch(label="No")])],
        open_questions=[OpenQuestion(id="q1", question="What if they refuse credit?")])
    client = FakeClient([{"action": "click", "by": "css", "selector": "#go", "why": "go"},
                         {"choice": 1, "why": "inside window"}])
    asked = []
    log = replay.run(client, FakePage(), pb, tmp_path, ask=lambda q: asked.append(q) or "")
    assert asked and "refuse credit" in asked[0]
    assert log["stopped"].startswith("unshown branch")


def test_replay_confirmed_inferred_step_runs(tmp_path):
    pb = Playbook(title="t", steps=[
        Step(id="s1", t_start=0, text="Once risky, now confirmed", source="inferred", confirmed=True)])
    client = FakeClient([{"action": "fill", "by": "css", "selector": "#q", "value": "ORD-1", "why": "type"}])
    page = FakePage()
    log = replay.run(client, page, pb, tmp_path, ask=lambda q: "s")
    assert log["actions"][0]["ok"] is True
    assert ("fill", "#q", "ORD-1") in page.calls
