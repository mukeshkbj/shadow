# Shadow — progress

Hackathon: Meta Global AI Developer Hackathon. Deadline: Wed 4 Nov 2026, 9:00 PM ET (Thu 5 Nov 02:00 GMT). Internal target: submit by 20:00 GMT on 4 Nov. Repo: github.com/mukeshkbj/shadow (public).

## Done and verified

- Full pipeline: upload MP4 → Muse Spark 1.2 timeline (seen/said) → Muse Voice Transcribe check → Muse Wonder 1.0 playbook → deterministic evidence check → Muse+SAM pointers → review UI → Markdown/Mermaid export.
- Upload guards for the public URL: `SHADOW_MAX_UPLOAD_MB` (200), `SHADOW_MAX_JOBS` (25).
- Open-weights path (`--provider open`, Baseten `meta-models/muse-spark-open`, /chat/completions). Not yet run with real credits.
- Replay stretch: `backend/shadow/replay.py` (playwright-free, duck-typed page), `scripts/replay.py` CLI (headed Chromium on `demo-prop/index.html`, `--auto` answers "stop"). Pauses on unconfirmed steps and unshown branches; writes `replay_log.json` + `replay/step_NN.png` into the job dir.
- Replay tab in the review UI: log + screenshots via `/api/jobs/{id}/replay` and `/replay/shots/{name}`. Rendered and inspected — seeded-log screenshot verified layout (stopped notice, action rows, pills, expert questions).
- Real end-to-end run on `recordings/take-synthetic.mp4`: planted conflict correctly `inferred`, both said rules transcript-verified, 5/6 steps have SAM pointers, 4 open questions.
- Tests: 23 passed, 1 warning (Starlette/httpx deprecation).

## Not yet done

- Take A recording per `demo-prop/RECORDING.md` → `recordings/take-a.mp4` → `python scripts/run_job.py recordings/take-a.mp4`. Then Take B (different customer/outcome).
- Real Replay run: `python scripts/replay.py synthetic --auto` (Playwright + Chromium installed in `backend/.venv`; needs `MODEL_API_KEY`).
- Modal deploy: `pip install modal`, `modal setup`, `modal secret create shadow-secrets MODEL_API_KEY=...`, `.\deploy.ps1`. Then smoke-test the public URL (health, upload caps, sample job, video, exports).
- Open-weights run once provider credits arrive.
- 3-minute demo video; 30–45 s social cut if pursuing the viral bonus; devpost submission before internal target.

## Watch items

- Port 8000 on this machine serves something else (not Shadow); use another port for local runs.
- `frontend/nul` was created once by a bash `2>nul` redirect — avoid `nul` redirections in bash; it is a real file here.
- Evidence framing: "consistency-checked and human-verifiable", never "verified". Pass 3 checks against Pass 1's own log.
- Voice Transcribe timestamps are turn-level, not word-level.
- PLAN.md holds the schedule; this file holds the state.

## 3 Nov (evening): competition-readiness pass (uncommitted, not deployed)

Done and verified:
- Public deploy keeps each visitor's review private. Before this, any judge who clicked Confirm or answered a question changed the featured run for every later judge. Edits now go to `jobs/<id>/reviews/<browser id>.json` when `SHADOW_UPLOAD_PASSCODE` is set (capped at 2000 per job); local runs still write `playbook.json`, so `scripts/replay.py` is unchanged. Test: `test_public_deploy_keeps_each_visitors_review_private`.
- Review page: "Try it" note, "Start over" control, and the reason a step needs the expert ("Why it needs you") shown on the flagged step, so the oldest-first vs newest-first conflict is in the first screen.
- Export and Review: loading and error states (Export used to render a blank page). Global `:focus-visible` ring. Share-preview meta tags. Phone layout: timeline ruler labels no longer overlap.
- Evidence: 28 tests pass; `npm run build` passes; checked in a browser at 1280x800 and 390x844 against a local server with a passcode set (confirm, start over, bad job id).

Needs approval (external actions):
- Commit and push; then `npm run build` and `.\deploy.ps1` so the live site gets the fix before judging starts (4 Nov).
- After deploy: open the featured run, confirm step 1 in one browser, check that a second browser still sees it as Inferred.

## 3 Nov (late): signature interaction (uncommitted, not deployed)

Done and verified:
- **Screen vs Voice card.** An Inferred step that cites both a screen event and a narration event opens as a two-sided card (prompts.py already requires a conflict to be Inferred and to cite both sides). "Watch it" plays the screen moment for 4 s; "Hear it" plays the exact Voice Transcribe turn and pauses at its end. The expert picks "Follow the screen", "Follow the voice" or writes the rule; the choice is saved as the step text and marks it confirmed, so Replay and the export use it. The card sits in the step list beside the video at 1108 px and wider, and under the video below that.
- The selected step's cited events light up on the Screen and Voice lanes of the timeline. "1 needs you" in the trust bar jumps to the flagged step. Tabs support arrow keys and have a tabpanel. The home page states the demo conflict under the call to action. The hero image is a new capture of the real review screen (frame at 00:07 of the featured run).
- Evidence: 28 tests pass; build passes. Local server with a passcode set, checked at 1440x900, 1024x800 and 390x844: "Hear it" played from 2.3 s and paused at 7.84 s (turn end 7.82 s); "Follow the screen" changed the private copy and its export, while the base playbook stayed "Select a refund request from the Refunds inbox", unconfirmed; arrow keys moved focus Steps to Flow and back; no horizontal scroll at 390 px.
- Known ceiling: an Inferred step that cites a seen and a said event without a real disagreement would also show as "Screen and voice disagree". All three real runs have exactly one such step, and it is the planted conflict.

## 3 Nov (night): conflict as a first-class record; shipped

- `evidence.conflict()` is now the one rule for "screen and voice disagree" (an Inferred step the model marked itself, citing a seen and a said event; steps the check downgraded are excluded). The API returns `conflicts` with every playbook; the UI card, the Markdown export and the Mermaid export all use it.
- `Step.resolution` (`screen` | `voice` | `expert`) records how the expert settled it. The Markdown export writes both sides with times and the decision; every timestamp links to `#/job/<id>?t=<s>`, which opens the review at that second.
- Security: on the public deploy an edit without a valid reviewer id now gets 400, so no request can change the shared run (before, a request without the header wrote to it).
- `deploy.ps1` no longer replaces the `shadow-secrets` secret unless `MODEL_API_KEY` is set, and then it keeps `SHADOW_UPLOAD_PASSCODE` and the open-weights key. Before, a plain run would have deleted the passcode and both keys from the live app.
- Evidence: 31 tests pass; build passes; local review at 1440x900 and 390x844 (deep link `?t=50` opens step 5 at 50 s; "Follow the screen" writes the decision line into the export; header-less PATCH returns 400; open-weights run shows the same card).
