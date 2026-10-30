# Shadow — record the job, get a reviewable playbook
Meta Global AI Developer Hackathon (Cerebral Valley) · Indie track · Theme: Build for Your World

> **Pitch:** Shadow turns an expert's screen recording and narration into a reviewable playbook, with every step tied to its source and every assumption called out.

## Deadlines (UK time)
- Submissions: Wed 4 Nov 21:00 ET = **Thu 5 Nov 02:00 GMT** (US clocks change 1 Nov). Aim to submit by **Wed 4 Nov 20:00 GMT** to leave a buffer.
- Judging 4–8 Nov · Finals 9 Nov
- Confirmed from the participant guide: submit on the CV platform by **Wed 4 Nov 9:00 PM ET**; Tue 3 Nov is the last day for technical help.

## Revalidated against the official participant guide (29 Oct)
**Verdict: Shadow still fits, and fits well.** It sits under *Build for Your World*, uses Meta's models at its core (Stage One pass/fail), and isn't on the anti-project list. It's not "a simple image analyzer" or "basic RAG": it's multimodal, multi-pass and cited.

**Rules that change what we do**
- **Public repo required.** Create `mukeshkbj/shadow` and make it public before submitting.
- **New work only; demo must show what was built during the event.** All code here was started 29 Oct. Commit often so the history shows it, and add a "Built during the hackathon" section to the README.
- **Judges use the video, the code *and the live product*.** Deploy a live URL (Modal) with the sample playbook working even when the API is busy.
- 3-minute demo video. Solo is fine (max team 4).

**Scoring rubric → how Shadow earns each point**
| Criterion (weight) | What judges ask | Shadow's answer |
|---|---|---|
| Impact (30%) | Who benefits, would people use it? | Team leads and ops teams turn undocumented know-how into a checked playbook, without trusting AI blindly. Open with the problem, not the tech |
| Use of Meta AI tooling (25%) | Beyond a basic integration? Surprise us | Five Meta models, each doing a distinct job (below), plus an evidence check that makes their output verifiable |
| Technical depth (20%) | Sound, thought-through engineering | Deterministic evidence check, Seen/Said downgrade rules, timestamp-safe windowing, tests |
| Demo (25%) | Works live, cool to watch | Click a "Said" rule → video jumps to the moment; watch a made-up step get downgraded; answer an open question live |

**Meta tooling: one job per model** (the 25% criterion)
| Model | Job in Shadow |
|---|---|
| Muse Spark 1.2 | Pass 1: watches the video *with* its audio and logs what was seen and said |
| Muse Wonder | Pass 2: drafts the playbook, decisions and open questions from the log |
| Muse Voice Transcribe | Turn-level narration timestamps (word-level is **not** available per the docs), so "Said" steps are checked against the exact words and the turn they were heard in |
| SAM 3.1 | Visual pointer: tracks the on-screen field through the step's clip (a pointer, not proof) |
| Muse Spark Open (via Baseten/Modal) | "Open-weights mode": the whole pipeline on an open model, for teams that can't send recordings to a hosted API |

## Bonus prizes to target
| Bonus | Prize | Plan | Effort |
|---|---|---|---|
| Best Build on Meta Open Weight Models | $10K | Open-weights mode on Muse Spark Open (`meta-models/muse-spark-open-1026` on Baseten, or Modal Endpoints). Show it in the demo and README | Medium. **Do it** |
| Most Viral Project (X engagement to 8 Nov) | $20K | Post a 30–45 s cut of the demo on X right after submitting, tag @AIatMeta and @cerebral_valley, submit the post link | Low. **Do it** |
| Community Vote (gallery, to 16 Nov) | $10K | Share the gallery link on LinkedIn, Pega Groundbreakers and X | Low. **Do it** |
| Best Agentic Use-Case | $5K | **Stretch, "Replay":** an agent re-runs the confirmed playbook on the demo prop and stops at any unconfirmed step or open question to ask the expert | High. Only if Days 1–5 land on time |
| Best Creative Build | $5K | Not a fit | — |

## Credits
| Partner | Status | Notes |
|---|---|---|
| Meta Model API ($150, guaranteed) | To do | Account at dev.meta.ai + card on file, then the claim form with your Team ID. Each person claims individually. Set a spend limit under Billing |
| Baseten ($100 + 2M TPM) | **Requested 29 Oct** | Selected by use case; reply by email. Model slug is `meta-models/muse-spark-open` on the chat/completions endpoint — no Responses API, and Baseten docs say Spark Open does **not** support structured outputs/JSON mode, so expect JSON-repair handling in Pass 1 |
| Modal ($100, up to 1,000 teams) | To do | Needs a Modal workspace first |
| Fireworks (shortlist) | To do | Needs a Fireworks account first |

## The problem (firsthand)
The people who really know how a job is done carry it in their heads. Written SOPs are out of date, skip the exceptions, and leave out the "then I check this other screen" steps. And an AI that writes an SOP confidently can be worse than none, because nobody can tell which parts it made up.

## The demo: one workflow, end to end
**Processing a refund request** for a fictional online shop, using synthetic data only (made-up orders, customers and amounts). "Works for any office process" is the vision; the demo proves it on this one workflow. Supplier setup is the stretch second example only if the core is solid.

Someone records their screen while handling one refund, talking as they go (3–5 min). Shadow produces exactly two outputs:
1. **A cited playbook**: every step shows its video timestamp and its source:
   - **Seen**: the action is visible on screen
   - **Said**: a rule or reason stated in the narration ("over £500 I get my manager to approve")
   - **Inferred**: Shadow's interpretation, not directly seen or said. Flagged for the expert to confirm or fix
2. **A flow diagram** of the same steps and decisions. Branches the recording didn't show appear as **open questions**, never as invented steps ("What happens if the customer refuses store credit?").

Review is part of the product: the expert confirms or corrects inferred steps and answers open questions, and the playbook records who confirmed what.

**Later, only if the core flow works:** data model of on-screen fields, training checklist, JSON workflow spec, merging recordings from several people.

## Why it fits this hackathon
- **Muse models take video with its audio track**, so one model can, in principle, see the actions and hear the reasons together. *Not yet proven for long screen recordings*: upload limits, processing time and timestamp accuracy are what the night-one gate test measures. Don't claim more until it passes.
- **SAM 3.1 as a visual pointer.** SAM 3.1 segments and tracks visual objects in images and video from a short text prompt. Shadow uses it to outline the on-screen field a step refers to, so a reviewer can find it in the frame fast. A mask around a field does **not** prove the step is right; the timestamped recording is the evidence. Pitch it exactly like that.
- Build for Your World: undocumented know-how is a problem I've seen firsthand.
- Indie criteria: creative (trustworthy knowledge capture, not another chatbot), technically ambitious (multimodal, multi-pass, cited), and it works (live upload of a fresh recording, with cached results as backup).

## Architecture
```
Upload MP4 ──► Files API (purpose="user_data") → file_id
                │
   Pass 1  muse-spark-1.2 (video+embedded audio, structured output)
           → event timeline: [{t, screen, action, field, quote, source: seen|said}]
                │
   Pass 2  muse-wonder-1.0 (reasoning=high), timeline-only, JSON schema
           → Playbook {steps[{t_start, t_end, text, source: seen|said|inferred,
                       evidence_quote}], decisions, open_questions}
           Rule: a branch with no evidence becomes an open_question, never a step
                │
   Pass 3  Validation (code): every step has a timestamp inside the video;
           "seen"/"said" steps must have matching timeline evidence or are
           downgraded to "inferred"
                │
   Pass 4  SAM 3.1 (optional pointer): keyframe at step t + field label
           → outline overlay in the player
                │
   Exporters (code, not LLM): playbook Markdown/PDF with citations, Mermaid flow
                │
   UI: player | Steps (source badges) | Flow | Open questions — click a step → seek video
```
- Stack: Python FastAPI backend + one React/Vite page. Run jobs on Modal (use the $100 credits).
- Fallback: if video input has size or duration limits, sample keyframes every 2s as images and send the narration separately: extract the audio track to WAV with ffmpeg and pass it as `input_audio`, or transcribe it with Muse Voice Transcribe and send the transcript with the frames.

## Verified API constraints (dev.meta.ai docs)
- Video input: `video/mp4` only, uploaded via Files API (`purpose="user_data"`), referenced by `file_id` as `input_file`/`input_video`. Audio input: MP3 or WAV as `input_audio`.
- **Audio understanding on muse-spark-1.3 is degraded** ("not fully supported" per docs). Use `muse-spark-1.2` for anything involving narration, or Muse Wonder.
- Reasoning shares the output budget. Set `max_output_tokens` ≥ 4000 or responses can come back empty (`finish_reason: length`).
- Stream (`stream: true`) on long videos to avoid idle-timeout disconnects.
- SAM 3.1 video accepts MP4/MOV (H.264/H.265/MPEG-4); one noun phrase per request; use `@meta-sam/parser` for box/mask decoding.
- Docs do not state duration/size limits — the night-one probe must measure them.

## Scope guard
Must: upload → timeline → cited playbook with Seen/Said/Inferred → flow with open questions → click-to-seek → playbook + flow export → **live deployed URL** → **public repo**.
Should: Voice Transcribe check of "Said" quotes; SAM 3.1 pointer; open-weights mode (bonus).
Stretch: "Replay" agent (bonus).
Won't (this hackathon): data model, checklist, JSON spec, merging recordings, live capture, auth.

## Day plan
| Day | Date | Goal |
|---|---|---|
| 1 | Thu 29 Oct | ✅ Pipeline, evidence check, exporters, API, tests, demo prop, review UI. ✅ Baseten credits requested. To do: Meta/Modal/Fireworks accounts + credit forms; record take A; run `probe.py` (timestamp gate) |
| 1b | Thu 29 Oct (late) | ✅ Built ahead: Voice Transcribe check of "Said" quotes, SAM 3.1 pointer, open-weights mode (Muse Spark Open, OpenAI-compatible), JSON retry, Modal deploy file. 14 tests pass |
| 2a | Fri 30 Oct (am) | ✅ **Gate test passed** on a synthetic take with known timings: muse-spark-1.2 placed visible actions within ~1 s, narration verbatim, 10 s per call → single-call mode. Found spoken-line times drift up to ~9 s → said events now snap to Voice Transcribe turns. SAM can't read labels → pointer is now Spark locates + SAM refines (pixel-exact). Prompt tuned: 6 steps, decisions with branches, narration/screen conflict flagged |
| 2 | Fri 30 Oct | Real run on take A; tune Pass 1/2 prompts. ✅ Public repo live: github.com/mukeshkbj/shadow (2 commits). ✅ Upload caps added for the public URL (200 MB / 25 jobs). Watch the Fireworks session (12:00 ET) |
| 3 | Sat 31 Oct | Tune transcript check + SAM noun phrases on real output; deploy to Modal (live URL) |
| 4 | Sun 1 Nov | Run open-weights mode for real once Baseten/Fireworks/Modal credits arrive |
| 5 | Mon 2 Nov | Record take B (shows it isn't hard-coded); polish UI. ✅ Replay built early (`shadow/replay.py` + `scripts/replay.py`): agent re-runs a confirmed playbook on the prop, stops at unconfirmed steps and unshown branches to ask. Needs `playwright install chromium` + a real take before a live run |
| 6 | Tue 3 Nov | Hardening, cached results, README with "Built during the hackathon"; last day for technical help. Stretch: Replay agent |
| 7 | Wed 4 Nov | 3-min demo video, submit by 20:00 GMT, post the X cut, share the gallery link |

## Demo script (3 min)
1. 0:00 Hook: "An AI-written SOP you can't check is worse than none. Shadow shows its working."
2. 0:15 Play 10s of the raw refund recording (screen + voice).
3. 0:30 Playbook appears: each step with timestamp and Seen / Said / Inferred badge. Click a "Said" rule → video jumps to the moment it was said.
4. 1:10 An "Inferred" step: show why it's flagged; confirm it with one click.
5. 1:40 Flow diagram: the unshown branch is an open question, not a guess. Answer it in a sentence.
6. 2:15 Pointer: the field outline helps find the moment; the recording is the proof.
7. 2:35 Export the cited playbook. Close: same workflow for any team, next steps.

## Risks
- **Timestamps are wrong or missing** (seek-to-evidence dies) → slice the video into fixed windows (e.g. 30s), process each, and label events with the window's known offset. Timestamps become trustworthy by construction, at the cost of more calls.
- Video limits or latency → keyframe + `input_audio` fallback; precompute the demo results.
- Over-confident steps → schema forces `source`; validation downgrades unsupported Seen/Said to Inferred; branches without evidence become open questions.
- Narration quality poor even on spark-1.2 → transcribe with Muse Voice Transcribe first, feed transcript + video.
- **Live URL exposes a paid upload endpoint** (anyone can POST an MP4 that burns your key) → cap upload size and max jobs before deploying, or gate uploads behind a demo token.
- Baseten credit not granted or Spark Open path slips → run Muse Spark Open via Modal Endpoints or vLLM instead; the open-weights bonus only needs the weights, not Baseten specifically.
- Sensitive data → synthetic data only; mention PII redaction as next step.

## Alternatives considered
- **Collections call vulnerability co-pilot** (audio-native). Overlaps with my Accel AI Innovate entry; check the rules on reusing work.
- Devin's shortlist: Fix-It (visual repair with SAM tracking), Reviewer (semantic visual diff), Narrator (scene describer). Shadow chosen as stronger and closer to firsthand experience.
