# Shadow

**Shadow turns an expert's screen recording and narration into a reviewable playbook, with every step tied to its source and every assumption called out.**

Built for the Meta Global AI Developer Hackathon (Indie track, *Build for Your World*).

**Live:** https://mukeshkbj--shadow-web.us-east.modal.run. The sample playbooks are open to everyone. Uploading a new recording needs a passcode, because each upload spends API credits.

## What it does
1. Someone records their screen while doing a task and talks as they go.
2. **Muse Spark** watches the video *with* its audio and logs what was **seen** on screen and what was **said**, with timestamps.
3. **Muse Wonder** drafts a step-by-step playbook from that log. Every step is labelled **Seen**, **Said** or **Inferred**, and branches nobody showed become **open questions**, not guesses.
4. A deterministic **evidence check** (plain code, no AI) verifies every step against the log. A step with no evidence is removed and turned into a question. A "Said" step whose words weren't heard is downgraded to Inferred.
   - **Muse Voice Transcribe** gives a second, independent check: a "Said" quote must appear in the narration turn spoken at that time. Spoken events also take their time from the transcript, because in testing Spark's times for spoken lines drifted by up to 9 s while screen actions were within about a second.
   - **Muse Spark + SAM 3.1** make a visual pointer for the reviewer: SAM can't read text labels, so Spark finds the field by its label and SAM 3.1 outlines it precisely. It's a pointer, not proof.
5. The expert reviews: click any step to jump to that moment in the video, confirm or fix inferred steps, answer open questions.
6. Export a cited playbook (Markdown) and a flow diagram (Mermaid).

## Measured accuracy
We scripted a recording of the demo app with known timings (`recordings/take-synthetic.ground_truth.json`) so timestamps could be scored, not eyeballed. Muse Spark 1.2, one call, 87-second clip:

| What | Average error | Worst |
|---|---|---|
| On-screen actions (6 clicks/typing) | **0.5 s** | 1 s |
| Spoken lines, timed by Muse Spark | 6.4 s | 14.5 s |
| Spoken lines, snapped to Muse Voice Transcribe turns | **0.3 s** | 0.5 s |

That gap is why spoken events take their time from the transcript. One silent action (choosing an email template) was missed; Shadow doesn't invent it.

## Run it (Windows)
Needs Python 3.10+, Node 18+ and ffmpeg on PATH.

```powershell
# backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:MODEL_API_KEY = "<your Meta Model API key>"   # leave unset to use the offline sample only
uvicorn shadow.api:app --reload --port 8000

# UI (second terminal)
cd frontend
npm install
npm run dev        # http://localhost:5173
# or: npm run build, then open http://localhost:8000 (the API serves the built UI)
```

### Settings (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| `MODEL_API_KEY` | (unset) | Meta Model API key. Unset = offline sample only |
| `SHADOW_TIMELINE_MODEL` | `muse-spark-1.2` | Pass 1. 1.2 because audio on 1.3 is "not fully supported" |
| `SHADOW_PLAYBOOK_MODEL` | `muse-wonder-1.0` | Pass 2 |
| `SHADOW_WINDOW_SECONDS` | `0` | `0` = whole video in one call; `30` = 30-second windows (timestamps correct by construction) |
| `SHADOW_MAX_OUTPUT_TOKENS` | `12000` | Min 4000: reasoning shares the output budget |
| `SHADOW_TRANSCRIBE` | `1` | Check "Said" quotes against Muse Voice Transcribe turns (`0` = off) |
| `SHADOW_POINTER` | `1` | Add SAM 3.1 visual pointers (`0` = off) |
| `SHADOW_OPEN_BASE_URL` | (unset) | Open-weights mode host, e.g. `https://inference.baseten.co/v1` |
| `SHADOW_OPEN_API_KEY` | (unset) | Key for that host |
| `SHADOW_UPLOAD_PASSCODE` | (unset) | If set, uploads need this passcode (viewing stays open) |
| `SHADOW_OPEN_MODEL` | `meta-models/muse-spark-open` | Muse Spark Open model ID on that host |

### Tests
```powershell
cd backend; python -m pytest -q
```
Includes a full pipeline run against a fake Meta API with a generated video, which checks windowing, timestamp offsets and the evidence rules.

## Open-weights mode
Pick **Open weights** on the upload screen to run both passes on **Muse Spark Open** through any OpenAI-compatible host (Baseten, Fireworks, Modal). Hosts ignore the audio inside a video, so each 30-second window is sent as a video part plus a separate WAV audio part.

## Replay (stretch): the agent does the job back
Once the expert has confirmed the playbook, Shadow can **re-run it** in the app it was recorded in.
An agent loop shows Muse Spark the live page (screenshot + DOM snapshot) plus the rules the expert
said aloud, and performs each step itself. It stops — rather than guesses — at any step still
unconfirmed, and at any branch the recording never showed, and asks the expert before continuing.

```powershell
cd backend; .venv\Scripts\pip install playwright; .venv\Scripts\python -m playwright install chromium
cd ..
python scripts\replay.py <job_id>            # headed browser; answers prompts in the terminal
python scripts\replay.py <job_id> --auto     # skip every unconfirmed/unshown stop (unattended)
```

Screenshots and `replay_log.json` land in the job's `replay/` folder. Playwright is an optional,
local-only dependency — it is not in `requirements.txt` and not in the deployed app.

## Deploy (Modal)
From PowerShell in this folder: `.\deploy.ps1` (set `$env:MODEL_API_KEY` first so uploads work live). It links your Modal account the first time, stores the settings as the `shadow-secrets` secret, builds the UI and deploys. Details are in `modal_app.py`.

## Demo data
`demo-prop/index.html` is a fictional shop back office with made-up orders, used for the demo recording. `demo-prop/RECORDING.md` is the narration script. No real customer data is used anywhere.

## Built during the hackathon
All code in this repository was written during the hackathon building period (from 29 Oct 2026): pipeline, evidence check, exporters, API, review UI, demo prop and tests.

## Project layout
```
backend/shadow/   passes.py (Pass 1, 2) · evidence.py (Pass 3) · providers.py (Meta API / open weights)
                  transcribe.py (Voice Transcribe) · pointer.py (SAM 3.1) · replay.py (agent re-run)
                  exporters.py · muse.py · api.py
modal_app.py      Modal deployment
backend/fixtures/ sample timeline + draft playbook (offline sample)
frontend/src/     review UI (React + Vite)
demo-prop/        fictional refunds desk to record
scripts/probe.py  timestamp gate test against the real API
scripts/replay.py Replay: drives the demo prop through a confirmed playbook (Playwright + Muse)
```
