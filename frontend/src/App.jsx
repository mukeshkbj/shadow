import React, { useEffect, useRef, useState } from "react";
import { api, ts } from "./api.js";

function useHash() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const on = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return hash;
}
const go = (h) => { window.location.hash = h; };

const Logo = () => (
  <a href="#/" className="logo">
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><circle cx="14" cy="14" r="12" fill="#12151B" /><circle cx="17.5" cy="14" r="7" fill="#C2410C" /></svg>
    <span>Shadow</span>
  </a>
);

const SOURCE_LABEL = { seen: "Seen", said: "Said", inferred: "Inferred" };
function Badge({ step }) {
  const kind = step.source === "inferred" && step.confirmed ? "confirmed" : step.source;
  const label = kind === "confirmed" ? "Confirmed" : SOURCE_LABEL[step.source];
  return <span className={`badge badge-${kind}`}>{label}</span>;
}

export default function App() {
  const hash = useHash();
  const m = hash.match(/^#\/job\/([\w-]+)(?:\/(processing|export))?/);
  if (!m) return <Home />;
  const [, id, view] = m;
  if (view === "processing") return <Processing id={id} />;
  if (view === "export") return <Export id={id} />;
  return <Review id={id} />;
}

/* ---------------- Home / upload ---------------- */
function Home() {
  const [jobs, setJobs] = useState([]);
  const [health, setHealth] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [provider, setProvider] = useState("muse");
  useEffect(() => {
    api.jobs().then(setJobs).catch(e => setErr(e.message));
    api.health().then(h => { setHealth(h); if (h.providers?.length && !h.providers.includes("muse")) setProvider(h.providers[0]); }).catch(() => {});
  }, []);

  const send = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".mp4")) { setErr("Please choose an MP4 file."); return; }
    setBusy(true); setErr("");
    try { const { id } = await api.upload(file, provider); go(`#/job/${id}/processing`); }
    catch (e) { setErr(e.message); setBusy(false); }
  };

  return (
    <div className="page">
      <header className="bar"><Logo /></header>
      <main className="narrow stack-lg">
        <div className="stack-sm">
          <h1 className="h1">Show Shadow how the job is done</h1>
          <p className="lede">Record your screen while you do the task, and talk as you go. Shadow turns it into a playbook you can check: every step tied to the moment it came from, every assumption flagged.</p>
        </div>
        {health && !health.providers?.length && (
          <div className="notice">No model is configured, so new recordings can't be processed yet. The sample playbook below works offline. Set <code>MODEL_API_KEY</code> and restart the server.</div>
        )}
        {health?.providers?.length > 0 && (
          <fieldset className="engine">
            <legend className="eyebrow">Run on</legend>
            {[["muse", "Meta Model API", "Muse Spark watches and listens, Muse Wonder writes, Voice Transcribe and SAM 3.1 check"],
              ["open", "Open weights", `Muse Spark Open on your own host${health.open_model ? ` (${health.open_model})` : ""}`]].map(([k, t, d]) => (
              <label key={k} className={`engine-opt ${provider === k ? "on" : ""} ${health.providers.includes(k) ? "" : "off"}`}>
                <input type="radio" name="engine" value={k} checked={provider === k} disabled={!health.providers.includes(k)} onChange={() => setProvider(k)} />
                <span className="stack-0"><strong>{t}</strong><span className="muted small">{health.providers.includes(k) ? d : "Not configured on this server"}</span></span>
              </label>
            ))}
          </fieldset>
        )}
        <div className={`drop ${drag ? "drag" : ""}`}
             onDragOver={e => { e.preventDefault(); setDrag(true); }}
             onDragLeave={() => setDrag(false)}
             onDrop={e => { e.preventDefault(); setDrag(false); send(e.dataTransfer.files[0]); }}>
          <div className="drop-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#C2410C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 16V4" /><path d="M6 10l6-6 6 6" /><path d="M4 20h16" /></svg></div>
          <div className="stack-xs center"><strong className="big">Drop a screen recording here</strong><span className="muted">MP4 with sound · one task, a few minutes long</span></div>
          <div className="row center">
            <label className="btn btn-dark">{busy ? "Uploading…" : "Choose a file"}
              <input type="file" accept="video/mp4" className="sr-only" disabled={busy} onChange={e => send(e.target.files[0])} />
            </label>
            <a className="btn" href="#/job/sample">Open the sample playbook</a>
          </div>
          {err && <p className="error" role="alert">{err}</p>}
        </div>
        <div className="grid3">
          {[["01", "Do the task for real", "One case, start to finish. Use test data if the real thing is sensitive."],
            ["02", "Say why, not just what", "“Over 30 days is store credit only.” Rules like that are what Shadow listens for."],
            ["03", "Don't worry about gaps", "Anything you don't show comes back as a question, not a guess."]].map(([n, t, d]) => (
            <div className="card stack-xs" key={n}><span className="mono accent">{n}</span><strong>{t}</strong><span className="muted small">{d}</span></div>
          ))}
        </div>
        <section className="stack-sm">
          <h2 className="h2">Your playbooks</h2>
          <div className="card flush">
            {jobs.length === 0 && <div className="pad muted">Nothing yet.</div>}
            {jobs.map(j => (
              <a key={j.id} className="job-row" href={j.state === "done" ? `#/job/${j.id}` : `#/job/${j.id}/processing`}>
                <strong className="grow">{j.title || j.filename}</strong>
                {j.counts && <span className="muted small">{j.counts.seen + j.counts.said + j.counts.inferred} steps · {j.counts.to_confirm} to confirm · {j.counts.open_questions} open questions</span>}
                <span className={`pill pill-${j.state}`}>{j.state === "done" ? (j.counts && (j.counts.to_confirm || j.counts.open_questions) ? "In review" : "Ready") : j.state === "error" ? "Failed" : "Processing"}</span>
              </a>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

/* ---------------- Processing ---------------- */
const STAGE_TEXT = {
  timeline: ["Watching and listening", "Logging what happened on screen and what was said, with times"],
  playbook: ["Writing the playbook", "Grouping moments into steps and decisions, with their sources"],
  evidence: ["Checking the evidence", "Every step must match the recording, or it's flagged or becomes a question"],
  done: ["Ready to review", ""],
};
function Processing({ id }) {
  const [st, setSt] = useState(null);
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const s = await api.job(id);
        if (!alive) return;
        setSt(s);
        if (s.state === "done") { go(`#/job/${id}`); return; }
        if (s.state !== "error") setTimeout(tick, 1500);
      } catch { if (alive) setTimeout(tick, 3000); }
    };
    tick();
    return () => { alive = false; };
  }, [id]);
  const order = ["timeline", "playbook", "evidence"];
  const cur = st ? order.indexOf(st.stage) : -1;
  return (
    <div className="page">
      <header className="bar"><Logo /><a className="btn" href="#/">Back</a></header>
      <main className="narrow stack-lg">
        <div className="stack-sm">
          <span className="mono muted">{st?.filename}</span>
          <h1 className="h1">{st?.state === "error" ? "Something went wrong" : "Watching your recording"}</h1>
          <p className="lede">{st?.state === "error" ? st.detail : "You can leave this page. We'll keep going."}</p>
        </div>
        <ol className="card flush stages">
          {order.map((k, i) => {
            const state = st?.state === "error" && i === Math.max(cur, 0) ? "error" : i < cur || st?.stage === "done" ? "done" : i === cur ? "active" : "todo";
            return (
              <li key={k} className={`stage stage-${state}`}>
                <span className="stage-dot" aria-hidden="true">{state === "done" ? "✓" : ""}</span>
                <div className="stack-xs"><strong>{STAGE_TEXT[k][0]}</strong><span className="muted small">{state === "active" && st?.detail ? st.detail : STAGE_TEXT[k][1]}</span></div>
              </li>
            );
          })}
        </ol>
      </main>
    </div>
  );
}

/* ---------------- Review ---------------- */
function Review({ id }) {
  const [pb, setPb] = useState(null);
  const [job, setJob] = useState(null);
  const [err, setErr] = useState("");
  const [sel, setSel] = useState(0);
  const [tab, setTab] = useState("steps");
  const [now, setNow] = useState(0);
  const video = useRef(null);

  useEffect(() => {
    api.playbook(id).then(setPb).catch(e => setErr(e.message));
    api.job(id).then(setJob).catch(() => {});
  }, [id]);

  if (err) return <div className="page"><header className="bar"><Logo /></header><main className="narrow"><p className="error">{err}</p></main></div>;
  if (!pb) return <div className="page"><header className="bar"><Logo /></header><main className="narrow muted">Loading…</main></div>;

  const steps = pb.steps;
  const cur = steps[sel] || steps[0];
  const c = pb.counts;
  const pick = (i) => {
    setSel(i);
    if (video.current && steps[i]) { video.current.currentTime = steps[i].t_start; }
  };
  const update = (p) => p.then(setPb).catch(e => setErr(e.message));

  return (
    <div className="page">
      <header className="bar wrap">
        <div className="row">
          <Logo />
          <span className="divider" />
          <div className="stack-0"><strong>{pb.title}</strong><span className="muted small">{job?.sample ? "Sample · synthetic data · " : ""}{ts(pb.duration)} recording{job?.provider === "open" ? " · run on open weights (Muse Spark Open)" : ""}</span></div>
        </div>
        <div className="row">
          <div className="legend small">
            <span><i className="key key-seen" />{c.seen} seen</span>
            <span><i className="key key-said" />{c.said} said</span>
            <span><i className="key key-inferred" />{c.to_confirm} to confirm</span>
            <span><b className="accent">?</b> {c.open_questions} open questions</span>
          </div>
          <a className="btn btn-dark" href={`#/job/${id}/export`}>Export playbook</a>
        </div>
      </header>

      <main className="split">
        <section className="col-main stack-md" aria-label="Recording">
          <div className="player">
            {job?.has_video ? (
              <div className="video-wrap">
                <video ref={video} src={api.videoUrl(id)} controls preload="metadata"
                       onTimeUpdate={e => {
                         const t = e.currentTarget.currentTime;
                         setNow(t);
                         let i = 0; steps.forEach((s, k) => { if (s.t_start <= t + 0.25) i = k; });
                         if (i !== sel) setSel(i);
                       }} />
                {cur.pointer && now >= cur.t_start - 0.5 && now <= (cur.t_end ?? cur.t_start + 8) && (
                  <div className="pointer" aria-hidden="true" style={{
                    left: `${(cur.pointer.x1 / cur.pointer.w) * 100}%`, top: `${(cur.pointer.y1 / cur.pointer.h) * 100}%`,
                    width: `${((cur.pointer.x2 - cur.pointer.x1) / cur.pointer.w) * 100}%`, height: `${((cur.pointer.y2 - cur.pointer.y1) / cur.pointer.h) * 100}%`,
                  }}><span>Pointer</span></div>
                )}
              </div>
            ) : (
              <div className="player-empty">
                <strong>No recording attached to the sample</strong>
                <span>Record take A from <code>demo-prop/RECORDING.md</code> and save it as <code>backend/fixtures/sample.mp4</code> to see the video here.</span>
              </div>
            )}
            <div className="track" aria-hidden="true">
              <div className="track-fill" style={{ width: `${(cur.t_start / (pb.duration || 1)) * 100}%` }} />
              {steps.map((s, i) => <span key={s.id} className={`tick tick-${s.source}`} style={{ left: `${(s.t_start / (pb.duration || 1)) * 100}%` }} />)}
            </div>
          </div>

          <div className="card stack-sm">
            <div className="row">
              <span className="eyebrow">Evidence for step {sel + 1}</span>
              <span className="mono chip">{ts(cur.t_start)}{cur.t_end != null ? `–${ts(cur.t_end)}` : ""}</span>
              <Badge step={cur} />
            </div>
            <p className="m0">{cur.evidence || "—"}</p>
            {cur.quote && <blockquote className="quote">“{cur.quote}”</blockquote>}
            {cur.quote_check && <p className="m0 small ok">✓ Matches the narration transcript at {ts(cur.quote_check.start)}–{ts(cur.quote_check.end)} (Muse Voice Transcribe)</p>}
            {cur.downgraded_reason && <p className="m0 small warn"><strong>Evidence check:</strong> {cur.downgraded_reason} So this step is marked inferred.</p>}
            {cur.field && <p className="m0 small muted">On screen: <strong>{cur.field}</strong>{cur.pointer ? " (outlined on the video by SAM 3.1 as a pointer)" : ""}. The timestamped recording is the evidence.</p>}
          </div>
        </section>

        <section className="col-side card flush" aria-label="Playbook">
          <div role="tablist" aria-label="Playbook views" className="tabs">
            {[["steps", "Steps"], ["flow", "Flow"], ["questions", `Open questions · ${c.open_questions}`], ["replay", "Replay"]].map(([k, l]) => (
              <button key={k} role="tab" aria-selected={tab === k} className={`tab ${tab === k ? "on" : ""}`} onClick={() => setTab(k)}>{l}</button>
            ))}
          </div>
          {tab === "steps" && (
            <ol className="steps">
              {steps.map((s, i) => (
                <li key={s.id} className={`step ${i === sel ? "on" : ""}`}>
                  <button className="step-main" onClick={() => pick(i)}>
                    <span className="stack-0 step-time"><span className="mono">{ts(s.t_start)}</span><span className="muted xsmall">Step {i + 1}</span></span>
                    <span className="stack-0 grow"><strong>{s.text}</strong><span className="muted small">{s.detail}</span></span>
                    <Badge step={s} />
                  </button>
                  {s.source === "inferred" && !s.confirmed && <StepReview s={s} onConfirm={() => update(api.editStep(id, s.id, { confirmed: true }))} onFix={(text) => update(api.editStep(id, s.id, { text }))} />}
                  {s.source === "inferred" && s.confirmed && <div className="step-note ok small">Confirmed by the expert · was inferred</div>}
                </li>
              ))}
            </ol>
          )}
          {tab === "flow" && <Flow pb={pb} onPick={(sid) => { const i = steps.findIndex(s => s.id === sid); if (i >= 0) { pick(i); setTab("steps"); } }} />}
          {tab === "questions" && <Questions pb={pb} onAnswer={(qid, a) => update(api.answer(id, qid, a))} />}
          {tab === "replay" && <Replay id={id} steps={steps} />}
          {pb.notes?.length > 0 && tab === "steps" && (
            <details className="notes small"><summary>Evidence check log ({pb.notes.length})</summary><ul>{pb.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></details>
          )}
        </section>
      </main>
    </div>
  );
}

function StepReview({ s, onConfirm, onFix }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(s.text);
  if (editing) return (
    <form className="step-note row" onSubmit={e => { e.preventDefault(); onFix(text); }}>
      <label className="sr-only" htmlFor={`fix-${s.id}`}>Step wording</label>
      <input id={`fix-${s.id}`} className="input grow" value={text} onChange={e => setText(e.target.value)} autoFocus />
      <button className="btn btn-dark" type="submit">Save</button>
      <button className="btn" type="button" onClick={() => setEditing(false)}>Cancel</button>
    </form>
  );
  return (
    <div className="step-note row">
      <button className="btn btn-dark" onClick={onConfirm}>Confirm</button>
      <button className="btn" onClick={() => setEditing(true)}>Fix wording</button>
    </div>
  );
}

function Flow({ pb, onPick }) {
  const byId = Object.fromEntries(pb.steps.map(s => [s.id, s]));
  const qs = Object.fromEntries(pb.open_questions.map(q => [q.id, q]));
  const decisions = Object.fromEntries(pb.decisions.map(d => [d.step_id, d]));
  return (
    <div className="flow">
      {pb.steps.map((s, i) => {
        const d = decisions[s.id];
        return (
          <React.Fragment key={s.id}>
            {i > 0 && <div className="flow-line" />}
            <button className={`flow-node ${d ? "flow-decision" : ""} ${s.source === "inferred" && !s.confirmed ? "flow-inferred" : ""}`} onClick={() => onPick(s.id)}>
              <span>{d ? d.question : s.text}</span>
              <span className="mono xsmall muted">{SOURCE_LABEL[s.source].toLowerCase()} · {ts(s.t_start)}</span>
            </button>
            {d && (
              <div className="flow-branches">
                {d.branches.map((b, k) => (
                  <div key={k} className="flow-branch">
                    <span className="flow-label">{b.label}</span>
                    {b.next_step_id && byId[b.next_step_id] && <span className="flow-target">→ {byId[b.next_step_id].text}</span>}
                    {!b.next_step_id && b.open_question_id && qs[b.open_question_id] && (
                      <span className={`flow-target flow-open ${qs[b.open_question_id].answer ? "answered" : ""}`}>
                        <b className="accent">?</b> {qs[b.open_question_id].question}{qs[b.open_question_id].answer ? ` — ${qs[b.open_question_id].answer}` : " (not shown)"}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function Questions({ pb, onAnswer }) {
  return (
    <div className="pad stack-sm">
      <p className="m0 muted small">These weren't shown in the recording, so Shadow hasn't filled them in. Answer in a sentence.</p>
      {pb.open_questions.map(q => <Question key={q.id} q={q} onAnswer={onAnswer} />)}
    </div>
  );
}
function Question({ q, onAnswer }) {
  const [val, setVal] = useState("");
  return (
    <div className={`question stack-xs ${q.answer ? "answered" : ""}`}>
      <strong><span className="accent">?</span> {q.question}</strong>
      {q.why && <span className="muted small">{q.why}{q.related_t != null ? ` (${ts(q.related_t)})` : ""}</span>}
      {q.answer ? <span className="ok small">Answered: {q.answer}</span> : (
        <form className="row" onSubmit={e => { e.preventDefault(); if (val.trim()) onAnswer(q.id, val); }}>
          <label className="sr-only" htmlFor={`a-${q.id}`}>Answer</label>
          <input id={`a-${q.id}`} className="input grow" placeholder="Type an answer" value={val} onChange={e => setVal(e.target.value)} />
          <button className="btn btn-accent" type="submit">Save answer</button>
        </form>
      )}
    </div>
  );
}

function Replay({ id, steps }) {
  const [log, setLog] = useState(undefined);
  useEffect(() => { setLog(undefined); api.replay(id).then(setLog).catch(() => setLog(null)); }, [id]);
  if (log === undefined) return <div className="pad muted">Loading…</div>;
  if (!log) return (
    <div className="pad stack-xs muted">
      <strong>No replay for this job yet.</strong>
      <span>After confirming the playbook, run <code>python scripts/replay.py {id}</code>. The agent re-runs it in the app it came from, and stops to ask at anything unconfirmed or unshown.</span>
    </div>
  );
  const indexOf = Object.fromEntries(steps.map((s, i) => [s.id, i + 1]));
  return (
    <div className="pad stack-md">
      {log.stopped && <div className="notice small">Stopped: {log.stopped}</div>}
      {log.actions.map((x, i) => {
        const shot = indexOf[x.step] ? api.replayShotUrl(id, `step_${String(indexOf[x.step]).padStart(2, "0")}.png`) : null;
        return (
          <div key={i} className="stack-xs" style={{ borderBottom: "1px solid var(--line)", paddingBottom: 12 }}>
            <div className="row" style={{ gap: 10, alignItems: "baseline" }}>
              <span className="mono xsmall muted">{x.step}</span>
              <span className="grow">
                {x.decision ? <>Decision — {x.decision} → <b>{x.chose}</b></>
                  : x.skipped ? <span className="muted"><s>{x.text}</s> skipped</span>
                  : <b>{x.text}</b>}
                {(x.error || x.why) && <span className="muted small"> — {x.error || x.why}</span>}
              </span>
              <span className={`pill ${x.ok === false ? "pill-error" : x.skipped ? "" : "pill-done"}`}>
                {x.skipped ? "skipped" : x.decision ? "decision" : x.ok === false ? "failed" : "done"}
              </span>
            </div>
            {x.action && !["none", "check"].includes(x.action) &&
              <span className="mono xsmall muted">{x.action} {x.selector}{x.value ? ` = ${x.value}` : ""}</span>}
            {shot && <img src={shot} alt="" onError={e => e.currentTarget.remove()}
                          style={{ maxWidth: "100%", borderRadius: 8, border: "1px solid var(--line)" }} />}
          </div>
        );
      })}
      {log.asked?.length > 0 && (
        <div className="stack-xs">
          <strong className="small">Asked the expert</strong>
          {log.asked.map((a, i) => (
            <div key={i} className="small muted"><span className="accent">?</span> {a.question} → {a.answer || "(stopped here)"}</div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------- Export ---------------- */
function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a"); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Export({ id }) {
  const [pb, setPb] = useState(null);
  const [md, setMd] = useState("");
  const [mmd, setMmd] = useState("");
  useEffect(() => { api.playbook(id).then(setPb); api.exportMd(id).then(setMd); api.exportMmd(id).then(setMmd); }, [id]);
  if (!pb) return null;
  const c = pb.counts;
  const slug = pb.title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  return (
    <div className="page">
      <header className="bar"><div className="row"><Logo /><a className="btn" href={`#/job/${id}`}>Back to review</a></div></header>
      <main className="split wide">
        <section className="col-side stack-md">
          <div className="stack-sm"><h1 className="h1 h1-sm">Export the playbook</h1><p className="m0 muted">Every step keeps its timestamp and source, so whoever reads it can check it.</p></div>
          {(c.to_confirm > 0 || c.open_questions > 0) && (
            <div className="notice stack-xs">
              <strong>{c.to_confirm} steps still inferred, {c.open_questions} questions open</strong>
              <span className="small">They'll be marked <b className="warn">Unconfirmed</b> and listed under “Open questions”.</span>
              <a href={`#/job/${id}`} className="small">Finish review first</a>
            </div>
          )}
          <div className="card flush">
            <div className="export-row"><div className="stack-0 grow"><strong>Cited playbook</strong><span className="muted small">Steps, sources, timestamps, open questions</span></div>
              <button className="btn btn-dark" onClick={() => download(`${slug}.md`, md, "text/markdown")}>Markdown</button></div>
            <div className="export-row"><div className="stack-0 grow"><strong>Flow diagram</strong><span className="muted small">Mermaid; open questions drawn dashed</span></div>
              <button className="btn btn-dark" onClick={() => download(`${slug}.mmd`, mmd, "text/plain")}>Mermaid</button></div>
          </div>
        </section>
        <section className="col-main stack-sm" aria-label="Preview">
          <span className="eyebrow">Preview</span>
          <article className="paper"><pre className="md">{md}</pre></article>
        </section>
      </main>
    </div>
  );
}
