from typing import Literal, Optional

from pydantic import BaseModel, Field

EventSource = Literal["seen", "said"]
StepSource = Literal["seen", "said", "inferred"]


class Event(BaseModel):
    """One thing that happened in the recording (Pass 1 output)."""
    id: str = ""
    t: float = Field(ge=0, description="seconds into the video")
    t_end: Optional[float] = None
    source: EventSource
    action: str = ""
    screen: str = ""
    field: str = ""
    quote: str = ""  # verbatim narration when source == "said" (or narration heard during a seen action)


class Turn(BaseModel):
    """One narration turn from Muse Voice Transcribe (turn-level timing, not word-level)."""
    start: float
    end: float
    text: str


class Timeline(BaseModel):
    duration: float = 0
    events: list[Event] = []
    transcript: str = ""
    turns: list[Turn] = []  # empty when transcription wasn't run


class Pointer(BaseModel):
    """SAM 3.1 box around the on-screen element, in source pixels of the frame at time t."""
    t: float
    x1: int
    y1: int
    x2: int
    y2: int
    w: int
    h: int
    label: str = ""


class QuoteCheck(BaseModel):
    start: float
    end: float
    text: str


class Step(BaseModel):
    id: str
    t_start: float
    t_end: Optional[float] = None
    text: str
    detail: str = ""
    kind: Literal["step", "decision"] = "step"
    source: StepSource
    evidence: str = ""          # plain-English description of what supports this step
    quote: str = ""
    evidence_event_ids: list[str] = []
    field: str = ""             # on-screen element the step refers to (used for the visual pointer)
    confirmed: bool = False     # expert confirmed an inferred step
    downgraded_reason: str = ""  # set by the evidence check when a claimed seen/said had no support
    quote_check: Optional[QuoteCheck] = None  # narration turn that contains the quote (Voice Transcribe)
    pointer: Optional[Pointer] = None         # SAM 3.1 visual pointer


class Branch(BaseModel):
    label: str
    next_step_id: Optional[str] = None
    open_question_id: Optional[str] = None
    source: StepSource = "inferred"
    t: Optional[float] = None


class Decision(BaseModel):
    id: str
    step_id: str
    question: str
    branches: list[Branch] = []


class OpenQuestion(BaseModel):
    id: str
    question: str
    why: str = ""
    related_t: Optional[float] = None
    answer: str = ""


class Playbook(BaseModel):
    title: str
    duration: float = 0
    steps: list[Step] = []
    decisions: list[Decision] = []
    open_questions: list[OpenQuestion] = []
    notes: list[str] = []  # evidence-check log, shown to reviewers

    def counts(self) -> dict:
        c = {"seen": 0, "said": 0, "inferred": 0, "to_confirm": 0, "open_questions": 0}
        for s in self.steps:
            c[s.source] += 1
            if s.source == "inferred" and not s.confirmed:
                c["to_confirm"] += 1
        c["open_questions"] = sum(1 for q in self.open_questions if not q.answer)
        return c
