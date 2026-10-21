/* Audiobook Studio front end. Plain JavaScript, no build step, works offline. */
"use strict";

// ---------------------------------------------------------------- icons

const ICONS = {
  library: '<path d="M4 19.5V5a2 2 0 0 1 2-2h3v18H6a2 2 0 0 1-2-1.5Z"/><path d="M9 3h4v18H9"/><path d="m15.5 4.2 3.6-.9 3 15.6-3.6.9z"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 17v4M8 21h8"/>',
  type: '<path d="M4 7V5h16v2M9 19h6M12 5v14"/>',
  sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  paste: '<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4V3h6v1M9 10h6M9 14h6M9 18h3"/>',
  play: '<path d="M7 4.5v15a1 1 0 0 0 1.5.86l12-7.5a1 1 0 0 0 0-1.72l-12-7.5A1 1 0 0 0 7 4.5Z" fill="currentColor" stroke="none"/>',
  pause: '<rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/><rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/>',
  back15: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><text x="12" y="15.5" font-size="7.5" text-anchor="middle" fill="currentColor" stroke="none" font-family="-apple-system,sans-serif" font-weight="700">15</text>',
  fwd30: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/><text x="12" y="15.5" font-size="7.5" text-anchor="middle" fill="currentColor" stroke="none" font-family="-apple-system,sans-serif" font-weight="700">30</text>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  check: '<path d="m5 12 5 5L20 7"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  skip: '<path d="M3 3l18 18"/><path d="M10.6 5.1A10.6 10.6 0 0 1 12 5c5 0 9 4.5 10 7a12.6 12.6 0 0 1-2.4 3.4M6.6 6.6A12.4 12.4 0 0 0 2 12c1 2.5 5 7 10 7a10 10 0 0 0 5.4-1.6"/>',
  restore: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  redo: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  download: '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 20h16"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
  alert: '<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4M12 17h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  sparkle: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8Z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8Z"/>',
  headphones: '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1v-6h3zM3 19a2 2 0 0 0 2 2h1v-6H3z"/>',
  chevronLeft: '<path d="m15 18-6-6 6-6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6"/>',
  wave: '<path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 7v10M21 12h0"/>',
  star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9Z"/>',
  book: '<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5Z"/><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>',
};

function icon(name, cls = "") {
  const span = document.createElement("span");
  span.className = "i " + cls;
  span.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
  return span;
}

// ---------------------------------------------------------------- dom helpers

function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k === "style") Object.assign(el.style, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k in el && typeof v !== "string") el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
const $ = (sel, root = document) => root.querySelector(sel);

function hydrateIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((el) => {
    if (!el.firstChild) el.replaceWith(Object.assign(icon(el.dataset.icon), { className: el.className }));
  });
}

// ---------------------------------------------------------------- formatting

const fmt = {
  dur(sec) {
    sec = Math.max(0, Math.round(sec || 0));
    const hrs = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60);
    if (hrs) return `${hrs} h ${m} min`;
    if (m) return `${m} min`;
    return `${sec} s`;
  },
  clock(sec) {
    const d = new Date(Date.now() + sec * 1000);
    const sameDay = d.toDateString() === new Date().toDateString();
    const t = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    return sameDay ? t : `${d.toLocaleDateString([], { weekday: "short" })} ${t}`;
  },
  num: (n) => (n || 0).toLocaleString(),
  time(sec) {
    if (!isFinite(sec)) return "0:00";
    sec = Math.floor(sec);
    const hrs = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return hrs ? `${hrs}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
  },
};

const voiceLabel = (id) => (id || "").startsWith("preset:") ? id.slice(7) : id;

// ---------------------------------------------------------------- api

async function api(method, url, body) {
  const opts = { method, headers: { "X-Studio": "1" } };
  if (body instanceof FormData) opts.body = body;
  else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  let data = null;
  try { data = await res.json(); } catch { /* empty */ }
  if (!res.ok) throw new Error((data && (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))) || res.statusText);
  return data;
}

function uploadWithProgress(url, form, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.setRequestHeader("X-Studio", "1");
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.upload.onload = () => onProgress(1);
    xhr.onload = () => {
      let data = null;
      try { data = JSON.parse(xhr.responseText); } catch { /* empty */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new Error((data && data.detail) || `Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("Couldn't reach the studio. Is it still running?"));
    xhr.send(form);
  });
}

// ---------------------------------------------------------------- toasts & modals

function toast(msg, kind = "info", ms = 4200) {
  const el = h("div", { class: `toast ${kind}` }, icon(kind === "error" ? "alert" : kind === "success" ? "check" : "info"), h("span", { text: msg }));
  $("#toasts").append(el);
  setTimeout(() => { el.style.transition = "opacity .3s"; el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, ms);
}

function modal({ title, subtitle, body, actions = [], narrow = false }) {
  const root = $("#modal-root");
  const close = () => { back.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = (e) => e.key === "Escape" && close();
  const back = h("div", { class: "modal-back", onclick: (e) => e.target === back && close() },
    h("div", { class: "modal" + (narrow ? " narrow" : ""), role: "dialog", "aria-modal": "true" },
      h("div", { class: "modal-head" },
        h("div", { class: "grow" }, h("h2", { text: title }), subtitle ? h("p", { class: "muted small", style: { margin: "4px 0 0" }, text: subtitle }) : null),
        h("button", { class: "icon-btn", "aria-label": "Close", onclick: close }, icon("x"))),
      h("div", { class: "modal-body" }, body),
      actions.length ? h("div", { class: "modal-foot" }, actions.map((a) => (typeof a === "function" ? a(close) : a))) : null));
  root.append(back);
  document.addEventListener("keydown", onKey);
  setTimeout(() => back.querySelector("textarea, input")?.focus(), 30);
  return close;
}

function confirmBox(title, text, okLabel = "OK") {
  return new Promise((resolve) => {
    modal({
      title, narrow: true, body: h("p", { class: "muted", style: { margin: 0 }, text }),
      actions: [
        (close) => h("button", { class: "btn btn-ghost", text: "Cancel", onclick: () => { close(); resolve(false); } }),
        (close) => h("button", { class: "btn btn-primary", text: okLabel, onclick: () => { close(); resolve(true); } }),
      ],
    });
  });
}

// ---------------------------------------------------------------- covers & avatars

const PALETTES = [
  ["#3b2f63", "#7c5cbf"], ["#1f4e5f", "#3c9d9b"], ["#6b2d2d", "#c4683f"], ["#2b3a55", "#5c7aa8"],
  ["#4a3b1f", "#b08a3e"], ["#273c2c", "#5f8a5a"], ["#5a2342", "#b35482"], ["#1d2b44", "#d2774b"],
];
function hashStr(s) { let x = 0; for (const c of s || "") x = (x * 31 + c.charCodeAt(0)) | 0; return Math.abs(x); }

function coverEl(book, extra = null) {
  const wrap = h("div", { class: "cover" });
  if (book.cover) {
    wrap.append(h("img", { src: book.cover, alt: "", loading: "lazy" }));
  } else {
    const [a, b] = PALETTES[hashStr(book.title) % PALETTES.length];
    wrap.style.background = `linear-gradient(160deg, ${b}, ${a})`;
    wrap.append(h("div", { class: "cover-gen" }, h("div", { class: "ct", text: book.title || "Untitled" }),
      h("div", { class: "ca", text: book.author && book.author !== "Unknown" ? book.author : "" })));
  }
  if (extra) wrap.append(extra);
  return wrap;
}

function avatarEl(name) {
  const [a, b] = PALETTES[hashStr(name) % PALETTES.length];
  return h("div", { class: "avatar", style: { background: `linear-gradient(140deg, ${b}, ${a})` }, text: (name || "?").slice(0, 1).toUpperCase() });
}

// ---------------------------------------------------------------- player

const Player = {
  audio: null, meta: null,
  init() {
    this.audio = $("#audio");
    const a = this.audio;
    $("#pl-play").onclick = () => (a.paused ? a.play() : a.pause());
    $("#pl-back").onclick = () => { a.currentTime = Math.max(0, a.currentTime - 15); };
    $("#pl-fwd").onclick = () => { a.currentTime = Math.min(a.duration || 0, a.currentTime + 30); };
    $("#pl-close").onclick = () => this.close();
    const rates = [1, 1.25, 1.5, 1.75, 0.8];
    $("#pl-rate").onclick = () => {
      const next = rates[(rates.indexOf(a.playbackRate) + 1) % rates.length];
      a.playbackRate = next;
      $("#pl-rate").textContent = `${next}×`;
    };
    const seek = $("#pl-seek");
    seek.oninput = () => { if (a.duration) a.currentTime = (seek.value / 1000) * a.duration; };
    a.ontimeupdate = () => {
      $("#pl-cur").textContent = fmt.time(a.currentTime);
      if (a.duration) seek.value = Math.round((a.currentTime / a.duration) * 1000);
    };
    a.onloadedmetadata = () => { $("#pl-dur").textContent = fmt.time(a.duration); };
    a.onplay = a.onpause = () => {
      $("#pl-play").replaceChildren(icon(a.paused ? "play" : "pause"));
      refreshPlayState();
    };
    a.onended = () => refreshPlayState();
    document.addEventListener("keydown", (e) => {
      if (e.code === "Space" && !$("#player").hidden && !/INPUT|TEXTAREA|SELECT|BUTTON/.test(document.activeElement.tagName)) {
        e.preventDefault();
        a.paused ? a.play() : a.pause();
      }
    });
  },
  play(url, title, subtitle = "", art = null) {
    if (!url) return;
    const a = this.audio;
    if (this.meta && this.meta.url === url) { a.paused ? a.play() : a.pause(); return; }
    this.meta = { url, title, subtitle };
    a.src = url;
    a.play().catch(() => {});
    $("#player-title").textContent = title || "";
    $("#player-sub").textContent = subtitle || "";
    const artBox = $("#player-art");
    artBox.replaceChildren(art ? (art.cover ? h("img", { src: art.cover, alt: "" }) : coverEl(art)) : h("div", { class: "mini", style: { display: "grid", placeItems: "center" } }, icon("headphones")));
    if (art && !art.cover) { const c = artBox.firstChild; c.style.width = "100%"; c.style.height = "100%"; c.style.borderRadius = "0"; c.querySelector(".ct").style.fontSize = "8px"; }
    $("#player").hidden = false;
    document.documentElement.style.setProperty("--player-h", "74px");
  },
  isPlaying(url) { return this.meta && this.meta.url === url && !this.audio.paused; },
  close() {
    this.audio.pause();
    this.meta = null;
    $("#player").hidden = true;
    document.documentElement.style.setProperty("--player-h", "0px");
    refreshPlayState();
  },
};

function refreshPlayState() {
  document.querySelectorAll("[data-playing-url]").forEach((el) => updatePlayButton(el));
  document.querySelectorAll("[data-wave-url]").forEach((el) => el.classList.toggle("playing", Player.isPlaying(el.dataset.waveUrl)));
}

function playButton(url, title, subtitle, art, opts = {}) {
  const btn = h("button", {
    class: opts.big ? "play-btn" : "icon-btn", title: opts.label || "Play", "aria-label": opts.label || "Play",
    dataset: { playingUrl: url || "" }, disabled: !url,
    onclick: (e) => { e.stopPropagation(); Player.play(url, title, subtitle, art); },
  });
  updatePlayButton(btn);
  return btn;
}
function updatePlayButton(btn) {
  btn.replaceChildren(icon(Player.isPlaying(btn.dataset.playingUrl) ? "pause" : "play"));
}

// ---------------------------------------------------------------- state & polling

const S = { jobs: [], route: [], lastSig: "", pending: new Map(), seenDone: new Set(), voices: null };
const JOB_WORD = { render: "Narrating", preview: "Previewing", redo: "Re-recording", say: "Speaking" };

function jobStage(job) {
  const p = job.progress || {};
  if (job.status === "queued") return "Waiting its turn";
  if (p.stage === "loading" || !p.stage || p.stage === "starting") return "Warming up the narrator…";
  if (p.stage === "mastering") return `Mastering chapter ${p.chapter}…`;
  if (p.stage === "packaging") return "Packaging the audiobook…";
  if (p.pct != null && p.eta_seconds != null && job.kind !== "say") return `${Math.floor(p.pct)}% · ${fmt.dur(p.eta_seconds)} left`;
  if (p.pct != null) return `${Math.floor(p.pct)}%`;
  if (p.stage === "narrating") return "Reading the first piece…";
  return "Working…";
}

function renderJobCard() {
  const card = $("#job-card");
  const running = S.jobs.find((j) => j.status === "running");
  const queued = S.jobs.filter((j) => j.status === "queued");
  const job = running || queued[0];
  if (!job) { card.hidden = true; document.title = "Audiobook Studio"; return; }
  const p = job.progress || {};
  const pct = p.pct ?? 0;
  const indeterminate = !running || p.stage === "loading" || p.stage === "packaging" || p.stage === "mastering" || p.pct == null;
  card.hidden = false;
  card.replaceChildren(...[
    h("div", { class: "jt" }, running ? h("span", { class: "dot pulse", style: { color: "var(--accent)" } }) : icon("clock", "i-sm"),
      h("span", { text: `${JOB_WORD[job.kind] || "Working"}` })),
    h("div", { style: { fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, text: job.label }),
    h("div", { class: "progress" + (indeterminate ? " indeterminate" : "") }, h("div", { style: { width: `${pct}%` } })),
    h("div", { class: "row" },
      h("span", { class: "js", text: jobStage(job) + (queued.length > (running ? 0 : 1) ? ` · ${queued.length - (running ? 0 : 1)} waiting` : "") }),
      h("button", { class: "btn btn-sm btn-ghost", text: job.kind === "render" ? "Pause" : "Stop", onclick: () => cancelJob(job) })),
    job.project ? h("a", { class: "tiny", href: `#/book/${job.project}`, text: "Open book →" }) : null,
  ].filter(Boolean));
  document.title = running && p.pct != null ? `${Math.floor(pct)}% · ${job.label} · Audiobook Studio` : "Audiobook Studio";
}

async function cancelJob(job) {
  if (job.kind === "render" && job.status === "running") {
    const ok = await confirmBox("Pause narration?", "Everything finished so far is saved. Press Resume any time to continue from here.", "Pause");
    if (!ok) return;
  }
  try { await api("POST", `/api/jobs/${job.id}/cancel`); } catch (e) { toast(e.message, "error"); }
  poll(true);
}

function onJobFinished(job) {
  const pending = S.pending.get(job.id);
  S.pending.delete(job.id);
  if (job.status === "done") {
    if (job.kind === "say" && job.result.url) {
      Player.play(job.result.url, pending?.title || "Quick listen", pending?.subtitle || job.label);
    } else if (job.kind === "preview") {
      const url = (job.result.preview_urls || [])[0];
      if (url) Player.play(url, `${job.label}`, `Preview · chapter ${job.extra?.chapter ?? ""}`);
      toast("Preview ready", "success");
    } else if (job.kind === "render") {
      const msg = job.result.flagged ? `“${job.label}” is finished. ${job.result.flagged} spot(s) to check.` : `“${job.label}” is finished.`;
      toast(msg, "success", 7000);
      notify("Audiobook finished", msg);
    } else if (job.kind === "redo") {
      toast("New take ready", "success");
    }
  } else if (job.status === "failed") {
    toast(`Something went wrong with “${job.label}”. See the book's Activity tab.`, "error", 8000);
    notify("Audiobook Studio", `Something went wrong with “${job.label}”.`);
  } else if (job.status === "cancelled" && job.kind === "render") {
    toast("Paused. Progress is saved.");
  }
  if (pending?.onDone) pending.onDone(job);
}

function notify(title, body) {
  if (document.hidden && "Notification" in window && Notification.permission === "granted") new Notification(title, { body });
}

let pollTimer = null;
async function poll(immediate = false) {
  clearTimeout(pollTimer);
  try {
    const { jobs } = await api("GET", "/api/jobs");
    const prev = new Map(S.jobs.map((j) => [j.id, j.status]));
    S.jobs = jobs;
    for (const j of jobs) {
      const was = prev.get(j.id);
      if (["done", "failed", "cancelled"].includes(j.status) && !S.seenDone.has(j.id)) {
        S.seenDone.add(j.id);
        if (was && was !== j.status) onJobFinished(j);
      }
    }
    renderJobCard();
    const sig = jobs.map((j) => `${j.id}:${j.status}:${j.progress?.overall_done ?? ""}:${j.progress?.stage ?? ""}`).join("|");
    if (sig !== S.lastSig) {
      S.lastSig = sig;
      refreshLive();
    }
  } catch { /* server restarting */ }
  const busy = S.jobs.some((j) => j.status === "running" || j.status === "queued");
  pollTimer = setTimeout(poll, busy ? 1200 : 3500);
}

// Refresh the visible page in place when jobs move, without losing scroll or focus.
let liveHandler = null;
function refreshLive() { if (liveHandler) liveHandler(); }

// ---------------------------------------------------------------- quick speech

async function speak(text, { voice, temperature, title, subtitle, project, onDone } = {}) {
  try {
    const job = await api("POST", "/api/say", { text, voice, temperature, project, label: title });
    S.pending.set(job.id, { title: title || "Quick listen", subtitle: subtitle || (voice ? voiceLabel(voice) : ""), onDone });
    toast("Narrating… it will play in a moment.");
    poll(true);
    return job;
  } catch (e) { toast(e.message, "error"); return null; }
}

// ---------------------------------------------------------------- router

const view = () => $("#view");
let viewToken = 0;

function route() {
  const parts = (location.hash.replace(/^#\/?/, "") || "").split("/").filter(Boolean);
  S.route = parts;
  liveHandler = null;
  const token = ++viewToken;
  document.querySelectorAll(".nav a").forEach((a) => a.classList.toggle("active",
    a.dataset.nav === (parts[0] === "book" ? "library" : parts[0] || "library")));
  view().replaceChildren();
  window.scrollTo(0, 0);
  const page = parts[0] || "library";
  const pages = { library: Library, book: Book, voices: Voices, pronunciations: Pronunciations, settings: SettingsPage };
  (pages[page] || Library)(token, parts.slice(1));
}
const alive = (token) => token === viewToken;

// ---------------------------------------------------------------- library

const BOOK_EXT = [".epub", ".pdf", ".txt", ".md", ".markdown"];
const AUDIO_EXT = [".wav", ".mp3", ".m4a", ".aiff", ".aif", ".flac", ".caf", ".ogg"];
const ext = (name) => (name.match(/\.[^.]+$/) || [""])[0].toLowerCase();

async function Library(token) {
  const mode = localStorage.getItem("createMode") || "upload";
  const head = h("div", { class: "page-head" },
    h("div", {}, h("h1", { text: "Library" }), h("p", { text: "Turn any book or piece of writing into a narrated audiobook, entirely on this Mac." })));
  const createBody = h("div");
  const seg = h("div", { class: "seg", role: "tablist" });
  const setMode = (m) => {
    localStorage.setItem("createMode", m);
    seg.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.m === m));
    createBody.replaceChildren(m === "upload" ? uploadPanel() : pastePanel());
  };
  seg.append(
    h("button", { dataset: { m: "upload" }, onclick: () => setMode("upload") }, icon("upload", "i-sm"), "Book file"),
    h("button", { dataset: { m: "paste" }, onclick: () => setMode("paste") }, icon("paste", "i-sm"), "Paste text"));
  const create = h("section", { class: "card create" },
    h("div", { class: "create-top" }, h("h2", { text: "New audiobook" }), seg), createBody);
  const books = h("section", { class: "section" });
  view().append(head, create, books);
  setMode(mode);

  const draw = async () => {
    let data;
    try { data = await api("GET", "/api/state"); } catch (e) { return; }
    if (!alive(token)) return;
    S.jobs = data.jobs;
    renderJobCard();
    books.replaceChildren(
      h("div", { class: "section-head" }, h("h2", { text: "Your books" }), data.projects.length ? h("span", { class: "muted small", text: `${data.projects.length} ${data.projects.length === 1 ? "book" : "books"}` }) : null),
      data.projects.length ? h("div", { class: "books" }, data.projects.map(bookCard)) :
        h("div", { class: "empty" }, icon("book", "i-xl"), h("h3", { text: "No books yet" }), h("p", { class: "small", style: { margin: "6px 0 0" }, text: "Drop an ebook above, or paste some text to get started." })));
  };
  liveHandler = draw;
  draw();
}

function bookStatus(b) {
  const pct = b.chunks ? Math.floor((100 * b.chunks_done) / b.chunks) : 0;
  const jobPct = b.job?.progress?.overall_done != null && b.job.progress.overall_total ? Math.floor((100 * b.job.progress.overall_done) / b.job.progress.overall_total) : pct;
  switch (b.state) {
    case "rendering": return { badge: h("span", { class: "badge accent" }, h("span", { class: "dot pulse" }), `Narrating · ${jobPct}%`), pct: jobPct };
    case "queued": return { badge: h("span", { class: "badge" }, icon("clock", "i-sm"), "Waiting its turn"), pct };
    case "complete": return { badge: b.flagged ? h("span", { class: "badge warn" }, `Finished · ${b.flagged} to check`) : h("span", { class: "badge success" }, icon("check", "i-sm"), "Finished") };
    case "partial": return { badge: h("span", { class: "badge" }, `Paused · ${pct}%`), pct };
    case "error": return { badge: h("span", { class: "badge danger", text: "Needs attention" }) };
    default: return { badge: h("span", { class: "badge accent", text: "Ready to narrate" }) };
  }
}

function bookCard(b) {
  const st = bookStatus(b);
  const overlay = st.pct != null && b.state !== "new" && b.state !== "complete"
    ? h("div", { class: "state" }, h("div", { class: "progress" }, h("div", { style: { width: `${st.pct}%` } }))) : null;
  return h("a", { class: "book", href: `#/book/${b.slug}` },
    coverEl(b, overlay),
    h("div", { class: "book-meta" },
      h("div", { class: "t", text: b.title }),
      h("div", { class: "a", text: [b.author !== "Unknown" ? b.author : null, b.est_audio_seconds ? fmt.dur(b.est_audio_seconds) : null].filter(Boolean).join(" · ") }),
      h("div", { class: "s" }, st.badge)));
}

function uploadPanel() {
  const input = h("input", { type: "file", accept: BOOK_EXT.join(","), hidden: true, onchange: () => input.files[0] && importFile(input.files[0], zone) });
  const zone = h("div", {
    class: "dropzone", tabindex: "0", role: "button",
    onclick: () => input.click(),
    onkeydown: (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), input.click()),
    ondragover: (e) => { e.preventDefault(); zone.classList.add("over"); },
    ondragleave: () => zone.classList.remove("over"),
    ondrop: (e) => { e.preventDefault(); e.stopPropagation(); zone.classList.remove("over"); hideOverlay(); const f = e.dataTransfer.files[0]; f && importFile(f, zone); },
  },
  icon("upload", "i-xl"),
  h("h3", { text: "Drop a book here" }),
  h("p", {}, "or ", h("span", { style: { color: "var(--accent-text)", fontWeight: 600 }, text: "choose a file" }), " from your Mac"),
  h("div", { class: "formats" }, ["EPUB", "PDF", "TXT", "Markdown"].map((f) => h("span", { class: "badge", text: f }))),
  input);
  return zone;
}

async function importFile(file, zone) {
  if (!BOOK_EXT.includes(ext(file.name))) { toast("Please choose an EPUB, PDF, TXT or Markdown file.", "error"); return; }
  const bar = h("div", { style: { width: "0%" } });
  const label = h("div", { class: "small muted", text: `Uploading ${file.name}…` });
  const status = h("div", { class: "upload-status" }, h("div", { class: "spinner" }),
    h("div", { class: "grow stack", style: { gap: "8px" } }, h("div", { style: { fontWeight: 600 }, text: file.name }), h("div", { class: "progress" }, bar), label));
  const target = zone || $(".dropzone");
  if (target) target.replaceWith(status);
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await uploadWithProgress("/api/projects/upload", form, (f) => {
      bar.style.width = `${Math.round(f * 100)}%`;
      if (f >= 1) { label.textContent = "Reading the book and finding chapters…"; bar.parentElement.classList.add("indeterminate"); }
    });
    toast("Book imported. Have a look at the chapters, then press Narrate.", "success");
    location.hash = `#/book/${res.slug}`;
  } catch (e) {
    toast(e.message, "error", 8000);
    status.replaceWith(uploadPanel());
  }
}

function pastePanel() {
  const title = h("input", { class: "input", placeholder: "Title", maxlength: "120" });
  const author = h("input", { class: "input", placeholder: "Author (optional)", maxlength: "120" });
  const text = h("textarea", { class: "textarea reading", rows: "9", placeholder: "Paste or type text here. Leave a blank line between paragraphs. Lines like “Chapter 2” or “## Part Two” start new chapters." });
  const stats = h("span", { class: "muted small grow" });
  const readTitle = h("input", { type: "checkbox" });
  const listen = h("button", { class: "btn" }, icon("headphones"), "Listen now");
  const createBtn = h("button", { class: "btn btn-primary" }, icon("sparkle"), "Create audiobook");
  const draft = JSON.parse(localStorage.getItem("pasteDraft") || "{}");
  title.value = draft.title || ""; author.value = draft.author || ""; text.value = draft.text || "";
  const update = () => {
    const words = (text.value.match(/\S+/g) || []).length;
    const listenMin = words / 155;
    stats.textContent = words ? `${fmt.num(words)} words · about ${fmt.dur(listenMin * 60)} of listening · takes about ${fmt.dur(listenMin * 60 * 0.95 + 15)} to make` : "";
    listen.disabled = !words || text.value.length > 20000;
    listen.title = text.value.length > 20000 ? "Long texts work better as an audiobook" : "Hear it right away as a single track";
    createBtn.disabled = !words;
    localStorage.setItem("pasteDraft", JSON.stringify({ title: title.value, author: author.value, text: text.value }));
  };
  [title, author, text].forEach((el) => el.addEventListener("input", update));
  update();
  listen.onclick = () => speak(text.value, { title: title.value || "Pasted text", subtitle: "Quick listen" });
  createBtn.onclick = async () => {
    createBtn.disabled = true;
    try {
      const res = await api("POST", "/api/projects/text", { title: title.value, author: author.value, text: text.value, speak_titles: readTitle.checked });
      localStorage.removeItem("pasteDraft");
      toast("Created. Press Narrate when you're ready.", "success");
      location.hash = `#/book/${res.slug}`;
    } catch (e) { toast(e.message, "error"); createBtn.disabled = false; }
  };
  return h("div", {},
    h("div", { class: "paste-grid" }, title, author),
    h("div", { style: { marginTop: "12px" } }, text),
    h("div", { class: "paste-foot" }, stats,
      h("label", { class: "switch small" }, readTitle, "Read titles aloud"),
      listen, createBtn));
}

// ---------------------------------------------------------------- book page

async function Book(token, [slug]) {
  let tab = sessionStorage.getItem(`tab:${slug}`) || "chapters";
  let voices = null;
  const root = view();
  const draw = async () => {
    let b;
    try { b = await api("GET", `/api/projects/${slug}`); } catch (e) {
      if (alive(token)) root.replaceChildren(h("a", { class: "back", href: "#/" }, icon("chevronLeft"), "Library"), h("div", { class: "empty" }, h("h3", { text: "Book not found" }), h("p", { text: e.message })));
      return;
    }
    if (!voices) { try { voices = (await api("GET", "/api/voices")).voices; } catch { voices = []; } }
    if (!alive(token)) return;
    const scroll = window.scrollY;
    root.replaceChildren(renderBook(b, voices, tab, (t) => { tab = t; sessionStorage.setItem(`tab:${slug}`, t); draw(); }, draw));
    window.scrollTo(0, scroll);
  };
  liveHandler = draw;
  await draw();
}

function renderBook(b, voices, tab, setTab, redraw) {
  const art = { title: b.title, author: b.author, cover: b.cover };
  const facts = h("div", { class: "facts" },
    h("span", { class: "badge" }, icon("book", "i-sm"), `${b.chapters} ${b.chapters === 1 ? "chapter" : "chapters"}`),
    h("span", { class: "badge", text: `${fmt.num(b.words)} words` }),
    h("span", { class: "badge" }, icon("clock", "i-sm"), `about ${fmt.dur(b.est_audio_seconds)}`),
    h("span", { class: "badge" }, icon("mic", "i-sm"), voiceLabel(b.voice)));
  const editBtn = h("button", { class: "btn btn-sm btn-ghost", onclick: () => editMeta(b, redraw) }, icon("edit"), "Edit details");
  const hero = h("div", { class: "hero" },
    coverEl(art),
    h("div", {},
      h("h1", { text: b.title }),
      h("div", { class: "author", text: b.author && b.author !== "Unknown" ? `by ${b.author}` : "Author unknown" }),
      facts,
      actionPanel(b, art),
      h("div", { class: "row", style: { marginTop: "10px" } }, editBtn,
        h("button", { class: "btn btn-sm btn-ghost", onclick: () => api("POST", `/api/projects/${b.slug}/reveal`).catch((e) => toast(e.message, "error")) }, icon("folder"), "Show in Finder"),
        h("button", { class: "btn btn-sm btn-ghost", onclick: () => archiveBook(b) }, icon("trash"), "Remove from library"))));

  const tabs = h("div", { class: "tabs", role: "tablist" },
    tabBtn("chapters", "Chapters", b.chapter_list.length, tab, setTab),
    tabBtn("flags", "Needs a listen", b.flagged, tab, setTab, b.flagged ? "warn" : ""),
    tabBtn("settings", "Voice & settings", null, tab, setTab),
    tabBtn("activity", "Activity", null, tab, setTab));
  let body;
  if (tab === "flags") body = flagsTab(b, art);
  else if (tab === "settings") body = bookSettings(b, voices, redraw);
  else if (tab === "activity") body = activityTab(b);
  else body = chaptersTab(b, art, redraw);
  return h("div", {}, h("a", { class: "back", href: "#/" }, icon("chevronLeft"), "Library"), hero, tabs, body);
}

function tabBtn(id, label, count, tab, setTab, cls = "") {
  return h("button", { class: tab === id ? "on" : "", role: "tab", onclick: () => setTab(id) }, label,
    count != null ? h("span", { class: `count ${cls}`, text: String(count) }) : null);
}

function actionPanel(b, art) {
  const job = b.job;
  if (b.error) return h("div", { class: "callout warn action-panel" }, icon("alert"), h("div", {}, h("b", { text: "This book can't be narrated yet. " }), b.error));
  if (job) {
    const p = job.progress || {};
    const total = p.overall_total || b.chunks;
    const doneN = p.overall_done ?? b.chunks_done;
    const pct = total ? (100 * doneN) / total : 0;
    const indet = job.status === "queued" || ["loading", "starting", "mastering", "packaging"].includes(p.stage) || !p.stage;
    const kindWord = { render: "Narrating the book", preview: `Previewing chapter ${job.extra?.chapter ?? ""}`, redo: "Re-recording selected pieces" }[job.kind] || "Working";
    return h("div", { class: "card action-panel" },
      h("div", { class: "big-progress" },
        h("div", { class: "row" },
          h("span", { class: "dot pulse", style: { color: "var(--accent)" } }),
          h("h3", { class: "grow", text: job.status === "queued" ? "Waiting for another job to finish" : kindWord }),
          job.kind === "render" ? h("span", { style: { fontWeight: 700, fontVariantNumeric: "tabular-nums" }, text: `${Math.floor(pct)}%` }) : null,
          h("button", { class: "btn btn-sm", onclick: () => cancelJob(job) }, icon(job.kind === "render" ? "pause" : "x"), job.kind === "render" ? "Pause" : "Stop")),
        h("div", { class: "progress lg" + (indet ? " indeterminate" : "") }, h("div", { style: { width: `${job.kind === "render" ? pct : p.pct || 0}%` } })),
        h("div", { class: "stat-line" },
          h("span", {}, job.kind === "render" && p.eta_seconds != null && p.stage === "narrating" ? `${fmt.dur(p.eta_seconds)} left` : jobStage(job)),
          job.kind === "render" ? h("span", {}, h("b", { text: fmt.num(doneN) }), ` of ${fmt.num(total)} pieces`) : null,
          p.eta_seconds != null ? h("span", {}, "ready around ", h("b", { text: fmt.clock(p.eta_seconds) })) : null,
          p.flagged ? h("span", { class: "badge warn", text: `${p.flagged} to check` }) : null),
        p.current_text && p.stage === "narrating" ? h("div", { class: "now-reading", text: `“${p.current_text}”` }) : null));
  }
  if (b.state === "complete") {
    return h("div", { class: "card action-panel" },
      h("div", { class: "row" },
        h("span", { class: "badge success" }, icon("check", "i-sm"), "Ready"),
        h("h3", { class: "grow", text: "Your audiobook is finished" })),
      h("div", { class: "row", style: { marginTop: "14px" } },
        h("a", { class: "btn btn-primary", href: b.m4b, download: b.m4b_name }, icon("download"), "Download audiobook (.m4b)"),
        b.chapter_list[0]?.mp3 ? h("button", { class: "btn", onclick: () => Player.play(b.chapter_list[0].mp3, b.chapter_list[0].title, b.title, art) }, icon("play"), "Play from the start") : null,
        b.flagged ? h("span", { class: "muted small", text: `${b.flagged} spot(s) in "Needs a listen"` }) : null));
  }
  const started = b.chunks_done > 0;
  const btn = h("button", { class: "btn btn-primary btn-lg", onclick: () => startRender(b) }, icon("play"), started ? "Resume narrating" : "Narrate the book");
  const firstCh = b.chapter_list[0];
  return h("div", { class: "card action-panel" },
    h("div", { class: "row" }, btn,
      firstCh ? h("button", { class: "btn btn-lg", onclick: () => startPreview(b, firstCh.number) }, icon("headphones"), "Preview chapter 1") : null),
    h("div", { class: "stat-line", style: { marginTop: "14px" } },
      started ? h("span", {}, h("b", { text: `${Math.floor((100 * b.chunks_done) / Math.max(1, b.chunks))}%` }), " done") : null,
      h("span", {}, "takes about ", h("b", { text: fmt.dur(b.est_render_seconds) })),
      h("span", {}, "ready around ", h("b", { text: fmt.clock(b.est_render_seconds) }), " if you start now")),
    b.est_render_seconds > 1800 ? h("p", { class: "tiny faint", style: { margin: "10px 0 0" }, text: "Long run: keep the Mac plugged in with the lid open. You can pause any time and pick up where you left off." }) : null);
}

async function startRender(b) {
  try {
    if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();
    await api("POST", `/api/projects/${b.slug}/render`);
    toast("Narration started. You can leave this page; it keeps going.", "success");
    poll(true);
  } catch (e) { toast(e.message, "error"); }
}

async function startPreview(b, number) {
  try {
    await api("POST", `/api/projects/${b.slug}/preview`, { chapter: number });
    toast(`Previewing chapter ${number}. It will play when ready.`);
    poll(true);
  } catch (e) { toast(e.message, "error"); }
}

function chaptersTab(b, art, redraw) {
  if (!b.chapter_list.length) return h("div", { class: "empty" }, h("h3", { text: "No chapters" }), h("p", { text: "All chapters are skipped. Restore one below." }), skippedList(b, redraw));
  const rows = b.chapter_list.map((c) => {
    const pct = c.chunks ? (100 * c.done) / c.chunks : 0;
    const done = c.chunks && c.done === c.chunks;
    const prog = h("div", { class: "prog" },
      h("div", { class: "progress" + (done ? " success" : "") }, h("div", { style: { width: `${pct}%` } })),
      h("span", { text: done ? (c.flagged ? `Done · ${c.flagged} to check` : "Done") : c.done ? `${c.done} of ${c.chunks} pieces` : `${c.minutes} min · not started` }));
    const listenUrl = c.mp3 || c.preview;
    return h("div", { class: "chapter" },
      h("div", { class: "num", text: String(c.number) }),
      h("div", { style: { minWidth: 0 } }, h("div", { class: "ttl", text: c.title }), h("div", { class: "sub", text: c.first_line })),
      prog,
      h("div", { class: "acts" },
        listenUrl ? playButton(listenUrl, c.title, c.mp3 ? b.title : `${b.title} · preview`, art, { label: c.mp3 ? "Play chapter" : "Play preview" }) : null,
        h("button", { class: "icon-btn", title: "Preview this chapter", "aria-label": "Preview this chapter", disabled: !!b.job, onclick: () => startPreview(b, c.number) }, icon("headphones")),
        h("button", { class: "icon-btn", title: "Edit text", "aria-label": "Edit text", onclick: () => editChapter(b, c, redraw) }, icon("edit")),
        h("button", { class: "icon-btn", title: "Skip this chapter", "aria-label": "Skip this chapter", disabled: !!b.job, onclick: () => skipChapter(b, c, redraw) }, icon("skip"))));
  });
  return h("div", {}, h("div", { class: "chapters" }, rows), skippedList(b, redraw));
}

function skippedList(b, redraw) {
  if (!b.skipped.length) return null;
  return h("div", { class: "section" },
    h("div", { class: "section-head" }, h("h3", { text: "Skipped" }), h("span", { class: "muted small", text: "Not narrated. Restore to include them." })),
    h("div", { class: "chapters" }, b.skipped.map((s) => h("div", { class: "chapter" },
      h("div", { class: "num", text: s.file.replace(".txt", "").replace(/^0+/, "") }),
      h("div", { class: "ttl faint", text: s.title }), h("div"),
      h("div", { class: "acts" }, h("button", { class: "btn btn-sm", onclick: async () => {
        try { await api("POST", `/api/projects/${b.slug}/chapters/${s.file}/restore`); redraw(); } catch (e) { toast(e.message, "error"); }
      } }, icon("restore"), "Restore"))))));
}

async function skipChapter(b, c, redraw) {
  try {
    await api("POST", `/api/projects/${b.slug}/chapters/${c.file}/skip`);
    toast(`Skipped “${c.title}”. You can restore it below.`);
    redraw();
  } catch (e) { toast(e.message, "error"); }
}

async function editChapter(b, c, redraw) {
  let data;
  try { data = await api("GET", `/api/projects/${b.slug}/chapters/${c.file}`); } catch (e) { toast(e.message, "error"); return; }
  const ta = h("textarea", { class: "textarea reading", style: { minHeight: "52vh" } });
  ta.value = data.text;
  modal({
    title: `Edit chapter ${c.number}`,
    subtitle: "The first line (starting with #) is the chapter title. Leave a blank line between paragraphs. Only changed paragraphs are re-recorded; your previous version is kept.",
    body: ta,
    actions: [
      (close) => h("button", { class: "btn btn-ghost", text: "Cancel", onclick: close }),
      (close) => h("button", { class: "btn btn-primary", onclick: async () => {
        try { await api("PUT", `/api/projects/${b.slug}/chapters/${c.file}`, { text: ta.value }); close(); toast("Saved", "success"); redraw(); }
        catch (e) { toast(e.message, "error"); }
      } }, icon("check"), "Save"),
    ],
  });
}

function editMeta(b, redraw) {
  const t = h("input", { class: "input", value: b.title });
  const a = h("input", { class: "input", value: b.author === "Unknown" ? "" : b.author });
  modal({
    title: "Book details", narrow: true,
    body: h("div", { class: "stack" }, h("label", { class: "field" }, h("span", { text: "Title" }), t), h("label", { class: "field" }, h("span", { text: "Author" }), a),
      h("p", { class: "tiny faint", style: { margin: 0 }, text: "Used for the audiobook's tags and file name." })),
    actions: [
      (close) => h("button", { class: "btn btn-ghost", text: "Cancel", onclick: close }),
      (close) => h("button", { class: "btn btn-primary", text: "Save", onclick: async () => {
        try { await api("PATCH", `/api/projects/${b.slug}`, { title: t.value, author: a.value }); close(); redraw(); } catch (e) { toast(e.message, "error"); }
      } }),
    ],
  });
}

async function archiveBook(b) {
  const ok = await confirmBox("Remove from library?", "The book moves to projects/_archived on your Mac. Nothing is deleted; you can move it back any time.", "Remove");
  if (!ok) return;
  try { await api("POST", `/api/projects/${b.slug}/archive`); toast("Removed from library"); location.hash = "#/"; } catch (e) { toast(e.message, "error"); }
}

function flagsTab(b, art) {
  if (!b.flagged_list.length) {
    return h("div", { class: "empty" }, icon("check", "i-xl"), h("h3", { text: b.chunks_done ? "Nothing to check" : "Nothing narrated yet" }),
      h("p", { class: "small", style: { margin: "6px 0 0" }, text: b.chunks_done ? "Every piece narrated so far passed the automatic checks." : "After narration, any piece that didn't pass the automatic checks shows up here." }));
  }
  const redoAll = h("button", { class: "btn btn-sm", disabled: !!b.job, onclick: () => redo(b, b.flagged_list.map((f) => f.id)) }, icon("redo"), "Re-record all");
  return h("div", {},
    h("div", { class: "callout", style: { marginBottom: "16px" } }, icon("info"),
      h("div", { class: "grow" }, "These pieces still didn't match the text after automatic retries. Listen to each; unusual names often show up here even when they sound fine. If one sounds wrong, re-record it, or fix the spelling in Pronunciations."), redoAll),
    b.flagged_list.map((f) => h("div", { class: "card flag" },
      playButton(f.audio, `Piece ${f.id}`, b.title, art, { label: "Play this piece" }),
      h("div", {},
        h("div", { class: "row", style: { marginBottom: "6px" } }, h("span", { class: "badge", text: `Chapter ${f.chapter} · piece ${f.id}` }), f.problems.map((p) => h("span", { class: "badge warn", text: p }))),
        h("div", { class: "q", text: f.text }),
        h("div", { class: "heard" }, h("b", { text: "Heard: " }), f.heard || "(nothing)")),
      h("button", { class: "btn btn-sm", disabled: !!b.job, onclick: () => redo(b, [f.id]) }, icon("redo"), "Re-record"))));
}

async function redo(b, ids) {
  try { await api("POST", `/api/projects/${b.slug}/redo`, { ids }); toast(`Re-recording ${ids.length} piece(s)…`); poll(true); } catch (e) { toast(e.message, "error"); }
}

function activityTab(b) {
  const j = b.job || b.last_job;
  if (!j) return h("div", { class: "empty" }, h("h3", { text: "No activity yet" }), h("p", { class: "small", text: "Progress messages from narration appear here." }));
  const log = h("div", { class: "log", text: (j.log || [j.last_line]).join("\n") });
  setTimeout(() => { log.scrollTop = log.scrollHeight; }, 0);
  if (b.job) api("GET", `/api/jobs/${b.job.id}`).then((d) => { log.textContent = d.log.join("\n"); log.scrollTop = log.scrollHeight; }).catch(() => {});
  return h("div", {}, h("div", { class: "row", style: { marginBottom: "10px" } },
    h("span", { class: "badge", text: `${JOB_WORD[j.kind] || j.kind} · ${j.status}` })), log);
}

function bookSettings(b, voices, redraw) {
  const sel = h("select", { class: "select" }, voices.map((v) => h("option", { value: v.id, selected: v.id === b.voice, text: `${v.name}${v.kind === "preset" ? " (built-in)" : ""}` })));
  const temp = h("input", { type: "range", min: "0.5", max: "1.2", step: "0.05", value: String(b.temperature) });
  const tempVal = h("b", { text: Number(b.temperature).toFixed(2) });
  temp.oninput = () => { tempVal.textContent = Number(temp.value).toFixed(2); };
  const titles = h("input", { type: "checkbox", checked: b.speak_titles });
  const save = async (patch) => {
    try { await api("PATCH", `/api/projects/${b.slug}`, patch); toast("Saved for this book", "success"); redraw(); } catch (e) { toast(e.message, "error"); }
  };
  sel.onchange = () => save({ voice: sel.value });
  temp.onchange = () => save({ temperature: Number(temp.value) });
  titles.onchange = () => save({ speak_titles: titles.checked });
  const sample = h("button", { class: "btn btn-sm", onclick: () => speak(b.chapter_list[0]?.first_line || "Hello. This is how this book will sound.", { voice: sel.value, temperature: Number(temp.value), title: "Voice check", subtitle: voiceLabel(sel.value), project: b.slug }) }, icon("headphones"), "Hear a sample");
  return h("div", { class: "card card-pad stack", style: { gap: "20px" } },
    b.chunks_done ? h("div", { class: "callout warn" }, icon("info"), h("span", { text: "Changing the voice or liveliness re-records the book from the start. Pieces already made in the current voice are kept, so switching back is instant." })) : null,
    h("div", { class: "settings-grid" },
      h("label", { class: "field" }, h("span", { text: "Narrator voice" }), sel),
      h("div", { class: "field" }, h("span", {}, "Liveliness ", tempVal), temp, h("div", { class: "range-labels" }, h("span", { text: "Steadier" }), h("span", { text: "Livelier" }))),
      h("div", { class: "field" }, h("span", { text: "Chapter titles" }), h("label", { class: "switch" }, titles, "Read each chapter title aloud"))),
    h("div", { class: "row" }, sample, h("span", { class: "tiny faint", text: "Plays the first line of the book with these settings." })));
}

// ---------------------------------------------------------------- voices

async function Voices(token) {
  const draw = async () => {
    let data;
    try { data = await api("GET", "/api/voices"); } catch (e) { toast(e.message, "error"); return; }
    if (!alive(token)) return;
    S.voices = data.voices;
    const mine = data.voices.filter((v) => v.kind !== "preset").sort((a, b) => (b.default - a.default) || a.name.localeCompare(b.name));
    const presets = data.voices.filter((v) => v.kind === "preset");
    view().replaceChildren(
      h("div", { class: "page-head" }, h("div", {}, h("h1", { text: "Voices" }), h("p", { text: "Choose who reads your books. The default voice is used for new books; each book can pick its own." }))),
      h("div", { class: "voices" }, mine.map((v) => voiceCard(v, draw))),
      h("section", { class: "section" }, h("div", { class: "section-head" }, h("h2", { text: "Built-in speakers" }), h("span", { class: "muted small", text: "From Qwen3-TTS" })),
        h("div", { class: "voices" }, presets.map((v) => voiceCard(v, draw)))),
      h("section", { class: "section" }, addVoicePanel(draw)));
  };
  liveHandler = null;
  await draw();
}

function voiceCard(v, redraw) {
  const tryBox = h("div", { hidden: true, class: "stack", style: { gap: "8px" } });
  const tryText = h("textarea", { class: "textarea", rows: "2", style: { minHeight: "64px" } });
  tryText.value = "It was late in the evening when the letter finally arrived, and the house had fallen quiet.";
  tryBox.append(tryText, h("div", { class: "row" },
    h("button", { class: "btn btn-sm btn-primary", onclick: () => speak(tryText.value, { voice: v.id, title: v.name, subtitle: "Voice test" }) }, icon("play"), "Speak"),
    h("span", { class: "tiny faint", text: "Takes a few seconds the first time." })));
  const wave = h("div", { class: "wave", dataset: { waveUrl: v.sample || "" } }, Array.from({ length: 28 }, (_, i) => h("span", { style: { height: `${6 + ((hashStr(v.id + i) % 18))}px` } })));
  const kindBadge = { designed: h("span", { class: "badge", text: "Designed" }), clone: h("span", { class: "badge accent", text: "Your clip" }), preset: h("span", { class: "badge", text: "Built-in" }) }[v.kind];
  return h("div", { class: "card voice" + (v.default ? " is-default" : "") },
    h("div", { class: "voice-head" }, avatarEl(v.name),
      h("div", { class: "grow" }, h("div", { class: "voice-name", text: v.name }), h("div", { class: "row", style: { gap: "6px", marginTop: "3px" } }, kindBadge, v.default ? h("span", { class: "badge success" }, icon("star", "i-sm"), "Default") : null)),
      v.sample ? playButton(v.sample, v.name, "Voice sample", null, { big: true, label: "Play sample" }) : null),
    h("div", { class: "voice-desc", text: v.description || (v.transcript ? `“${v.transcript}”` : "") }),
    v.sample ? wave : null,
    h("div", { class: "row" },
      h("button", { class: "btn btn-sm", onclick: () => { tryBox.hidden = !tryBox.hidden; } }, icon("headphones"), "Try it"),
      v.default ? null : h("button", { class: "btn btn-sm btn-ghost", onclick: async () => {
        try { await api("POST", "/api/voices/default", { voice: v.id }); toast(`${v.name} is now the default voice`, "success"); redraw(); } catch (e) { toast(e.message, "error"); }
      } }, "Make default")),
    tryBox);
}

function addVoicePanel(redraw, file = null) {
  let chosen = file;
  const name = h("input", { class: "input", placeholder: "Name, e.g. my-voice" });
  const transcript = h("textarea", { class: "textarea", rows: "3", placeholder: "Type exactly what is said in the clip, word for word." });
  const desc = h("input", { class: "input", placeholder: "Short description (optional)" });
  const fileLabel = h("span", { class: "muted", text: chosen ? chosen.name : "No clip chosen" });
  const input = h("input", { type: "file", accept: AUDIO_EXT.join(","), hidden: true, onchange: () => { chosen = input.files[0]; fileLabel.textContent = chosen ? chosen.name : ""; } });
  const zone = h("div", {
    class: "dropzone", style: { padding: "26px" }, onclick: () => input.click(),
    ondragover: (e) => { e.preventDefault(); zone.classList.add("over"); }, ondragleave: () => zone.classList.remove("over"),
    ondrop: (e) => { e.preventDefault(); e.stopPropagation(); hideOverlay(); zone.classList.remove("over"); chosen = e.dataTransfer.files[0]; fileLabel.textContent = chosen ? chosen.name : ""; },
  }, icon("mic", "i-xl"), h("h3", { text: "Drop a voice clip" }), fileLabel, input);
  const btn = h("button", { class: "btn btn-primary" }, icon("plus"), "Add voice");
  btn.onclick = async () => {
    if (!chosen) return toast("Choose a clip first.", "error");
    if (!name.value.trim()) return toast("Give the voice a name.", "error");
    const form = new FormData();
    form.append("file", chosen); form.append("name", name.value); form.append("transcript", transcript.value); form.append("description", desc.value);
    btn.disabled = true;
    try {
      const res = await api("POST", "/api/voices", form);
      toast(`Voice “${res.id}” added (${res.seconds} s).`, "success");
      res.warnings.forEach((w) => toast(w, "info", 7000));
      redraw();
    } catch (e) { toast(e.message, "error", 7000); btn.disabled = false; }
  };
  return h("div", { class: "card card-pad" },
    h("div", { class: "section-head" }, h("h2", { text: "Add your own voice" })),
    h("div", { class: "settings-grid", style: { alignItems: "start" } },
      h("div", { class: "stack" }, zone,
        h("ul", { class: "small muted", style: { margin: "4px 0 0", paddingLeft: "18px", lineHeight: 1.7 } },
          h("li", { text: "10–30 seconds of one person reading calmly" }),
          h("li", { text: "A quiet room: no music, echo or background noise" }),
          h("li", { text: "Read the way you want the whole book read" }),
          h("li", { text: "Only your own voice, or one you have permission to use" }))),
      h("div", { class: "stack" },
        h("label", { class: "field" }, h("span", { text: "Name" }), name),
        h("label", { class: "field" }, h("span", { text: "Exact transcript" }), transcript),
        h("label", { class: "field" }, h("span", { text: "Description" }), desc),
        h("div", { class: "row" }, btn, h("span", { class: "tiny faint", text: "Silence is trimmed and volume evened out automatically. Your clips are never uploaded anywhere." })))));
}

// ---------------------------------------------------------------- pronunciations

async function Pronunciations(token) {
  let data;
  try { data = await api("GET", "/api/pronunciations"); } catch (e) { toast(e.message, "error"); return; }
  if (!alive(token)) return;
  const tbody = h("tbody");
  const addRow = (word = "", say = "") => {
    const w = h("input", { class: "input", value: word, placeholder: "Word as written" });
    const s = h("input", { class: "input", value: say, placeholder: "How to say it, e.g. her-MY-oh-nee" });
    const tr = h("tr", {},
      h("td", {}, w), h("td", { class: "arrow" }, "→"), h("td", {}, s),
      h("td", { style: { whiteSpace: "nowrap" } },
        h("button", { class: "icon-btn", title: "Hear it", "aria-label": "Hear it", onclick: () => s.value.trim() && speak(`${s.value.trim()}.`, { title: w.value || s.value, subtitle: "Pronunciation" }) }, icon("headphones")),
        h("button", { class: "icon-btn", title: "Remove", "aria-label": "Remove", onclick: () => { tr.remove(); dirty(); } }, icon("x"))));
    [w, s].forEach((el) => el.addEventListener("input", dirty));
    tbody.append(tr);
    return w;
  };
  const save = h("button", { class: "btn btn-primary", disabled: true }, icon("check"), "Save");
  function dirty() { save.disabled = false; }
  data.entries.forEach((e) => addRow(e.word, e.say));
  if (!data.entries.length) addRow();
  save.onclick = async () => {
    const entries = [...tbody.querySelectorAll("tr")].map((tr) => { const [w, s] = tr.querySelectorAll("input"); return { word: w.value, say: s.value }; });
    try { await api("PUT", "/api/pronunciations", { entries }); save.disabled = true; toast("Saved. Only pieces with these words will be re-recorded.", "success"); } catch (e) { toast(e.message, "error"); }
  };
  view().replaceChildren(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", { text: "Pronunciations" }), h("p", { text: "Teach the narrator how to say unusual names and words. Applies to every book." })),
      save),
    h("div", { class: "callout", style: { marginBottom: "18px" } }, icon("info"),
      h("div", {}, "Spell it the way it sounds, with hyphens between syllables and the ", h("b", { text: "stressed syllable in capitals" }),
        ": Hermione → her-MY-oh-nee, Aoife → Eefa. Press ", icon("headphones", "i-sm"), " to hear it.")),
    h("div", { class: "card card-pad" },
      h("table", { class: "pron-table" }, h("thead", {}, h("tr", {}, h("th", { text: "In the book" }), h("th"), h("th", { text: "Say it like" }), h("th"))), tbody),
      h("button", { class: "btn btn-sm", style: { marginTop: "12px" }, onclick: () => { addRow().focus(); dirty(); } }, icon("plus"), "Add a word")));
}

// ---------------------------------------------------------------- settings

async function SettingsPage(token) {
  let s, voices;
  try { [s, voices] = await Promise.all([api("GET", "/api/settings"), api("GET", "/api/voices")]); } catch (e) { toast(e.message, "error"); return; }
  if (!alive(token)) return;
  const voice = h("select", { class: "select" }, voices.voices.map((v) => h("option", { value: v.id, selected: v.id === s.voice, text: `${v.name}${v.kind === "preset" ? " (built-in)" : ""}` })));
  const temp = h("input", { type: "range", min: "0.5", max: "1.2", step: "0.05", value: String(s.temperature) });
  const tempVal = h("b", { text: Number(s.temperature).toFixed(2) });
  temp.oninput = () => { tempVal.textContent = Number(temp.value).toFixed(2); };
  const num = (v, step, min, max) => h("input", { class: "input", type: "number", step, min, max, value: String(v) });
  const sentence = num(s.sentence, "0.05", "0", "2"), paragraph = num(s.paragraph, "0.05", "0", "4"), afterTitle = num(s.after_title, "0.25", "0", "6");
  const titles = h("input", { type: "checkbox", checked: s.speak_titles });
  const wer = num(Math.round(s.wer_threshold * 100), "1", "1", "50"), retries = num(s.max_retries, "1", "0", "6");
  const save = h("button", { class: "btn btn-primary" }, icon("check"), "Save settings");
  save.onclick = async () => {
    try {
      await api("PUT", "/api/settings", {
        voice: voice.value, temperature: Number(temp.value), sentence: Number(sentence.value), paragraph: Number(paragraph.value),
        after_title: Number(afterTitle.value), speak_titles: titles.checked, wer_threshold: Number(wer.value) / 100, max_retries: Number(retries.value),
      });
      toast("Settings saved", "success");
    } catch (e) { toast(e.message, "error"); }
  };
  const sys = s.system;
  const info = (k, v) => h("div", { class: "row", style: { justifyContent: "space-between", padding: "8px 0", borderTop: "1px solid var(--border)" } }, h("span", { class: "muted", text: k }), h("span", { style: { fontWeight: 600 }, text: v }));
  view().replaceChildren(
    h("div", { class: "page-head" }, h("div", {}, h("h1", { text: "Settings" }), h("p", { text: "Defaults for every book. Each book can override the voice and liveliness on its own page." })), save),
    h("div", { class: "card card-pad stack", style: { gap: "24px" } },
      h("div", {}, h("h2", { text: "Narration", style: { marginBottom: "14px" } }),
        h("div", { class: "settings-grid" },
          h("label", { class: "field" }, h("span", { text: "Default voice" }), voice),
          h("div", { class: "field" }, h("span", {}, "Liveliness ", tempVal), temp, h("div", { class: "range-labels" }, h("span", { text: "Steadier" }), h("span", { text: "Livelier" }))),
          h("div", { class: "field" }, h("span", { text: "Chapter titles" }), h("label", { class: "switch" }, titles, "Read titles aloud")))),
      h("div", {}, h("h2", { text: "Pauses (seconds)", style: { marginBottom: "14px" } }),
        h("div", { class: "settings-grid" },
          h("label", { class: "field" }, h("span", { text: "Between sentences in a paragraph" }), sentence),
          h("label", { class: "field" }, h("span", { text: "Between paragraphs" }), paragraph),
          h("label", { class: "field" }, h("span", { text: "After a chapter title" }), afterTitle))),
      h("div", {}, h("h2", { text: "Quality checks", style: { marginBottom: "6px" } }),
        h("p", { class: "muted small", style: { margin: "0 0 14px" }, text: "Every piece is transcribed and compared with the book. Pieces with too many differences are re-recorded automatically." }),
        h("div", { class: "settings-grid" },
          h("label", { class: "field" }, h("span", { text: "Re-record when more than this % of words differ" }), wer),
          h("label", { class: "field" }, h("span", { text: "Maximum retries per piece" }), retries)))),
    h("section", { class: "section" },
      h("div", { class: "card card-pad" },
        h("div", { class: "section-head" }, h("h2", { text: "This Mac" }),
          h("button", { class: "btn btn-sm", onclick: () => api("POST", "/api/reveal-root") }, icon("folder"), "Open AudiobookTTS folder")),
        info("Chip", sys.chip), info("Memory", `${sys.memory_gb} GB${sys.memory_free_pct != null ? ` · ${sys.memory_free_pct}% free now` : ""}`),
        info("Free disk space", `${sys.disk_free_gb} GB`), info("Narration model", s.model.split("/").pop()), info("mlx-audio", sys.mlx_audio),
        info("Folder", sys.folder))));
}

// ---------------------------------------------------------------- global drag & drop

let dragDepth = 0;
function showOverlay(title, sub) { $("#drop-overlay-title").textContent = title; $("#drop-overlay-sub").textContent = sub; $("#drop-overlay").hidden = false; }
function hideOverlay() { dragDepth = 0; $("#drop-overlay").hidden = true; }
function initDrop() {
  const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
  window.addEventListener("dragenter", (e) => {
    if (!hasFiles(e)) return;
    dragDepth++;
    if (S.route[0] === "voices") showOverlay("Drop a voice clip", "WAV, MP3, M4A, AIFF or FLAC");
    else showOverlay("Drop to import", "EPUB, PDF, TXT or Markdown");
  });
  window.addEventListener("dragleave", (e) => { if (hasFiles(e) && --dragDepth <= 0) hideOverlay(); });
  window.addEventListener("dragover", (e) => hasFiles(e) && e.preventDefault());
  window.addEventListener("drop", (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    hideOverlay();
    const f = e.dataTransfer.files[0];
    if (!f) return;
    if (AUDIO_EXT.includes(ext(f.name)) && S.route[0] === "voices") {
      const panel = document.querySelector(".section:last-child");
      const fresh = addVoicePanel(() => route(), f);
      if (panel) panel.replaceChildren(fresh);
      fresh.scrollIntoView({ behavior: "smooth" });
      toast(`Clip “${f.name}” ready. Add a name and transcript.`);
    } else if (BOOK_EXT.includes(ext(f.name))) {
      if (S.route[0] && S.route[0] !== "library") { location.hash = "#/"; setTimeout(() => importFile(f), 50); }
      else importFile(f);
    } else {
      toast("That file type isn't supported here.", "error");
    }
  });
}

// ---------------------------------------------------------------- start

hydrateIcons();
Player.init();
initDrop();
window.addEventListener("hashchange", route);
route();
poll();
