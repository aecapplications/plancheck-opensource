"use strict";

const $ = (id) => document.getElementById(id);
let jobId = null;
let pollTimer = null;
let result = null;
let booksInfo = [];      // registry from /api/books
let jobBooks = [];       // book ids of the current job
let currentBook = null;  // book whose results are displayed

const PHASE_LABELS = {
  queued: "Queued",
  validating: "Validating PDF",
  classifying: "Classifying sheets",
  text_pass: "Reading notes & schedules",
  vision_pass: "Analyzing drawings",
  reconciling: "Reconciling facts",
  plan_check: "Running rule engine",
  rendering: "Building report",
  done: "Done",
};
const PHASE_ORDER = Object.keys(PHASE_LABELS);

// ---- Upload ----
const dz = $("dropzone");
const fileInput = $("file-input");

dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
dz.addEventListener("drop", (e) => {
  e.preventDefault(); dz.classList.remove("drag");
  if (e.dataTransfer.files.length) upload(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) upload(fileInput.files[0]);
});

// ---- Code-book selection ----
async function loadBooks() {
  try {
    const r = await fetch("/api/books");
    booksInfo = await r.json();
  } catch (err) { booksInfo = []; }
  const el = $("book-options");
  if (!booksInfo.length) { $("book-select").classList.add("hidden"); return; }
  el.innerHTML = booksInfo.map((b) => `
    <label class="book-option ${b.available ? "" : "disabled"}">
      <input type="checkbox" name="books" value="${escapeHtml(b.id)}"
             ${b.id === "crc" && b.available ? "checked" : ""}
             ${b.available ? "" : "disabled"} />
      <span class="bshort">${escapeHtml(b.short)}</span>
      <span class="blabel">${escapeHtml(b.label)}</span>
      <span class="bhint hint">${b.available
        ? `${b.rule_count} rules`
        : "rules not yet extracted"}</span>
    </label>`).join("");
}

function selectedBooks() {
  return [...document.querySelectorAll('#book-options input:checked')]
    .map((i) => i.value);
}

function bookShort(id) {
  const b = booksInfo.find((x) => x.id === id);
  return b ? b.short : id.toUpperCase();
}

async function upload(file) {
  const chosen = selectedBooks();
  if (booksInfo.length && !chosen.length) {
    alert("Select at least one code book to check against.");
    return;
  }
  const fd = new FormData();
  fd.append("file", file);
  chosen.forEach((id) => fd.append("books", id));
  $("upload-card").classList.add("hidden");
  $("progress-card").classList.remove("hidden");
  $("progress-phase").textContent = "Uploading…";
  try {
    const r = await fetch("/api/jobs", { method: "POST", body: fd });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    jobId = (await r.json()).job_id;
    poll();
  } catch (err) {
    showError(err.message);
  }
}

// ---- Polling ----
async function pollTick() {
  try {
    const r = await fetch(`/api/jobs/${jobId}`);
    if (r.status === 404) { clearInterval(pollTimer); showError(`Unknown job "${jobId}"`); return; }
    const s = await r.json();
    jobBooks = s.books || [];
    updateProgress(s);
    if (s.state === "done") { clearInterval(pollTimer); loadResult(); }
    if (s.state === "error") { clearInterval(pollTimer); showError(s.error, s.warnings); }
  } catch (err) { /* transient; keep polling */ }
}

function poll() {
  pollTimer = setInterval(pollTick, 2500);
  pollTick();
}

function updateProgress(s) {
  $("progress-phase").textContent = PHASE_LABELS[s.phase] || s.phase;
  $("progress-msg").textContent = s.message || "";
  let pct;
  if (s.progress && s.progress.total) {
    pct = 100 * s.progress.done / s.progress.total;
    $("progress-msg").textContent =
      `${s.message || ""} (${s.progress.done}/${s.progress.total})`;
  } else {
    const idx = PHASE_ORDER.indexOf(s.phase);
    pct = idx >= 0 ? (idx / (PHASE_ORDER.length - 1)) * 100 : 5;
  }
  $("progress-fill").style.width = `${pct}%`;
  renderBookProgress(s);

  // Live LLM calls can run for minutes with no phase change; show how stale
  // the status is so "working" and "stuck" are distinguishable.
  if (s.updated_at) {
    const age = Math.max(0, Math.round(Date.now() / 1000 - s.updated_at));
    $("progress-updated").textContent =
      age < 5 ? "" : `Last update ${age < 120 ? age + "s" : Math.round(age / 60) + " min"} ago
        — extraction calls can take a few minutes each.`;
  }

  const wel = $("progress-warnings");
  const warnings = s.warnings || [];
  if (warnings.length) {
    wel.classList.remove("hidden");
    wel.innerHTML = `<div class="warnings-title">${warnings.length} step(s)
      degraded so far — continuing with fallbacks:</div>` + warningListHtml(warnings);
  }
}

function renderBookProgress(s) {
  const el = $("book-progress");
  const bs = s.book_status || {};
  const ids = (s.books || []).filter((b) => bs[b]);
  // Per-book rows only add signal for multi-book jobs mid-flight.
  if (ids.length < 2 || s.state !== "running") { el.innerHTML = ""; return; }
  el.innerHTML = ids.map((id) => {
    const b = bs[id];
    const pct = b.progress_total ? 100 * b.progress_done / b.progress_total
      : (b.state === "done" ? 100 : 0);
    const note = b.error ? escapeHtml(b.error)
      : `${escapeHtml(b.message || b.phase)}` +
        (b.progress_total ? ` (${b.progress_done}/${b.progress_total})` : "");
    return `<div class="book-row ${b.state}">
      <span class="bshort">${escapeHtml(bookShort(id))}</span>
      <div class="bar mini"><div class="bar-fill" style="width:${pct}%"></div></div>
      <span class="bnote hint">${note}</span>
    </div>`;
  }).join("");
}

function showError(msg, warnings) {
  $("progress-card").classList.add("hidden");
  $("error-card").classList.remove("hidden");
  $("error-msg").textContent = msg || "Unknown error";
  const el = $("error-warnings");
  if (warnings && warnings.length) {
    el.classList.remove("hidden");
    el.innerHTML = `<div class="warnings-title">Before failing, ${warnings.length}
      step(s) were skipped:</div>` + warningListHtml(warnings);
  }
}

function warningListHtml(warnings) {
  return `<ul>` + warnings.map((w) => {
    const where = w.page ? ` — p.${w.page}${w.sheet_id ? " " + escapeHtml(w.sheet_id) : ""}` : "";
    const detail = w.detail
      ? `<details><summary>detail</summary><pre>${escapeHtml(w.detail)}</pre></details>` : "";
    return `<li><span class="wphase">${escapeHtml(w.phase || "")}</span>
      ${escapeHtml(w.message || "")}${where}${detail}</li>`;
  }).join("") + `</ul>`;
}

// ---- Results ----
function artifactUrl(kind) {
  return (jobBooks.length > 1 && currentBook)
    ? `/api/jobs/${jobId}/books/${encodeURIComponent(currentBook)}/${kind}`
    : `/api/jobs/${jobId}/${kind}`;
}

async function loadResult() {
  $("progress-card").classList.add("hidden");
  $("results").classList.remove("hidden");
  renderChips();
  // Deep link: ?job=<id>&book=<book_id> opens on that book's results.
  const urlBook = new URLSearchParams(location.search).get("book");
  const start = jobBooks.includes(urlBook) ? urlBook : (jobBooks[0] || null);
  await loadBookResult(start);
}

function renderChips() {
  const el = $("book-chips");
  if (jobBooks.length < 2) { el.classList.add("hidden"); return; }
  el.classList.remove("hidden");
  el.innerHTML = jobBooks.map((id) => `
    <button class="chip" data-book="${escapeHtml(id)}">${escapeHtml(bookShort(id))}</button>`).join("");
  el.querySelectorAll(".chip").forEach((c) =>
    c.addEventListener("click", () => loadBookResult(c.dataset.book)));
}

async function loadBookResult(bookId) {
  currentBook = bookId;
  document.querySelectorAll("#book-chips .chip").forEach((c) =>
    c.classList.toggle("active", c.dataset.book === bookId));
  const r = await fetch(artifactUrl("result"));
  if (!r.ok) {
    // A failed book has no result.json; say so instead of showing stale data.
    $("warnings-banner").classList.remove("hidden");
    $("warnings-banner").innerHTML = `<div class="warnings-title">No results for
      ${escapeHtml(bookShort(bookId))} — this book's check failed.</div>`;
    $("summary").innerHTML = "";
    $("sheet-grid").innerHTML = "";
    $("flag-panel").innerHTML = "";
    $("tab-unmapped").innerHTML = "";
    $("tab-review").innerHTML = "";
    $("report-md").innerHTML = "";
    return;
  }
  result = await r.json();
  renderWarnings();
  renderSummary();
  renderSheets();
  renderUnmapped();
  renderReview();
  loadReport();
}

function renderWarnings() {
  const el = $("warnings-banner");
  const warnings = result.warnings || [];
  if (!warnings.length) { el.classList.add("hidden"); return; }
  el.classList.remove("hidden");
  el.innerHTML = `<div class="warnings-title">${warnings.length} item(s) were
    skipped or degraded during extraction — results may be incomplete.</div>` +
    warningListHtml(warnings);
}

function renderSummary() {
  const s = result.summary;
  const cells = [
    [s.rules_fired, "Rules fired"],
    [s.pages_flagged, "Sheets flagged"],
    [s.chains, "Compliance chains"],
    [s.evidence_items, "Evidence items"],
    [s.unmapped_rules, "Project-level"],
    [s.needs_review, "Needs review"],
  ];
  if (result.summary.warnings)
    cells.push([result.summary.warnings, "Warnings"]);
  if (result.usage && result.usage.estimated_cost_usd != null)
    cells.push(["$" + result.usage.estimated_cost_usd, "Est. cost"]);
  $("summary").innerHTML = cells.map(
    ([n, l]) => `<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`
  ).join("");
}

function renderSheets() {
  const grid = $("sheet-grid");
  if (!result.pages.length) {
    grid.innerHTML = `<p class="hint">No sheet-level flags. See project-level findings.</p>`;
    return;
  }
  grid.innerHTML = result.pages.map((p) => `
    <div class="sheet" data-page="${p.page}">
      <span class="badge ${p.max_severity}">${p.flag_count}</span>
      <img loading="lazy" src="/api/jobs/${jobId}/pages/${p.page}.png" alt="sheet ${p.page}" />
      <div class="meta">
        <div class="sid">${p.sheet_id || "Page " + p.page}</div>
        <div class="stype">${(p.sheet_type || "").replace(/_/g, " ")}</div>
      </div>
    </div>`).join("");
  grid.querySelectorAll(".sheet").forEach((el) =>
    el.addEventListener("click", () => selectSheet(+el.dataset.page, el)));
  selectSheet(result.pages[0].page, grid.querySelector(".sheet"));
}

function selectSheet(page, el) {
  document.querySelectorAll(".sheet").forEach((s) => s.classList.remove("selected"));
  if (el) el.classList.add("selected");
  const p = result.pages.find((x) => x.page === page);
  const panel = $("flag-panel");
  panel.innerHTML =
    `<h3>${p.sheet_id || "Page " + p.page} — ${p.flag_count} flag(s)</h3>` +
    p.flags.map(flagHtml).join("");
}

function flagHtml(f) {
  const ev = f.evidence ? `<div class="ev">“${escapeHtml(f.evidence)}”</div>` : "";
  const conf = f.confidence != null ? `<span class="conf">conf ${(f.confidence).toFixed(2)}</span>` : "";
  const reqs = (f.evidence_required || []).length
    ? `<ul>${f.evidence_required.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul>` : "";
  return `<div class="flag ${f.severity}">
    ${conf}
    <div class="cite">${f.cite || ""}</div>
    <div class="title">${escapeHtml(f.title || "")}</div>
    ${f.via_predicate ? `<div class="pred">${f.via_predicate}</div>` : ""}
    ${ev}
    ${reqs}
  </div>`;
}

function renderUnmapped() {
  const el = $("tab-unmapped");
  if (!result.unmapped_rules.length) {
    el.innerHTML = `<p class="hint">No project-level findings.</p>`; return;
  }
  el.innerHTML = `<p class="hint">Rules triggered by project metadata (seismic
    category, climate zone, fire zone, etc.) rather than a specific sheet.</p>` +
    result.unmapped_rules.map(flagHtml).join("");
}

function renderReview() {
  const el = $("tab-review");
  if (!result.needs_review.length) {
    el.innerHTML = `<p class="hint">No low-confidence or conflicting facts.</p>`; return;
  }
  el.innerHTML = result.needs_review.map((c) => `
    <div class="flag recommended">
      <span class="conf">conf ${(c.confidence ?? 0).toFixed(2)}</span>
      <div class="pred">${c.predicate} = ${c.value}</div>
      <div class="ev">“${escapeHtml(c.evidence || "")}” — p.${c.page || "?"} ${c.sheet_id || ""}</div>
    </div>`).join("");
}

async function loadReport() {
  const r = await fetch(artifactUrl("report"));
  const md = await r.text();
  const el = $("report-md");
  if (window.marked && window.DOMPurify) {
    el.innerHTML = DOMPurify.sanitize(marked.parse(md, { gfm: true, breaks: false }));
  } else {
    // CDN unavailable — fall back to plain text
    const pre = document.createElement("pre");
    pre.textContent = md;
    el.replaceChildren(pre);
  }
}

// ---- Tabs ----
document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((x) => x.classList.add("hidden"));
    t.classList.add("active");
    $("tab-" + t.dataset.tab).classList.remove("hidden");
  }));

function escapeHtml(s) {
  return (s || "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ---- Open an existing job via ?job=<id>, or list past jobs ----
async function loadRecentJobs() {
  try {
    const r = await fetch("/api/jobs");
    const jobs = await r.json();
    if (!jobs.length) { $("recent-jobs").classList.add("hidden"); return; }
    $("recent-jobs").classList.remove("hidden");
    $("recent-list").innerHTML = jobs.map((j) => `
      <li>
        <a href="?job=${encodeURIComponent(j.job_id)}">${escapeHtml(j.filename || j.job_id)}</a>
        <span class="jstate ${j.state}">${escapeHtml(j.state)}</span>
        <span class="jmsg hint">${escapeHtml(j.message || j.error || "")}</span>
        <span class="jdate hint">${j.created_at ? new Date(j.created_at * 1000).toLocaleString() : ""}</span>
        <button class="jdelete" data-job="${escapeHtml(j.job_id)}"
                title="Delete this job and all its files">✕</button>
      </li>`).join("");
    $("recent-list").querySelectorAll(".jdelete").forEach((btn) =>
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        deleteJob(btn.dataset.job);
      }));
  } catch (err) { /* listing is optional */ }
}

async function deleteJob(id) {
  if (!confirm(`Delete this job and all its files (upload, results, report)?\n\nJob ${id} — this cannot be undone.`)) return;
  try {
    const r = await fetch(`/api/jobs/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      alert(body.detail || `Delete failed (${r.status})`);
      return;
    }
    loadRecentJobs();
  } catch (err) {
    alert("Delete failed — is the server running?");
  }
}

loadBooks();
const urlJob = new URLSearchParams(location.search).get("job");
if (urlJob) {
  jobId = urlJob;
  $("upload-card").classList.add("hidden");
  $("progress-card").classList.remove("hidden");
  $("progress-phase").textContent = "Loading job…";
  poll();
} else {
  loadRecentJobs();
}
