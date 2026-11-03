import React, { useEffect, useRef, useState } from "react";
import { api, startOver, ts } from "./api.js";

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

const Logo = ({ light = false }) => (
  <a href="#/" className={`logo ${light ? "logo-light" : ""}`}>
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><circle cx="14" cy="14" r="12" fill={light ? "#FFFFFF" : "#12151B"} /><circle cx="17.5" cy="14" r="7" fill="#C2410C" /></svg>
    <span>Shadow</span>
  </a>
);

const kindOf = (s) => (s.source === "inferred" && s.confirmed ? "confirmed" : s.source);

function StageRail({ active, done = [] }) {
  const stages = [["record", "Record"], ["verify", "Verify"], ["replay", "Replay"]];
  return (
    <ol className="stages-rail" aria-label="Shadow stages">
      {stages.map(([k, l], i) => (
        <li key={k} className={`rail-step ${active === k ? "on" : ""} ${done.includes(k) ? "done" : ""}`}>
          <span className="rail-dot" aria-hidden="true">{done.includes(k) ? "✓" : i + 1}</span>{l}
        </li>
      ))}
    </ol>
  );
}

const TABS = [["steps", "Steps"], ["flow", "Flow"], ["questions", "Questions"], ["replay", "Replay"]];
const SOURCE_LABEL = { seen: "Seen", said: "Said", inferred: "Inferred" };
function Badge({ step }) {
  const kind = step.source === "inferred" && step.confirmed ? "confirmed" : step.source;
  const label = kind === "confirmed" ? "Confirmed" : SOURCE_LABEL[step.source];
  return <span className={`badge badge-${kind}`}>{label}</span>;
}

export default function App() {
  const hash = useHash();
  const m = hash.match(/^#\/job\/([\w-]+)(?:\/(processing|export))?(?:\?t=(\d+))?/);
  if (!m) return <Home />;
  const [, id, view, at] = m;
  if (view === "processing") return <Processing id={id} />;
  if (view === "export") return <Export id={id} />;
  return <Review id={id} at={at == null ? null : Number(at)} />;
}

function Unavailable({ what, detail }) {
  return (
    <div className="page"><header className="bar"><Logo /><a className="btn" href="#/">Back</a></header>
      <main className="narrow stack-sm" role="alert">
        <h1 className="h1 h1-sm">Shadow could not load {what}</h1>
        <p className="m0 muted">{detail === "playbook not ready" ? "This job has no finished playbook yet." : detail}</p>
      </main>
    </div>
  );
}

/* ---------------- Home / upload ---------------- */
function Home() {
  const [jobs, setJobs] = useState([]);
  const [health, setHealth] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [provider, setProvider] = useState("muse");
  const [passcode, setPasscode] = useState(() => { try { return localStorage.getItem("shadow-passcode") || ""; } catch { return ""; } });
  useEffect(() => {
    api.jobs().then(setJobs).catch(e => setErr(e.message));
    api.health().then(h => { setHealth(h); if (h.providers?.length && !h.providers.includes("muse")) setProvider(h.providers[0]); }).catch(() => {});
  }, []);

  const send = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".mp4")) { setErr("Please choose an MP4 file."); return; }
    if (health?.passcode_required && !passcode.trim()) { setErr("Enter the upload passcode first."); return; }
    setBusy(true); setErr("");
    try {
      const { id } = await api.upload(file, provider, passcode);
      try { localStorage.setItem("shadow-passcode", passcode); } catch {}
      go(`#/job/${id}/processing`);
    }
    catch (e) { setErr(e.message); setBusy(false); }
  };
  const demo = jobs.find(j => !j.sample && j.state === "done" && j.provider !== "open") || jobs.find(j => !j.sample && j.state === "done") || jobs.find(j => j.state === "done");

  return (
    <div className="page">
      <section className="hero">
        <header className="hero-bar">
          <Logo light />
          <nav className="row hero-nav" aria-label="Main">
            <a href="#how">How it works</a>
            <a href="https://github.com/mukeshkbj/shadow" target="_blank" rel="noreferrer">GitHub</a>
          </nav>
        </header>
        <div className="hero-body">
          <div className="hero-grid">
          <div className="hero-copy">
          <span className="hero-eyebrow mono">Built with Muse Spark · Muse Wonder · Voice Transcribe · SAM 3.1</span>
          <h1 className="hero-title">Show it once.</h1>
          <p className="hero-lede">Shadow watches an expert do a task, writes the playbook, <em>proves every step</em> against the recording, then does the job back — and stops wherever you never showed it.</p>
          <div className="row hero-cta">
            {demo && <a className="btn btn-accent btn-lg" href={`#/job/${demo.id}`}>Open the live demo</a>}
            <a className="btn btn-ghost btn-lg" href="#upload">Upload a recording</a>
          </div>
          {demo && <p className="hero-proof">In the live demo the expert says <q>I always take the oldest one first</q>. The screen shows the inbox sorted <b>Newest first</b>. Shadow does not choose. It asks.</p>}
          </div>
          <a className="hero-shot" href={demo ? `#/job/${demo.id}` : "#upload"} aria-label="Open the live demo">
            <img src="/hero-review.jpg" width="1280" height="800" fetchpriority="high" alt="Shadow's review screen: the recording with the Newest first sort outlined, the narration line saying the oldest is taken first, and a card asking the expert which one is the rule" />
          </a>
          </div>
          <ol className="loop" id="how">
            {[["01", "Record", "Do the task once, talking as you go. One screen recording with sound.", ["Muse Spark 1.2 watches + listens", "Voice Transcribe times every line"]],
              ["02", "Verify", "Every step cites the second it came from: Seen, Said or Inferred. Gaps become questions, never guesses.", ["Muse Wonder drafts", "Evidence check in plain code", "Spark + SAM 3.1 point at fields"]],
              ["03", "Replay", "An agent does the job back in the real app — and asks you at anything you never showed it.", ["Muse Spark agent on the live page"]]].map(([n, t, d, chips]) => (
              <li key={n} className="loop-card">
                <span className="mono loop-n">{n}</span>
                <strong className="loop-title">{t}</strong>
                <span className="loop-desc">{d}</span>
                <span className="loop-chips">{chips.map(c => <span key={c} className="model-chip">{c}</span>)}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <main className="narrow stack-lg" id="upload">
        <div className="stack-sm">
          <h2 className="h1 h1-sm">Show Shadow how the job is done</h2>
          <p className="lede">Record your screen while you do the task and say why you do things. Use test data if the real thing is sensitive.</p>
        </div>
        {health && !health.providers?.length && (
          <div className="notice">No model is configured, so new recordings can't be processed yet. The playbooks below still open. Set <code>MODEL_API_KEY</code> and restart the server.</div>
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
          {health?.passcode_required && (
            <div className="row center">
              <label htmlFor="passcode" className="small muted">Upload passcode</label>
              <input id="passcode" className="input" type="password" autoComplete="off" value={passcode}
                     onChange={e => setPasscode(e.target.value)} placeholder="Needed to upload" />
            </div>
          )}
          <div className="row center">
            <label className="btn btn-dark">{busy ? "Uploading…" : "Choose a file"}
              <input type="file" accept="video/mp4" className="sr-only" disabled={busy} onChange={e => send(e.target.files[0])} />
            </label>
          </div>
          {err && <p className="error" role="alert">{err}</p>}
        </div>
        <section className="stack-sm">
          <h2 className="h2">Playbooks</h2>
          <div className="card flush">
            {jobs.length === 0 && <div className="pad muted">Nothing yet.</div>}
            {jobs.map(j => (
              <a key={j.id} className="job-row" href={j.state === "done" ? `#/job/${j.id}` : `#/job/${j.id}/processing`}>
                <span className="stack-0 grow"><strong>{j.title || j.filename}</strong>
                  <span className="muted small">{j.sample ? "Offline sample (no model calls)" : j.provider === "open" ? `Open weights · Muse Spark Open on Nebius + Meta Voice Transcribe & SAM 3.1 · ${j.filename}` : `Real run on the Meta Model API · ${j.filename}`}</span></span>
                {j.counts && <span className="muted small">{j.counts.seen + j.counts.said + j.counts.inferred} steps · {j.counts.to_confirm} to confirm · {j.counts.open_questions} questions</span>}
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
function TrustBar({ pb, onJump }) {
  const steps = pb.steps;
  const counts = { seen: 0, said: 0, confirmed: 0, inferred: 0 };
  steps.forEach(s => { counts[kindOf(s)] += 1; });
  const backed = counts.seen + counts.said + counts.confirmed;
  const openQ = pb.counts.open_questions;
  return (
    <div className="trust" aria-label="Evidence summary">
      <div className="trust-bar" aria-hidden="true">
        {steps.map(s => <span key={s.id} className={`trust-seg seg-${kindOf(s)}`} />)}
      </div>
      <span className="trust-text"><strong>{backed} of {steps.length}</strong> steps backed by the recording
        {counts.inferred > 0 && <> · <button className="link-btn warn" onClick={onJump}>{counts.inferred} need{counts.inferred === 1 ? "s" : ""} you</button></>}
        {openQ > 0 && <> · <b className="accent">{openQ} open question{openQ === 1 ? "" : "s"}</b></>}
      </span>
    </div>
  );
}

function EvidenceTimeline({ duration, events, turns, steps, sel, now, onSeek, onPick }) {
  const D = duration || 1;
  const cited = new Set(steps[sel]?.evidence_event_ids || []);
  const heard = events.filter(e => e.source === "said" && cited.has(e.id));
  const turnCited = u => heard.some(e => e.t >= u.start - 0.5 && e.t <= u.end + 0.5);
  const pct = t => `${Math.min(100, Math.max(0, (t / D) * 100))}%`;
  const seekFrom = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    onSeek(Math.max(0, Math.min(D, ((e.clientX - r.left) / r.width) * D)));
  };
  const ticks = []; for (let t = 0; t <= D; t += D > 150 ? 30 : 10) ticks.push(t);
  return (
    <div className="tl" aria-label="Evidence timeline">
      <div className="tl-row tl-ruler"><span className="tl-label" />
        <div className="tl-track">{ticks.map(t => <span key={t} className="tl-tick mono" style={{ left: pct(t) }}>{ts(t)}</span>)}</div></div>
      <div className="tl-row"><span className="tl-label">Screen</span>
        <div className="tl-track tl-click" onClick={seekFrom} title="What Muse Spark saw on screen">
          {events.filter(e => e.source === "seen").map(e => <span key={e.id} className={`tl-dot ${cited.has(e.id) ? "cited" : ""}`} style={{ left: pct(e.t) }} title={`${ts(e.t)} · ${e.action}`} />)}
        </div></div>
      <div className="tl-row"><span className="tl-label">Voice</span>
        <div className="tl-track tl-click" onClick={seekFrom} title="Narration turns from Muse Voice Transcribe">
          {turns.map((u, i) => <span key={i} className={`tl-turn ${now >= u.start && now <= u.end ? "on" : ""} ${turnCited(u) ? "cited" : ""}`} style={{ left: pct(u.start), width: pct(Math.max(0.6, u.end - u.start)) }} title={`${ts(u.start)} · “${u.text}”`} />)}
        </div></div>
      <div className="tl-row"><span className="tl-label">Steps</span>
        <div className="tl-track">
          {steps.map((s, i) => {
            const end = s.t_end != null && s.t_end > s.t_start ? s.t_end : (steps[i + 1]?.t_start ?? Math.min(D, s.t_start + 6));
            return <button key={s.id} className={`tl-step seg-${kindOf(s)} ${i === sel ? "on" : ""}`} style={{ left: pct(s.t_start), width: pct(Math.max(1.5, end - s.t_start)) }}
                           onClick={() => onPick(i)} title={`Step ${i + 1} · ${s.text}`}>{i + 1}</button>;
          })}
        </div></div>
      <div className="tl-playhead-wrap" aria-hidden="true"><span className="tl-playhead" style={{ left: pct(now) }} /></div>
    </div>
  );
}

function Provenance({ step, events, open }) {
  const watcher = open ? "Muse Spark Open" : "Muse Spark 1.2";
  const byId = Object.fromEntries(events.map(e => [e.id, e]));
  const cited = (step.evidence_event_ids || []).map(id => byId[id]).filter(Boolean);
  const seen = cited.filter(e => e.source === "seen");
  const items = [];
  if (seen.length) items.push(["spark", watcher, `saw it on screen at ${seen.map(e => ts(e.t)).join(", ")}`]);
  if (step.quote_check) items.push(["voice", "Voice Transcribe", `heard the quote at ${ts(step.quote_check.start)}–${ts(step.quote_check.end)}`]);
  else if (step.source === "said") items.push(["voice", open ? "Voice Transcribe" : "Muse Spark 1.2", "heard it in the narration"]);
  items.push(["wonder", open ? "Muse Spark Open" : "Muse Wonder", "wrote the step from the timeline"]);
  if (step.downgraded_reason) items.push(["check warn", "Evidence check", step.downgraded_reason]);
  else items.push(["check", "Evidence check", step.source === "inferred" ? "kept it as an interpretation" : "found matching evidence"]);
  if (step.pointer) items.push(["sam", "Spark + SAM 3.1", `outlined “${step.pointer.label || step.field}”`]);
  if (step.confirmed) items.push(["expert", "Expert", "confirmed it"]);
  return (
    <ul className="prov" aria-label="Where this step came from">
      {items.map(([k, who, what], i) => <li key={i} className={`prov-item prov-${k}`}><b>{who}</b> {what}</li>)}
    </ul>
  );
}

const FOLLOWED = { screen: "followed the screen", voice: "followed the narration", expert: "wrote the rule" };

function Disagreement({ s, clash, canPlay, onPlay, onSave }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(s.text);
  const head = `clash-${s.id}`;
  return (
    <div className="clash" role="group" aria-labelledby={head}>
      <p id={head} className="clash-head">Screen and voice disagree. Shadow did not pick one.</p>
      <div className="clash-sides">
        <div className="clash-side clash-screen">
          <span className="clash-kind mono">Screen · {ts(clash.seen_t)}</span>
          <span className="clash-text">{clash.seen}</span>
          {canPlay && <button className="btn btn-sm" onClick={() => onPlay(clash.seen_t, clash.seen_t + 4)}>Watch it</button>}
        </div>
        <span className="clash-vs mono" aria-hidden="true">vs</span>
        <div className="clash-side clash-voice">
          <span className="clash-kind mono">Voice · {ts(clash.said_t)}</span>
          <q className="clash-text">{clash.said}</q>
          {canPlay && <button className="btn btn-sm" onClick={() => onPlay(clash.said_t, clash.said_end ?? clash.said_t + 5)}>Hear it</button>}
        </div>
      </div>
      {editing ? (
        <form className="row" onSubmit={e => { e.preventDefault(); if (text.trim()) onSave(text, "expert"); }}>
          <label className="sr-only" htmlFor={`fix-${s.id}-clash`}>The rule, in your words</label>
          <input id={`fix-${s.id}-clash`} className="input grow" value={text} onChange={e => setText(e.target.value)} autoFocus />
          <button className="btn btn-dark" type="submit">Save</button>
          <button className="btn" type="button" onClick={() => setEditing(false)}>Cancel</button>
        </form>
      ) : (
        <div className="stack-xs">
          <strong className="small">Which one is the rule?</strong>
          <div className="row">
            <button className="btn btn-dark" onClick={() => onSave(`${s.text}: follow the screen (${clash.seen})`, "screen")}>Follow the screen</button>
            <button className="btn" onClick={() => onSave(`${s.text}: follow the narration (“${clash.said}”)`, "voice")}>Follow the voice</button>
            <button className="btn" onClick={() => setEditing(true)}>Write it myself</button>
          </div>
        </div>
      )}
      <p className="m0 xsmall muted">Your answer becomes the step the Replay agent runs. In testing, a bare “run it anyway” here sent the agent to the wrong customer.</p>
    </div>
  );
}

function Review({ id, at }) {
  const [pb, setPb] = useState(null);
  const [tl, setTl] = useState({ events: [], turns: [], duration: 0 });
  const [job, setJob] = useState(null);
  const [replay, setReplay] = useState(undefined);
  const [err, setErr] = useState("");
  const [sel, setSel] = useState(0);
  const [tab, setTab] = useState("steps");
  const [now, setNow] = useState(0);
  const [privateReview, setPrivateReview] = useState(false);
  const [round, setRound] = useState(0);
  const video = useRef(null);
  const stopAt = useRef(null);

  useEffect(() => { api.health().then(h => setPrivateReview(!!h.private_review)).catch(() => {}); }, []);
  useEffect(() => {
    api.playbook(id).then(setPb).catch(e => setErr(e.message));
  }, [id, round]);
  useEffect(() => {
    if (at == null || !pb) return;
    let i = 0; pb.steps.forEach((s, k) => { if (s.t_start <= at + 0.25) i = k; });
    setSel(i); setNow(at);
    if (video.current) video.current.currentTime = at;
  }, [at, !!pb]);
  useEffect(() => {
    api.job(id).then(setJob).catch(() => {});
    api.timeline(id).then(t => setTl({ events: t.events || [], turns: t.turns || [], duration: t.duration || 0 })).catch(() => {});
    api.replay(id).then(setReplay).catch(() => setReplay(null));
  }, [id]);

  if (err) return <Unavailable what="this playbook" detail={err} />;
  if (!pb) return <div className="page"><header className="bar"><Logo /></header><main className="narrow muted" role="status">Loading the playbook…</main></div>;

  const steps = pb.steps;
  const cur = steps[sel] || steps[0];
  const c = pb.counts;
  const duration = pb.duration || tl.duration;
  const seek = (t) => { setNow(t); if (video.current) video.current.currentTime = t; };
  const pick = (i) => { setSel(i); if (steps[i]) seek(steps[i].t_start); };
  const play = (from, to) => {
    const v = video.current;
    if (!v) return;
    seek(from); stopAt.current = to;
    v.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    v.play().catch(() => { stopAt.current = null; });
  };
  const firstOpen = steps.findIndex(s => s.source === "inferred" && !s.confirmed);
  const update = (p) => p.then(setPb).catch(e => setErr(e.message));
  const clashOf = (s) => (!s.confirmed && pb.conflicts?.[s.id]) || null;
  const curClash = clashOf(cur);
  const resolve = (step, text, resolution) => update(api.editStep(id, step.id, { text, resolution }));
  const saying = tl.turns.find(u => now >= u.start - 0.2 && now <= u.end + 0.2);
  const replayDone = replay && !replay.stopped && replay.actions?.length > 0;

  return (
    <div className="page">
      <header className="bar wrap">
        <div className="row">
          <Logo />
          <span className="divider" />
          <div className="stack-0"><strong>{pb.title}</strong><span className="muted small">{job?.sample ? "Offline sample · " : job?.provider === "open" ? "Open weights · Muse Spark Open on Nebius · " : "Real run · Meta Model API · "}{ts(duration)} recording</span></div>
        </div>
        <StageRail active={tab === "replay" ? "replay" : "verify"} done={["record", ...(replayDone ? ["replay"] : [])]} />
        <a className="btn btn-dark" href={`#/job/${id}/export`}>Export playbook</a>
      </header>
      <TrustBar pb={pb} onJump={() => { setTab("steps"); if (firstOpen >= 0) pick(firstOpen); }} />
      {privateReview && (
        <div className="private-note small">Try it: confirm a step or answer a question. Your changes stay in this browser, so the next visitor sees the original run.
          {(pb.steps.some(s => s.confirmed) || pb.open_questions.some(q => q.answer)) && <button className="link-btn" onClick={() => { startOver(); setRound(r => r + 1); }}>Start over</button>}</div>
      )}

      <main className="split">
        <section className="col-main stack-md" aria-label="Recording">
          <div className="player">
            {job?.has_video ? (
              <div className="video-wrap">
                <video ref={video} src={api.videoUrl(id)} controls preload="metadata" onPause={() => { stopAt.current = null; }} onLoadedMetadata={e => { if (at != null) e.currentTarget.currentTime = at; }}
                       onTimeUpdate={e => {
                         const t = e.currentTarget.currentTime;
                         setNow(t);
                         if (stopAt.current != null && t >= stopAt.current) { stopAt.current = null; e.currentTarget.pause(); }
                         let i = 0; steps.forEach((s, k) => { if (s.t_start <= t + 0.25) i = k; });
                         if (i !== sel) setSel(i);
                       }} />
                {cur.pointer && now >= cur.t_start - 0.5 && now <= (cur.t_end ?? cur.t_start + 8) && (
                  <div className="pointer" aria-hidden="true" style={{
                    left: `${(cur.pointer.x1 / cur.pointer.w) * 100}%`, top: `${(cur.pointer.y1 / cur.pointer.h) * 100}%`,
                    width: `${((cur.pointer.x2 - cur.pointer.x1) / cur.pointer.w) * 100}%`, height: `${((cur.pointer.y2 - cur.pointer.y1) / cur.pointer.h) * 100}%`,
                  }}><span>{cur.pointer.label || "Pointer"}</span></div>
                )}
              </div>
            ) : (
              <div className="player-empty">
                <strong>The offline sample has no video</strong>
                <span>Open the real run from the home page to see the recording, pointers and timeline in action.</span>
              </div>
            )}
            <EvidenceTimeline duration={duration} events={tl.events} turns={tl.turns} steps={steps} sel={sel} now={now} onSeek={seek} onPick={pick} />
            <div className="saying" aria-live="polite">{saying ? <><span className="mono">{ts(saying.start)}</span> “{saying.text}”</> : <span className="muted">Narration appears here as the video plays</span>}</div>
          </div>

          <div className="card evidence stack-sm">
            <div className="row">
              <span className="eyebrow">Step {sel + 1} · evidence</span>
              <span className="mono chip">{ts(cur.t_start)}{cur.t_end != null ? `–${ts(cur.t_end)}` : ""}</span>
              <Badge step={cur} />
            </div>
            <h3 className="evidence-title">{cur.text}</h3>
            {curClash && <div className="clash-narrow"><Disagreement key={cur.id} s={cur} clash={curClash} canPlay={!!job?.has_video} onPlay={play} onSave={(text, r) => resolve(cur, text, r)} /></div>}
            <p className={`m0 ${curClash ? "clash-wide" : ""}`}>{cur.evidence || "—"}</p>
            {cur.quote && <blockquote className="quote">“{cur.quote}”</blockquote>}
            <Provenance step={cur} events={tl.events} open={job?.provider === "open"} />
            <p className="m0 xsmall muted">Pointers and model notes help you look. The timestamped recording is the evidence.</p>
          </div>
        </section>

        <section className="col-side card flush" aria-label="Playbook">
          <div role="tablist" aria-label="Playbook views" className="tabs" onKeyDown={e => {
            const keys = TABS.map(t => t[0]); const i = keys.indexOf(tab);
            const next = e.key === "ArrowRight" ? keys[(i + 1) % keys.length] : e.key === "ArrowLeft" ? keys[(i + keys.length - 1) % keys.length] : null;
            if (next) { e.preventDefault(); setTab(next); document.getElementById(`tab-${next}`)?.focus(); }
          }}>
            {TABS.map(([k, l]) => (
              <button key={k} id={`tab-${k}`} role="tab" aria-selected={tab === k} aria-controls="tabpanel" tabIndex={tab === k ? 0 : -1}
                      className={`tab ${tab === k ? "on" : ""}`} onClick={() => setTab(k)}>
                {k === "steps" ? `${l} · ${steps.length}` : k === "questions" ? `${l} · ${c.open_questions}` : l}{k === "replay" && replayDone && <span className="tab-dot" />}
              </button>
            ))}
          </div>
          <div id="tabpanel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
          {tab === "steps" && (
            <ol className="steps">
              {steps.map((s, i) => (
                <li key={s.id} className={`step step-${kindOf(s)} ${i === sel ? "on" : ""}`}>
                  <button className="step-main" onClick={() => pick(i)}>
                    <span className="step-node" aria-hidden="true">{i + 1}</span>
                    <span className="stack-0 grow"><strong>{s.text}</strong><span className="muted small">{s.detail}</span>
                      <span className="mono xsmall muted">{ts(s.t_start)}{s.kind === "decision" ? " · decision" : ""}</span></span>
                    <Badge step={s} />
                  </button>
                  {clashOf(s) ? (
                    <div className="step-note clash-wide"><Disagreement s={s} clash={clashOf(s)} canPlay={!!job?.has_video} onPlay={play} onSave={(text, r) => resolve(s, text, r)} /></div>
                  ) : <>
                  {s.source === "inferred" && !s.confirmed && (s.downgraded_reason || s.evidence) && <p className="step-note step-why small"><b>Why it needs you:</b> {s.downgraded_reason || s.evidence}</p>}
                  {s.source === "inferred" && !s.confirmed && <StepReview s={s} onConfirm={() => update(api.editStep(id, s.id, { confirmed: true }))} onFix={(text) => update(api.editStep(id, s.id, { text }))} />}
                  </>}
                  {s.source === "inferred" && s.confirmed && <div className="step-note ok small">{pb.conflicts?.[s.id] && s.resolution
                    ? `Screen and voice disagreed. The expert ${FOLLOWED[s.resolution]}.` : "Confirmed by the expert · was inferred."} Replay runs this wording.</div>}
                </li>
              ))}
            </ol>
          )}
          {tab === "flow" && <Flow pb={pb} onPick={(sid) => { const i = steps.findIndex(s => s.id === sid); if (i >= 0) { pick(i); setTab("steps"); } }} />}
          {tab === "questions" && <Questions pb={pb} onAnswer={(qid, a) => update(api.answer(id, qid, a))} />}
          {tab === "replay" && <Replay id={id} steps={steps} log={replay} />}
          {pb.notes?.length > 0 && tab === "steps" && (
            <details className="notes small"><summary>Evidence check log ({pb.notes.length})</summary><ul>{pb.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></details>
          )}
          </div>
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

function Replay({ id, steps, log }) {
  const [open, setOpen] = useState(null);
  if (log === undefined) return <div className="pad muted">Loading…</div>;
  if (!log) return (
    <div className="pad stack-xs muted">
      <strong>No replay for this playbook yet.</strong>
      <span>After confirming the playbook, run <code>python scripts/replay.py {id}</code>. An agent re-runs it in the app it came from, and stops to ask at anything unconfirmed or unshown.</span>
    </div>
  );
  const indexOf = Object.fromEntries(steps.map((s, i) => [s.id, i + 1]));
  const groups = [];
  log.actions.forEach(x => {
    const last = groups[groups.length - 1];
    if (last && last.step === x.step) last.items.push(x); else groups.push({ step: x.step, items: [x] });
  });
  const askedBy = {}; (log.asked || []).forEach(a => { (askedBy[a.step] = askedBy[a.step] || []).push(a); });
  const nActions = log.actions.filter(x => x.ok && x.action && !["none", "check"].includes(x.action)).length;
  const nDecisions = log.actions.filter(x => x.decision).length;
  return (
    <div className="replay">
      <div className={`replay-head ${log.stopped ? "stopped" : "done"}`}>
        <strong>{log.stopped ? `Stopped and asked: ${log.stopped}` : "The agent did the job back"}</strong>
        <span className="small">{nActions} actions · {nDecisions} decisions · {(log.asked || []).length} question{(log.asked || []).length === 1 ? "" : "s"} for the expert · {log.model && log.model.includes("open") ? "Muse Spark Open (open weights)" : "Muse Spark"} reading the live page</span>
      </div>
      <ol className="replay-steps">
        {groups.map((g, gi) => {
          const n = indexOf[g.step];
          const shot = n ? api.replayShotUrl(id, `step_${String(n).padStart(2, "0")}.png`) : null;
          return (
            <li key={gi} className="replay-step">
              <span className="step-node" aria-hidden="true">{n || "·"}</span>
              <div className="stack-xs grow">
                <strong>{steps[n - 1]?.text || g.step}</strong>
                {(askedBy[g.step] || []).map((a, k) => (
                  <div key={k} className="replay-ask"><b>Asked the expert</b> {a.question === "unconfirmed step" ? "this step was never confirmed — run it anyway?" : a.question} <span className="muted">→ {a.answer?.trim() ? a.answer : "go ahead"}</span></div>
                ))}
                {g.items.map((x, k) => x.decision ? (
                  <div key={k} className="replay-act"><span className="act-kind act-decide">decide</span>{x.decision} → <b>{x.chose}</b><span className="muted small"> · {x.why}</span></div>
                ) : x.skipped ? (
                  <div key={k} className="replay-act muted"><span className="act-kind">skip</span>skipped at the expert's request</div>
                ) : (
                  <div key={k} className={`replay-act ${x.ok === false ? "bad" : ""}`}>
                    <span className="act-kind">{x.action || "—"}</span>
                    <span className="mono xsmall">{x.selector}{x.value ? ` = “${x.value}”` : ""}</span>
                    <span className="muted small"> {x.error || x.why}</span>
                  </div>
                ))}
                {shot && (
                  <button className="replay-shot" onClick={() => setOpen(open === gi ? null : gi)} aria-expanded={open === gi}>
                    <img src={shot} alt={`Screen after step ${n}`} className={open === gi ? "big" : ""} onError={e => e.currentTarget.parentElement.remove()} />
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ol>
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
  const [err, setErr] = useState("");
  useEffect(() => {
    const fail = e => setErr(e.message);
    api.playbook(id).then(setPb, fail); api.exportMd(id).then(setMd, fail); api.exportMmd(id).then(setMmd, fail);
  }, [id]);
  if (err) return <Unavailable what="the export" detail={err} />;
  if (!pb) return <div className="page"><header className="bar"><Logo /></header><main className="narrow muted" role="status">Preparing the export…</main></div>;
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
              <strong>{[c.to_confirm > 0 && `${c.to_confirm} step${c.to_confirm === 1 ? "" : "s"} still unconfirmed`, c.open_questions > 0 && `${c.open_questions} question${c.open_questions === 1 ? "" : "s"} open`].filter(Boolean).join(", ")}</strong>
              <span className="small">The export marks them <b className="warn">Unconfirmed</b> and lists them under “Open questions”.</span>
              <a href={`#/job/${id}`} className="small">Finish review first</a>
            </div>
          )}
          <div className="card flush">
            <div className="export-row"><div className="stack-0 grow"><strong>Cited playbook</strong><span className="muted small">Steps, sources, timestamps, open questions</span></div>
              <button className="btn btn-dark" disabled={!md} onClick={() => download(`${slug}.md`, md, "text/markdown")}>Markdown</button></div>
            <div className="export-row"><div className="stack-0 grow"><strong>Flow diagram</strong><span className="muted small">Mermaid; open questions drawn dashed</span></div>
              <button className="btn btn-dark" disabled={!mmd} onClick={() => download(`${slug}.mmd`, mmd, "text/plain")}>Mermaid</button></div>
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
