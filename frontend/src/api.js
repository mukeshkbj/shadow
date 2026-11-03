async function req(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    let msg = `${r.status}`;
    try { msg = (await r.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  const type = r.headers.get("content-type") || "";
  return type.includes("json") ? r.json() : r.text();
}

export const api = {
  health: () => req("/api/health"),
  jobs: () => req("/api/jobs"),
  job: (id) => req(`/api/jobs/${id}`),
  playbook: (id) => req(`/api/jobs/${id}/playbook`),
  timeline: (id) => req(`/api/jobs/${id}/timeline`),
  upload: (file, provider = "muse", passcode = "") => { const f = new FormData(); f.append("file", file); f.append("provider", provider); f.append("passcode", passcode); return req("/api/jobs", { method: "POST", body: f }); },
  editStep: (id, sid, body) => req(`/api/jobs/${id}/steps/${sid}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  answer: (id, qid, answer) => req(`/api/jobs/${id}/questions/${qid}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answer }) }),
  exportMd: (id) => req(`/api/jobs/${id}/export.md`),
  exportMmd: (id) => req(`/api/jobs/${id}/export.mmd`),
  replay: (id) => req(`/api/jobs/${id}/replay`),
  replayShotUrl: (id, name) => `/api/jobs/${id}/replay/shots/${name}`,
  videoUrl: (id) => `/api/jobs/${id}/video`,
};

export const ts = (sec) => {
  if (sec == null) return "--:--";
  const s = Math.round(sec);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};
