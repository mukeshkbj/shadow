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
