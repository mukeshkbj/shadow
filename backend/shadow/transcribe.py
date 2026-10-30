"""Muse Voice Transcribe: turn-level narration timestamps used to check "Said" steps.

The API returns turns (startMs/endMs/transcript), not word timings, so a quote is checked
against the turn that overlaps the step's time window.
"""
from pathlib import Path
from typing import Optional

from . import media
from .muse import MuseClient
from .evidence import quote_matches
from .schemas import Timeline, Turn

MAX_SECONDS = 600       # API limit: 10 minutes
MAX_BYTES = 32_000_000  # API limit: 32 MB


def narration_turns(client: MuseClient, video: Path, work: Path, model: str) -> Optional[list[Turn]]:
    wav = media.extract_wav(video, work / "narration.wav", rate=24000)
    if wav is None:
        return None
    if media.duration(wav) > MAX_SECONDS or wav.stat().st_size > MAX_BYTES:
        wav = media.extract_wav(video, work / "narration16k.wav", rate=16000)
        if media.duration(wav) > MAX_SECONDS or wav.stat().st_size > MAX_BYTES:
            raise RuntimeError("narration is longer than the 10-minute transcription limit")
    data = client.transcribe(wav, model, mode="ENDPOINTING")
    turns = []
    for t in data.get("turns", []) or []:
        try:
            turns.append(Turn(start=float(t["startMs"]) / 1000, end=float(t["endMs"]) / 1000,
                              text=str(t.get("transcript", ""))))
        except (KeyError, TypeError, ValueError):
            continue
    return turns


def align_said_events(tl: Timeline, search: float = 20.0) -> int:
    """Snap each "said" event to the transcript turn containing its words.

    Video models place spoken lines less precisely than the transcriber does (seen in testing:
    up to ~9 s late), so turn times are used for narration. Returns how many events moved.
    """
    moved = 0
    for e in tl.events:
        if e.source != "said" or not e.quote:
            continue
        best = None
        for u in tl.turns:
            if abs(u.start - e.t) <= search and quote_matches(e.quote, u.text):
                if best is None or abs(u.start - e.t) < abs(best.start - e.t):
                    best = u
        if best and abs(best.start - e.t) > 0.5:
            e.t, e.t_end = best.start, best.end
            moved += 1
    tl.events.sort(key=lambda ev: ev.t)
    return moved
