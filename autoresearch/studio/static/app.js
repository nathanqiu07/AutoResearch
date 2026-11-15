/* Profile Studio frontend. Plain JS, no build step. Every server value is escaped with esc()
   before it goes into markup. */
"use strict";

const PDFJS = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/";
const TEXT_EXT = ["txt", "md", "markdown", "tex", "rst", "bib", "json", "csv", "html", "htm", "org"];
const S = { config: null, st: null, slug: null, polling: {} };
const app = document.getElementById("app");

// ---------- helpers ----------
function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
async function api(method, path, body) {
  const r = await fetch(path, {
    method, headers: body ? { "content-type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}
let toastTimer;
function toast(msg, isError) {
  const t = document.getElementById("toast");
  t.textContent = msg; t.className = "toast" + (isError ? " error" : ""); t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), isError ? 6000 : 2800);
}
function fail(e) { toast(e.message || String(e), true); }
function on(sel, ev, fn, root = app) { root.querySelectorAll(sel).forEach(el => el.addEventListener(ev, fn)); }
function val(id) { const el = document.getElementById(id); return el ? el.value.trim() : ""; }
function fmtNum(n) { return Number(n || 0).toLocaleString(); }
function store(key, v) { try { v === undefined ? localStorage.removeItem(key) : localStorage.setItem(key, JSON.stringify(v)); } catch (_) {} }
function load(key) { try { return JSON.parse(localStorage.getItem(key) || "null"); } catch (_) { return null; } }
function go(hash) { if (location.hash === hash) render(); else location.hash = hash; }

// ---------- routing ----------
window.addEventListener("hashchange", () => { window.scrollTo(0, 0); render(); });
(async function boot() {
  try { S.config = await api("GET", "/api/config"); } catch (e) { app.innerHTML = `<div class="notice bad">Could not reach the studio server: ${esc(e.message)}</div>`; return; }
  render();
})();

// Views await the server before drawing; a render started later wins, so fast navigation never
// leaves an older view on screen.
let renderSeq = 0;
const stale = seq => seq !== renderSeq;

async function render() {
  const seq = ++renderSeq;
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  try {
    if (!parts.length) return await viewHome(seq);
    if (parts[0] === "new" && parts[1] === "personal") return viewNewPersonal();
    if (parts[0] === "new" && parts[1] === "public") return viewNewPublic();
    if (parts[0] === "p" && parts[1]) return await viewWorkspace(parts[1], parts[2], seq);
    go("#/");
  } catch (e) { if (!stale(seq)) app.innerHTML = `<div class="notice bad">${esc(e.message)}</div><p><a href="#/">Back to profiles</a></p>`; }
}

// ---------- home ----------
async function viewHome(seq) {
  const profiles = await api("GET", "/api/profiles");
  if (stale(seq)) return;
  const rows = profiles.map(p => `
    <tr class="clickable" data-slug="${esc(p.slug)}">
      <td><strong>${esc(p.name)}</strong><div class="muted small mono">${esc(p.slug)}</div></td>
      <td><span class="badge ${esc(p.mode)}">${p.mode === "external" ? "read-only" : esc(p.mode)}</span></td>
      <td>${fmtNum(p.n_docs)}</td>
      <td>${p.has_profile ? '<span class="badge ok">profile.json</span>' : '<span class="badge">not built</span>'}
          ${p.has_usermodel ? '<span class="badge ok">usermodel.json</span>' : ""}</td>
      <td class="muted small">${esc((p.updated || "").slice(0, 10))}</td>
    </tr>`).join("");
  app.innerHTML = `
    <section class="hero">
      <h1>Build a researcher profile</h1>
      <p>A profile captures how a researcher makes decisions: what they value, what they avoid, and how they trade off
      realism, rigour, cost and novelty. The research loop uses it to steer which experiments it proposes and runs
      (<code>--researcher &lt;id&gt;</code>).</p>
    </section>
    <section class="mode-cards">
      <a class="card mode-card" href="#/new/personal">
        <div class="mode-icon" aria-hidden="true">✎</div>
        <h2>Your own profile</h2>
        <p class="muted">From your papers and writing, plus a questionnaire about how you work.</p>
        <ul>
          <li>Upload papers, drafts, notes (PDF, Markdown, LaTeX, text)</li>
          <li>Import your publication record</li>
          <li>Open questions + forced-choice trade-offs</li>
          <li>Optionally fit a user model on your choices</li>
        </ul>
        <span class="go">Start →</span>
      </a>
      <a class="card mode-card" href="#/new/public">
        <div class="mode-icon public" aria-hidden="true">⌕</div>
        <h2>A known researcher</h2>
        <p class="muted">From someone's public record, gathered automatically.</p>
        <ul>
          <li>Find the right person among same-named authors</li>
          <li>Papers from Semantic Scholar and arXiv</li>
          <li>Blog posts, LessWrong, web pages, optional Exa harvest</li>
          <li>Review the corpus before building</li>
        </ul>
        <span class="go">Start →</span>
      </a>
    </section>
    <section class="card">
      <div class="row"><h2 style="margin:0">Profiles</h2><span class="spacer"></span>
        <span class="muted small mono">${esc(S.config.root)}</span></div>
      ${profiles.length ? `<div class="table-wrap"><table class="list" style="margin-top:.75rem">
        <thead><tr><th>Researcher</th><th>Mode</th><th>Docs</th><th>Output</th><th>Updated</th></tr></thead>
        <tbody>${rows}</tbody></table></div>` : `<div class="empty">No profiles yet.</div>`}
    </section>`;
  on("tr[data-slug]", "click", e => go(`#/p/${e.currentTarget.dataset.slug}`));
}

// ---------- new personal ----------
function viewNewPersonal() {
  app.innerHTML = `
    <p><a href="#/">← Profiles</a></p>
    <div class="card" style="max-width:640px">
      <h1>Your own profile</h1>
      <p class="muted">Start with who you are. You'll add material and answer questions next; you can stop and come back at any point.</p>
      <div class="stack">
        <label class="field"><span>Full name</span><input id="np-name" type="text" autocomplete="name"></label>
        <label class="field"><span>Profile id</span><input id="np-slug" type="text" class="mono" placeholder="from your name">
          <small>Lowercase letters, digits and _. This is what you pass to <code>--researcher</code>.</small></label>
        <label class="field"><span>Affiliation <span class="muted">(optional)</span></span><input id="np-aff" type="text"></label>
        <div class="row end"><button class="btn primary" id="np-create">Create profile</button></div>
      </div>
    </div>`;
  const name = document.getElementById("np-name"), slug = document.getElementById("np-slug");
  name.focus();
  name.addEventListener("input", () => { if (!slug.dataset.touched) slug.value = slugify(name.value); });
  slug.addEventListener("input", () => (slug.dataset.touched = "1"));
  on("#np-create", "click", async () => {
    try {
      const meta = await api("POST", "/api/profiles", { name: val("np-name"), mode: "personal", slug: val("np-slug") });
      if (val("np-aff")) await api("PATCH", `/api/profiles/${meta.slug}`, { affiliation: val("np-aff") });
      go(`#/p/${meta.slug}/about`);
    } catch (e) { fail(e); }
  });
}
function slugify(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, ""); }

// ---------- new public ----------
function viewNewPublic() {
  app.innerHTML = `
    <p><a href="#/">← Profiles</a></p>
    <div class="card">
      <h1>Profile a known researcher</h1>
      <p class="muted">Search by name, then pick the right person. Several authors often share a name, so check the affiliation and top papers.</p>
      <div class="row">
        <input id="pub-name" type="text" placeholder="e.g. a researcher's full name" style="flex:1;min-width:220px">
        <button class="btn primary" id="pub-search">Search</button>
      </div>
      <div id="pub-results" style="margin-top:1.25rem"></div>
    </div>`;
  const input = document.getElementById("pub-name");
  input.focus();
  input.addEventListener("keydown", e => { if (e.key === "Enter") doSearch(); });
  on("#pub-search", "click", doSearch);

  async function doSearch() {
    const name = input.value.trim();
    if (!name) return;
    const box = document.getElementById("pub-results");
    box.innerHTML = `<div class="row muted"><span class="spinner"></span> Searching Semantic Scholar and Wikipedia…</div>`;
    const [cands, wiki] = await Promise.all([
      api("GET", `/api/search/s2?name=${encodeURIComponent(name)}`).catch(e => ({ error: e.message })),
      api("GET", `/api/search/wikipedia?name=${encodeURIComponent(name)}`).catch(() => null),
    ]);
    renderCandidates(box, name, cands, wiki, async (picked, useWiki) => {
      try {
        const meta = await api("POST", "/api/profiles", { name: val("pub-final-name") || name, mode: "public", slug: val("pub-final-slug") });
        const patch = {};
        if (picked) patch.s2_author = picked;
        if (picked && picked.affiliations && picked.affiliations.length) patch.affiliation = picked.affiliations.join("; ");
        if (useWiki && wiki) { patch.bio = wiki.extract; patch.bio_source = wiki.url; }
        if (Object.keys(patch).length) await api("PATCH", `/api/profiles/${meta.slug}`, patch);
        go(`#/p/${meta.slug}/sources`);
      } catch (e) { fail(e); }
    });
  }
}

/* Candidate list shared by the public flow and "import my publications". onPick(candidate|null, useWiki). */
function renderCandidates(box, name, cands, wiki, onPick, opts = {}) {
  let selected = null;
  const list = Array.isArray(cands) ? cands : [];
  const err = cands && cands.error ? `<div class="notice warn">Semantic Scholar: ${esc(cands.error)}. You can still continue with arXiv and web sources.</div>` : "";
  const wikiHtml = wiki && !opts.noWiki ? `
    <div class="notice" style="margin-bottom:1rem">
      <div class="row"><strong>Wikipedia: ${esc(wiki.title)}</strong><span class="muted small">${esc(wiki.description)}</span></div>
      <p class="small" style="margin:.4rem 0">${esc(wiki.extract)}</p>
      <label class="check small"><input type="checkbox" id="use-wiki" checked> Use as the bio on the profile card (not used as taste evidence)</label>
    </div>` : "";
  box.innerHTML = `${err}${wikiHtml}
    ${list.length ? `<h3>Semantic Scholar authors named “${esc(name)}”</h3>` : (!err ? `<div class="notice">No Semantic Scholar author found. You can continue with arXiv and web sources.</div>` : "")}
    <div id="cands">${list.map((c, i) => `
      <div class="cand" data-i="${i}">
        <input type="radio" name="cand" value="${i}" aria-label="Select ${esc(c.name)}">
        <div style="flex:1">
          <div class="row"><strong>${esc(c.name)}</strong>
            ${c.affiliations.length ? `<span class="muted small">${esc(c.affiliations.join("; "))}</span>` : ""}
            <span class="spacer"></span><a class="small" href="${esc(c.url)}" target="_blank" rel="noopener">Semantic Scholar ↗</a></div>
          <div class="stats"><span><b>${fmtNum(c.papers)}</b> papers</span><span><b>${fmtNum(c.citations)}</b> citations</span><span>h-index <b>${fmtNum(c.h_index)}</b></span></div>
          <div class="titles"><button class="btn ghost small" data-titles="${esc(c.author_id)}">Show top papers</button></div>
        </div>
      </div>`).join("")}</div>
    <hr class="hr">
    ${opts.noCreate ? "" : `<div class="grid2">
      <label class="field"><span>Profile name</span><input id="pub-final-name" type="text" value="${esc(name)}"></label>
      <label class="field"><span>Profile id</span><input id="pub-final-slug" type="text" class="mono" value="${esc(slugify(name))}"></label>
    </div>`}
    <div class="row end" style="margin-top:1rem">
      ${list.length ? `<span class="muted small" id="cand-hint">Select an author${opts.noCreate ? "" : ", or continue without one"}.</span>` : ""}
      ${opts.noCreate ? "" : `<button class="btn" id="cand-none">Continue without Semantic Scholar</button>`}
      ${list.length ? `<button class="btn primary" id="cand-go" disabled>${esc(opts.goLabel || "Create profile with this author")}</button>` : ""}
    </div>`;
  box.querySelectorAll(".cand").forEach(el => el.addEventListener("click", e => {
    if (e.target.closest("button,a")) return;
    box.querySelectorAll(".cand").forEach(c => c.classList.remove("selected"));
    el.classList.add("selected"); el.querySelector("input").checked = true;
    selected = list[+el.dataset.i];
    const go = box.querySelector("#cand-go"); if (go) go.disabled = false;
  }));
  box.querySelectorAll("[data-titles]").forEach(b => b.addEventListener("click", async () => {
    const holder = b.parentElement; holder.innerHTML = `<span class="muted small"><span class="spinner"></span> loading…</span>`;
    try {
      const titles = await api("GET", `/api/search/s2/${b.dataset.titles}/titles`);
      holder.innerHTML = titles.length ? `<ul>${titles.map(t => `<li>${esc(t)}</li>`).join("")}</ul>` : `<span class="muted small">no papers listed</span>`;
    } catch (e) { holder.innerHTML = `<span class="muted small">${esc(e.message)}</span>`; }
  }));
  const useWiki = () => { const c = box.querySelector("#use-wiki"); return !!(c && c.checked); };
  const goBtn = box.querySelector("#cand-go"); if (goBtn) goBtn.addEventListener("click", () => onPick(selected, useWiki()));
  const noneBtn = box.querySelector("#cand-none"); if (noneBtn) noneBtn.addEventListener("click", () => onPick(null, useWiki()));
}

// ---------- workspace ----------
const STEPS = {
  personal: [["about", "About & consent"], ["materials", "Materials"], ["questionnaire", "Questionnaire"], ["tradeoffs", "Trade-offs"], ["build", "Build & review"], ["use", "Use in the loop"]],
  public: [["identity", "Identity"], ["sources", "Gather sources"], ["corpus", "Review corpus"], ["build", "Build & review"], ["use", "Use in the loop"]],
  external: [["build", "Profile"], ["corpus", "Corpus"], ["use", "Use in the loop"]],
};

async function refresh(slug) {
  S.st = await api("GET", `/api/profiles/${slug || S.slug}`);
  document.querySelectorAll(".step[data-step]").forEach((el, i) => {   // keep the sidebar ticks current
    const done = !!stepDone(el.dataset.step);
    el.classList.toggle("done", done);
    el.querySelector(".num").textContent = done ? "✓" : i + 1;
  });
  return S.st;
}

function stepDone(step) {
  const st = S.st, m = st.meta;
  const ownDocs = st.docs.filter(d => d.source !== "questionnaire").length;
  return {
    about: st.consent.length && st.consent.every(c => c.ticked),
    materials: ownDocs > 0,
    questionnaire: Object.keys(m.questionnaire || {}).length > 0,
    tradeoffs: st.choices.answered > 0,
    identity: !!(m.s2_author || m.bio),
    sources: st.docs.length > 0,
    corpus: st.docs.length > 0,
    build: !!st.profile,
    use: false,
  }[step];
}

async function viewWorkspace(slug, step, seq) {
  const st = await api("GET", `/api/profiles/${slug}`);
  if (stale(seq)) return;
  S.slug = slug; S.st = st;
  const mode = S.st.editable ? S.st.meta.mode : "external";
  const steps = STEPS[mode] || STEPS.external;
  if (!step || !steps.some(s => s[0] === step)) return go(`#/p/${slug}/${steps[0][0]}`);
  app.innerHTML = `
    <p><a href="#/">← Profiles</a></p>
    <div class="workspace">
      <nav class="steps" aria-label="Steps">
        <div class="steps-head"><h2>${esc(S.st.meta.name)}</h2>
          <span class="badge ${esc(mode)}">${mode === "external" ? "read-only" : esc(mode)}</span>
          <span class="muted small mono">${esc(slug)}</span></div>
        ${steps.map(([k, label], i) => `<a class="step ${k === step ? "active" : ""} ${stepDone(k) ? "done" : ""}" data-step="${k}" href="#/p/${esc(slug)}/${k}">
          <span class="num">${stepDone(k) ? "✓" : i + 1}</span>${esc(label)}</a>`).join("")}
      </nav>
      <section id="panel"></section>
    </div>`;
  const panel = document.getElementById("panel");
  const next = steps[steps.findIndex(s => s[0] === step) + 1];
  const nextBtn = next ? `<div class="row end" style="margin-top:1.25rem"><a class="btn" href="#/p/${esc(slug)}/${next[0]}">Next: ${esc(next[1])} →</a></div>` : "";
  const views = { about: panelAbout, materials: panelMaterials, questionnaire: panelQuestionnaire, tradeoffs: panelTradeoffs,
                  identity: panelIdentity, sources: panelSources, corpus: panelCorpus, build: panelBuild, use: panelUse };
  await views[step](panel, nextBtn, seq);
}

function head(title, desc) { return `<div class="section-head"><div><h1>${esc(title)}</h1>${desc ? `<p>${desc}</p>` : ""}</div></div>`; }

// ----- About & consent (personal)
function panelAbout(panel, nextBtn) {
  const m = S.st.meta;
  panel.innerHTML = head("About you", "Basic details for the profile card, and your consent for how your answers are used.") + `
    <div class="card stack">
      <div class="grid2">
        <label class="field"><span>Full name</span><input id="ab-name" type="text" value="${esc(m.name)}"></label>
        <label class="field"><span>Affiliation</span><input id="ab-aff" type="text" value="${esc(m.affiliation)}"></label>
      </div>
      <label class="field"><span>Homepage</span><input id="ab-home" type="url" value="${esc(m.homepage)}" placeholder="https://"></label>
      <label class="field"><span>Short bio <span class="muted">(optional)</span></span><textarea id="ab-bio" rows="3">${esc(m.bio)}</textarea>
        <small>Shown on the profile card and given to the summary writer. Not used as taste evidence.</small></label>
    </div>
    <div class="card stack">
      <h3>Consent</h3>
      <p class="muted small">This is the personal track's consent form (<code>CONSENT.md</code>). Trade-off items stay locked until every box is ticked.</p>
      ${S.st.consent.map((c, i) => `<label class="check"><input type="checkbox" data-consent="${i}" ${c.ticked ? "checked" : ""}><span>${esc(c.text)}</span></label>`).join("")}
    </div>
    <div class="row end" style="margin-top:1rem"><button class="btn primary" id="ab-save">Save</button></div>${nextBtn}`;
  on("#ab-save", "click", async () => {
    try {
      await api("PATCH", `/api/profiles/${S.slug}`, { name: val("ab-name"), affiliation: val("ab-aff"), homepage: val("ab-home"), bio: val("ab-bio"), bio_source: "self" });
      const ticked = [...panel.querySelectorAll("[data-consent]")].map(c => c.checked);
      await api("POST", `/api/profiles/${S.slug}/consent`, { ticked });
      toast("Saved"); render();
    } catch (e) { fail(e); }
  });
}

// ----- Materials (personal)
function panelMaterials(panel, nextBtn) {
  const queue = [];
  panel.innerHTML = head("Your materials", "Anything you have written: papers, drafts, blog posts, research notes, reviews, talk transcripts. Writing outside research (marked <em>other</em>) counts too, at lower weight.") + `
    <div class="card">
      <h3>Upload files</h3>
      <div class="drop" id="drop" tabindex="0" role="button" aria-label="Choose files to upload">
        <strong>Drop files here</strong> or click to choose<br><span class="small">PDF, Markdown, LaTeX, plain text, HTML, BibTeX. Text is extracted in your browser.</span>
      </div>
      <input type="file" id="file-input" multiple hidden accept=".pdf,${TEXT_EXT.map(e => "." + e).join(",")}">
      <div class="file-queue" id="queue"></div>
      <div class="row end" style="margin-top:.75rem"><button class="btn primary" id="upload" disabled>Add files</button></div>
    </div>
    <div class="card stack">
      <h3>Paste text</h3>
      <div class="grid2">
        <label class="field"><span>Title</span><input id="paste-title" type="text" placeholder="e.g. Research statement"></label>
        <label class="field"><span>Kind</span><select id="paste-kind"><option value="research">research</option><option value="other">other (non-research)</option></select></label>
      </div>
      <textarea id="paste-text" rows="6" placeholder="Paste a research statement, abstract, review, notes…"></textarea>
      <div class="row end"><button class="btn" id="paste-add">Add text</button></div>
    </div>
    <div class="card stack">
      <h3>Links</h3>
      <label class="field"><span>Pages you wrote, one per line</span><textarea id="links" rows="3" placeholder="https://your-blog.example/post"></textarea>
        <small>Each page is fetched and its text saved. Pages that need a login or render with JavaScript may come back empty.</small></label>
      <div class="row end"><button class="btn" id="links-add">Fetch pages</button></div>
    </div>
    <div class="card stack">
      <h3>Import your publications</h3>
      <p class="muted small">Find yourself on Semantic Scholar, and/or match your name on arXiv. Only papers with an abstract are imported.</p>
      <div class="row">
        <input id="pub-me" type="text" value="${esc(S.st.meta.name)}" style="flex:1;min-width:200px">
        <label class="check small"><input type="checkbox" id="pub-arxiv" checked> also arXiv</label>
        <button class="btn" id="pub-find">Find me</button>
      </div>
      <div id="pub-box"></div>
    </div>
    <div id="job"></div>
    <div class="card" id="corpus"></div>${nextBtn}`;
  renderCorpus(document.getElementById("corpus"));

  const drop = document.getElementById("drop"), input = document.getElementById("file-input");
  drop.addEventListener("click", () => input.click());
  drop.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", e => { e.preventDefault(); drop.classList.remove("over"); addFiles(e.dataTransfer.files); });
  input.addEventListener("change", () => { addFiles(input.files); input.value = ""; });

  async function addFiles(files) {
    for (const f of files) {
      const item = { file: f, title: f.name.replace(/\.[^.]+$/, ""), kind: "research", text: null, status: "reading…" };
      queue.push(item); drawQueue();
      try { item.text = await extractText(f); item.status = `${fmtNum(item.text.length)} chars`; if (!item.text.trim()) item.status = "no text found"; }
      catch (e) { item.status = "could not read: " + e.message; }
      drawQueue();
    }
  }
  function drawQueue() {
    const q = document.getElementById("queue");
    q.innerHTML = queue.map((it, i) => `<div class="file-item">
      <span class="name" title="${esc(it.file.name)}">${esc(it.file.name)}</span>
      <span class="muted small">${esc(it.status)}</span>
      <select data-kind="${i}"><option value="research" ${it.kind === "research" ? "selected" : ""}>research</option><option value="other" ${it.kind === "other" ? "selected" : ""}>other</option></select>
      <button class="btn ghost small" data-rm="${i}" aria-label="Remove ${esc(it.file.name)}">✕</button></div>`).join("");
    q.querySelectorAll("[data-kind]").forEach(s => s.addEventListener("change", () => (queue[+s.dataset.kind].kind = s.value)));
    q.querySelectorAll("[data-rm]").forEach(b => b.addEventListener("click", () => { queue.splice(+b.dataset.rm, 1); drawQueue(); }));
    document.getElementById("upload").disabled = !queue.some(it => it.text && it.text.trim());
  }
  on("#upload", "click", async () => {
    let n = 0;
    for (const it of queue.filter(it => it.text && it.text.trim())) {
      try { await api("POST", `/api/profiles/${S.slug}/docs`, { kind: it.kind, title: it.title, text: it.text, source: "upload", filename: it.file.name }); n++; }
      catch (e) { fail(e); }
    }
    queue.length = 0; drawQueue(); toast(`Added ${n} file${n === 1 ? "" : "s"}`);
    await refresh(); renderCorpus(document.getElementById("corpus"));
  });
  on("#paste-add", "click", async () => {
    try {
      await api("POST", `/api/profiles/${S.slug}/docs`, { kind: val("paste-kind"), title: val("paste-title") || "Pasted text", text: val("paste-text"), source: "paste" });
      document.getElementById("paste-text").value = ""; document.getElementById("paste-title").value = "";
      toast("Added"); await refresh(); renderCorpus(document.getElementById("corpus"));
    } catch (e) { fail(e); }
  });
  on("#links-add", "click", () => {
    const urls = val("links").split(/\s+/).filter(Boolean);
    if (!urls.length) return;
    startJob("gather", { urls }, document.getElementById("job"), () => { document.getElementById("links").value = ""; renderCorpus(document.getElementById("corpus")); });
  });
  on("#pub-find", "click", async () => {
    const name = val("pub-me"); const box = document.getElementById("pub-box");
    box.innerHTML = `<div class="row muted" style="margin-top:.75rem"><span class="spinner"></span> Searching…</div>`;
    const cands = await api("GET", `/api/search/s2?name=${encodeURIComponent(name)}`).catch(e => ({ error: e.message }));
    const div = document.createElement("div"); div.style.marginTop = "1rem"; box.innerHTML = ""; box.appendChild(div);
    renderCandidates(div, name, cands, null, picked => {
      const body = { name, arxiv: document.getElementById("pub-arxiv").checked };
      if (picked) { body.s2_author_id = picked.author_id; api("PATCH", `/api/profiles/${S.slug}`, { s2_author: picked }).catch(fail); }
      box.innerHTML = "";
      startJob("gather", body, document.getElementById("job"), () => renderCorpus(document.getElementById("corpus")));
    }, { noWiki: true, noCreate: true, goLabel: "Import this author's papers" });
    if (!Array.isArray(cands) || !cands.length) {
      const b = document.createElement("button"); b.className = "btn"; b.textContent = "Import from arXiv only";
      b.addEventListener("click", () => { box.innerHTML = ""; startJob("gather", { name, arxiv: true }, document.getElementById("job"), () => renderCorpus(document.getElementById("corpus"))); });
      div.appendChild(b);
    }
  });
}

async function extractText(file) {
  const ext = (file.name.split(".").pop() || "").toLowerCase();
  if (ext === "pdf") return await pdfText(file);
  if (!TEXT_EXT.includes(ext)) throw new Error("unsupported file type");
  const raw = await file.text();
  if (ext === "html" || ext === "htm") { const d = new DOMParser().parseFromString(raw, "text/html"); d.querySelectorAll("script,style,nav,footer").forEach(n => n.remove()); return d.body.innerText || d.body.textContent || ""; }
  return raw;
}
let pdfjsReady;
function loadPdfJs() {
  pdfjsReady = pdfjsReady || new Promise((res, rej) => {
    const s = document.createElement("script"); s.src = PDFJS + "pdf.min.js";
    s.onload = () => { window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS + "pdf.worker.min.js"; res(window.pdfjsLib); };
    s.onerror = () => { pdfjsReady = null; rej(new Error("PDF reader could not load (needs internet for cdnjs)")); };
    document.head.appendChild(s);
  });
  return pdfjsReady;
}
async function pdfText(file) {
  const lib = await loadPdfJs();
  const doc = await lib.getDocument({ data: await file.arrayBuffer() }).promise;
  const pages = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const c = await (await doc.getPage(i)).getTextContent();
    let line = "", out = [];
    for (const it of c.items) { line += it.str; if (it.hasEOL) { out.push(line); line = ""; } }
    if (line) out.push(line);
    pages.push(out.join("\n"));
  }
  return pages.join("\n\n");
}

// ----- corpus list (shared)
function renderCorpus(el, filter = "all") {
  const docs = S.st.docs.filter(d => filter === "all" || d.kind === filter);
  const editable = S.st.editable;
  const count = k => S.st.docs.filter(d => d.kind === k).length;
  el.innerHTML = `
    <div class="row"><h3 style="margin:0">Corpus <span class="muted">(${S.st.docs.length})</span></h3><span class="spacer"></span>
      <div class="filters">${[["all", "All"], ["research", `Research (${count("research")})`], ["other", `Other (${count("other")})`]].map(([k, l]) =>
        `<button class="btn small ${filter === k ? "on" : ""}" data-f="${k}">${esc(l)}</button>`).join("")}</div></div>
    ${docs.length ? `<div class="table-wrap"><table class="list" style="margin-top:.5rem"><thead><tr><th>Title</th><th>Source</th><th>Date</th><th>Kind</th><th>Size</th><th></th></tr></thead><tbody>
      ${docs.map(d => `<tr class="doc-row"><td class="title"><a href="#" class="t" data-view="${esc(d.file)}" title="${esc(d.title)}">${esc(d.title)}</a></td>
        <td><span class="badge">${esc(d.source)}</span></td><td class="muted small nowrap">${esc(d.date)}</td><td class="small">${esc(d.kind)}</td>
        <td class="muted small">${fmtNum(d.chars)}</td>
        <td>${editable && d.source !== "questionnaire" ? `<button class="btn ghost small danger" data-del="${esc(d.file)}" aria-label="Remove">Remove</button>` : ""}</td></tr>`).join("")}
      </tbody></table></div>` : `<div class="empty">No documents yet.</div>`}`;
  el.querySelectorAll("[data-f]").forEach(b => b.addEventListener("click", () => renderCorpus(el, b.dataset.f)));
  el.querySelectorAll("[data-view]").forEach(a => a.addEventListener("click", async e => {
    e.preventDefault();
    try {
      const d = await api("GET", `/api/profiles/${S.slug}/docs/${a.dataset.view}`);
      document.getElementById("docDialogTitle").textContent = d.front_matter.title || d.file;
      const fm = d.front_matter;
      document.getElementById("docDialogMeta").innerHTML = [fm.url ? `<a href="${esc(fm.url)}" target="_blank" rel="noopener">${esc(fm.url)}</a>` : "", esc(fm.publishedDate || ""), esc(fm.source || ""), `<span class="mono">${esc(d.file)}</span>`].filter(Boolean).join(" · ");
      document.getElementById("docDialogBody").textContent = d.text;
      document.getElementById("docDialog").showModal();
    } catch (err) { fail(err); }
  }));
  el.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", async () => {
    if (!confirm("Remove this document from the profile? Its file in corpus/ is deleted.")) return;
    try { await api("DELETE", `/api/profiles/${S.slug}/docs/${b.dataset.del}`); await refresh(); renderCorpus(el, filter); } catch (e) { fail(e); }
  }));
}

// ----- Questionnaire (personal)
function panelQuestionnaire(panel, nextBtn) {
  const answers = { ...(S.st.meta.questionnaire || {}) };
  const qs = S.st.questions;
  const draftKey = `studio:q:${S.slug}`;
  const draft = load(draftKey) || {};
  panel.innerHTML = head("Questionnaire", "Open questions about how you work. Answer in your own words: a few sentences each is plenty, and every question is optional. There are no right answers. Answers save when you leave a box.") + `
    <div class="card">
      <div class="row small muted"><span id="q-count"></span><span class="spacer"></span><span id="q-saved"></span></div>
      <div class="progress" style="margin:.5rem 0 .25rem"><div id="q-bar"></div></div>
      ${qs.map((q, i) => `<div class="q"><div class="qtext">${i + 1}. ${esc(q.text)} ${q.kind === "other" ? '<span class="badge">outside research</span>' : ""}</div>
        <textarea data-q="${esc(q.id)}" rows="3">${esc(draft[q.id] ?? answers[q.id] ?? "")}</textarea></div>`).join("")}
    </div>${nextBtn}`;
  const count = () => {
    const n = qs.filter(q => (panel.querySelector(`[data-q="${q.id}"]`).value || "").trim()).length;
    document.getElementById("q-count").textContent = `${n} of ${qs.length} answered`;
    document.getElementById("q-bar").style.width = `${(100 * n) / qs.length}%`;
  };
  count();
  const timers = {};
  async function save(t) {
    clearTimeout(timers[t.dataset.q]);
    const q = t.dataset.q, v = t.value.trim();
    if (v === (answers[q] || "")) return;
    try {
      const meta = await api("POST", `/api/profiles/${S.slug}/answers`, { answers: { [q]: v } });
      answers[q] = v; S.st.meta = meta;
      if ((draft[q] ?? "").trim() === v) { delete draft[q]; store(draftKey, Object.keys(draft).length ? draft : undefined); }
      const saved = document.getElementById("q-saved");
      if (saved) saved.textContent = "Saved " + new Date().toLocaleTimeString();
      refresh().catch(() => {});
    } catch (e) { fail(e); }
  }
  panel.querySelectorAll("[data-q]").forEach(t => {
    t.addEventListener("input", () => {
      draft[t.dataset.q] = t.value; store(draftKey, draft); count();
      clearTimeout(timers[t.dataset.q]); timers[t.dataset.q] = setTimeout(() => save(t), 1200);
    });
    t.addEventListener("blur", () => save(t));
  });
}

// ----- Trade-offs (personal; trackp seed pairs)
async function panelTradeoffs(panel, nextBtn, seq) {
  const st = S.st;
  const consentOk = st.consent.length && st.consent.every(c => c.ticked);
  if (!st.choices.pairs) {
    panel.innerHTML = head("Trade-offs", "Forced-choice questions: each shows a research situation and two options, and asks which you would pick. These are the personal track's seed items; your answers are what a user model is fitted on.") + `
      <div class="card stack">
        ${consentOk ? "" : `<div class="notice warn">Tick every consent box under <a href="#/p/${esc(S.slug)}/about">About &amp; consent</a> first.</div>`}
        <p class="muted small">The set of questions is fixed by the personal track's trade-off bank: situations from the benchmark first, then general questions about how you design evals.</p>
        <div class="row end"><button class="btn primary" id="to-gen" ${consentOk ? "" : "disabled"}>Prepare questions</button></div>
      </div>${nextBtn}`;
    on("#to-gen", "click", async () => {
      try { await api("POST", `/api/profiles/${S.slug}/choices/generate`, {}); render(); } catch (e) { fail(e); }
    });
    return;
  }
  const pend = await api("GET", `/api/profiles/${S.slug}/choices/pending`);
  if (stale(seq)) return;
  const items = pend.items;
  let idx = 0, chosen = null, prevGroup = null, showCtx = false, started = st.choices.answered > 0;
  const total = st.choices.pairs;
  let answered = st.choices.answered;

  function draw() {
    if (!started) {
      panel.innerHTML = head("Trade-offs", "") + `
        <div class="card stack">
          <p>You'll see <strong>${fmtNum(items.length)}</strong> questions. Each describes a situation and gives two options.</p>
          <ul>
            <li>It takes about ${minutes(items.length, 25)} minutes, or about ${minutes(items.length, 35)} if you add a one-line reason to each answer.</li>
            <li>You can stop at any time and pick up where you left off.</li>
            <li>There are no right answers. Each question asks what <em>you</em> would do.</li>
            <li>Skip anything you can't decide on; skipped items are not recorded.</li>
          </ul>
          <div class="row end"><button class="btn primary" id="to-start">Begin</button></div>
        </div>${nextBtn}`;
      on("#to-start", "click", () => { started = true; draw(); });
      return;
    }
    if (idx >= items.length) {
      panel.innerHTML = head("Trade-offs", "") + `<div class="card"><div class="notice good">${answered >= total ? "All items answered. Thank you." : "No more items in this session."}
        <strong>${fmtNum(answered)}</strong> of ${fmtNum(total)} answered.</div>
        <p class="muted small" style="margin-top:.75rem">${answered >= total ? "Next, build your profile and fit a user model." : "Skipped questions come back the next time you open this step."}</p></div>${nextBtn}`;
      return;
    }
    const it = items[idx];
    // trackp serves items grouped by situation (`group`), with the situation in `context` and the
    // item's own `question` apart: show a situation once per group, then each question.
    const same = prevGroup !== null && prevGroup === groupKey(it) && it.question;
    panel.innerHTML = head("Trade-offs", "") + `
      <div class="card">
        <div class="row small muted"><span>Question ${fmtNum(answered + 1)} of ${fmtNum(total)}</span><span class="spacer"></span>
          ${idx > 0 && idx === Math.floor(items.length / 2) ? "<span>Halfway. Take a break if you like; progress is saved.</span>" : ""}</div>
        <div class="progress" style="margin:.5rem 0 1rem"><div style="width:${(100 * answered) / total}%"></div></div>
        ${same && !showCtx ? `<div class="notice small">Same situation as the previous question. <button class="btn ghost small" id="to-ctx">Show it again</button></div>`
          : `<div class="context">${esc(it.context)}</div>`}
        ${it.question ? `<p class="qtext" style="margin:.85rem 0 0;font-weight:600">${esc(it.question)}</p>` : ""}
        ${Object.keys(it.evidence || {}).length ? `<pre class="context small" style="margin-top:.5rem">${esc(JSON.stringify(it.evidence, null, 1))}</pre>` : ""}
        <div class="options">${it.options.map((o, i) => `<button class="option ${chosen === i + 1 ? "chosen" : ""}" data-opt="${i + 1}"><span class="n">${i + 1}</span><span>${esc(o)}</span></button>`).join("")}</div>
        <label class="field" style="margin-top:1rem"><span>Why? <span class="muted">(optional, one sentence)</span></span><input id="to-reason" type="text"></label>
        <div class="row end" style="margin-top:1rem">
          <button class="btn" id="to-skip">Skip</button>
          <button class="btn primary" id="to-save" ${chosen ? "" : "disabled"}>Save and continue</button>
        </div>
        <p class="muted small" style="margin-top:.5rem">Keys: 1 / 2 to choose, Enter to save.</p>
      </div>`;
    const reason = document.getElementById("to-reason");
    on("[data-opt]", "click", e => { chosen = +e.currentTarget.dataset.opt; const r = reason.value; draw(); document.getElementById("to-reason").value = r; });
    on("#to-ctx", "click", () => { showCtx = true; const r = reason.value; draw(); document.getElementById("to-reason").value = r; });
    on("#to-skip", "click", () => { prevGroup = groupKey(it); idx++; chosen = null; showCtx = false; draw(); });
    on("#to-save", "click", save);
  }
  async function save() {
    if (!chosen) return;
    const it = items[idx];
    try {
      await api("POST", `/api/profiles/${S.slug}/choices/record`, { id: it.id, choice: chosen, reason: val("to-reason") });
      answered++; prevGroup = groupKey(it); idx++; chosen = null; showCtx = false; draw(); refresh().catch(() => {});
    } catch (e) { fail(e); }
  }
  function keys(e) {
    if (!document.body.contains(panel) || !location.hash.endsWith("/tradeoffs")) return document.removeEventListener("keydown", keys);
    if (e.target.tagName === "INPUT" && e.key !== "Enter") return;
    if (!started || idx >= items.length) return;
    if (/^[1-9]$/.test(e.key) && +e.key <= items[idx].options.length) { const r = val("to-reason"); chosen = +e.key; draw(); document.getElementById("to-reason").value = r; }
    else if (e.key === "Enter" && chosen) { e.preventDefault(); save(); }
  }
  document.addEventListener("keydown", keys);
  draw();
}

function groupKey(it) { return `${it.group ?? ""}\u0000${it.context}`; }
function minutes(n, secondsEach) { return Math.max(1, Math.round((n * secondsEach) / 60)); }

// ----- Identity (public)
function panelIdentity(panel, nextBtn) {
  const m = S.st.meta, a = m.s2_author;
  panel.innerHTML = head("Identity", "Who this profile is about. The Semantic Scholar author decides which papers are imported.") + `
    <div class="card stack">
      <div class="grid2">
        <label class="field"><span>Name</span><input id="id-name" type="text" value="${esc(m.name)}"><small>Also used to match author lists on arXiv and Exa.</small></label>
        <label class="field"><span>Affiliation</span><input id="id-aff" type="text" value="${esc(m.affiliation)}"></label>
      </div>
      <label class="field"><span>Bio</span><textarea id="id-bio" rows="4">${esc(m.bio)}</textarea>
        <small>${m.bio_source ? `From <a href="${esc(m.bio_source)}" target="_blank" rel="noopener">${esc(m.bio_source)}</a>. ` : ""}Shown on the card; not used as taste evidence.</small></label>
      <div class="row end"><button class="btn primary" id="id-save">Save</button></div>
    </div>
    <div class="card">
      <h3>Semantic Scholar author</h3>
      ${a ? `<div class="cand selected"><div style="flex:1"><div class="row"><strong>${esc(a.name)}</strong><span class="muted small">${esc((a.affiliations || []).join("; "))}</span>
        <span class="spacer"></span><a class="small" href="${esc(a.url)}" target="_blank" rel="noopener">Semantic Scholar ↗</a></div>
        <div class="stats"><span><b>${fmtNum(a.papers)}</b> papers</span><span><b>${fmtNum(a.citations)}</b> citations</span><span>h-index <b>${fmtNum(a.h_index)}</b></span></div></div></div>`
        : `<p class="muted">None selected. Papers can still come from arXiv and web sources.</p>`}
      <div class="row" style="margin-top:.75rem"><button class="btn" id="id-change">${a ? "Change author" : "Find author"}</button></div>
      <div id="id-cands"></div>
    </div>${nextBtn}`;
  on("#id-save", "click", async () => {
    try { await api("PATCH", `/api/profiles/${S.slug}`, { name: val("id-name"), affiliation: val("id-aff"), bio: val("id-bio") }); toast("Saved"); render(); } catch (e) { fail(e); }
  });
  on("#id-change", "click", async () => {
    const box = document.getElementById("id-cands");
    box.innerHTML = `<div class="row muted" style="margin-top:.75rem"><span class="spinner"></span> Searching…</div>`;
    const cands = await api("GET", `/api/search/s2?name=${encodeURIComponent(val("id-name"))}`).catch(e => ({ error: e.message }));
    const div = document.createElement("div"); div.style.marginTop = "1rem"; box.innerHTML = ""; box.appendChild(div);
    renderCandidates(div, val("id-name"), cands, null, async picked => {
      try { await api("PATCH", `/api/profiles/${S.slug}`, { s2_author: picked }); toast("Author set"); render(); } catch (e) { fail(e); }
    }, { noWiki: true, noCreate: true, goLabel: "Use this author" });
  });
}

// ----- Sources (public)
function panelSources(panel, nextBtn) {
  const m = S.st.meta, a = m.s2_author, exa = S.config.exa_available;
  panel.innerHTML = head("Gather sources", "Pick where to look. Everything lands in the corpus, which you review next. Sources that fail are reported and the rest still run.") + `
    <div class="card stack">
      <label class="field"><span>Name to match</span><input id="g-name" type="text" value="${esc(m.name)}"></label>
      <label class="check"><input type="checkbox" id="g-s2" ${a ? "checked" : "disabled"}><span><strong>Semantic Scholar papers</strong>
        ${a ? `<span class="muted small">for ${esc(a.name)} (${fmtNum(a.papers)} papers listed)</span>` : `<span class="muted small">select an author under <a href="#/p/${esc(S.slug)}/identity">Identity</a> first</span>`}</span></label>
      <label class="field" style="max-width:200px;margin-left:1.6rem"><span class="small">Max papers</span><input id="g-s2max" type="number" min="1" max="1000" value="150"></label>
      <label class="check"><input type="checkbox" id="g-arxiv" checked><span><strong>arXiv</strong> <span class="muted small">papers whose author list contains the name; duplicates of Semantic Scholar papers are skipped</span></span></label>
      <label class="field" style="max-width:200px;margin-left:1.6rem"><span class="small">Max results</span><input id="g-axmax" type="number" min="1" max="300" value="60"></label>
      <label class="check"><input type="checkbox" id="g-wiki" ${m.bio ? "" : "checked"}><span><strong>Wikipedia bio</strong> <span class="muted small">for the card only</span></span></label>
      <hr class="hr" style="margin:.25rem 0">
      <div class="grid2">
        <label class="field"><span>LessWrong / Alignment Forum username</span><input id="g-lw" type="text" placeholder="e.g. their-user-slug" class="mono"></label>
        <label class="field"><span>Blog RSS feed URL</span><input id="g-rss" type="url" placeholder="https://…/feed.xml"></label>
      </div>
      <label class="field"><span>Other pages they wrote, one per line</span><textarea id="g-urls" rows="3" placeholder="https://"></textarea></label>
      <hr class="hr" style="margin:.25rem 0">
      <label class="check"><input type="checkbox" id="g-exa" ${exa ? "" : "disabled"}><span><strong>Exa harvest</strong> <span class="badge warn">paid</span>
        <span class="muted small">${exa ? "deep web search for everything they published in the date range (taste/scrape.scrape_exa)" : "set EXA_API_KEY in the studio's environment to enable"}</span></span></label>
      ${exa ? `<div class="row" style="margin-left:1.6rem"><label class="field"><span class="small">From</span><input id="g-exa-start" type="date" value="2018-01-01"></label>
        <label class="field"><span class="small">To</span><input id="g-exa-end" type="date" value="${new Date().toISOString().slice(0, 10)}"></label></div>` : ""}
      <div class="row end"><button class="btn primary" id="g-go">Gather</button></div>
    </div>
    <div id="job"></div>
    ${S.st.docs.length ? `<div class="notice" style="margin-top:1rem">${fmtNum(S.st.docs.length)} documents in the corpus so far. Gathering again only adds new ones.</div>` : ""}${nextBtn}`;
  on("#g-go", "click", () => {
    const chk = id => { const el = document.getElementById(id); return !!(el && el.checked); };
    const body = {
      name: val("g-name"), arxiv: chk("g-arxiv"), arxiv_max: +val("g-axmax") || 60, wikipedia: chk("g-wiki"),
      lesswrong_user: val("g-lw"), rss: val("g-rss"), urls: val("g-urls").split(/\s+/).filter(Boolean),
    };
    if (chk("g-s2") && a) { body.s2_author_id = a.author_id; body.s2_max = +val("g-s2max") || 150; }
    if (chk("g-exa")) {
      if (!confirm("The Exa harvest makes paid API calls. Continue?")) return;
      Object.assign(body, { exa: true, exa_start: val("g-exa-start"), exa_end: val("g-exa-end") });
    }
    startJob("gather", body, document.getElementById("job"), () => {
      const n = document.createElement("div"); n.className = "row end"; n.style.marginTop = ".75rem";
      n.innerHTML = `<span class="muted small">${fmtNum(S.st.docs.length)} documents in the corpus.</span><a class="btn primary" href="#/p/${esc(S.slug)}/corpus">Review corpus →</a>`;
      document.getElementById("job").appendChild(n);
    });
  });
}

// ----- Corpus (public / external)
function panelCorpus(panel, nextBtn) {
  panel.innerHTML = head("Review corpus", S.st.editable
    ? "Check that these are really this person's work and remove anything that isn't (a same-named author, a page about them rather than by them). Building uses the newest documents first."
    : "Documents in this researcher's corpus (read-only: not made in the studio).") + `<div class="card" id="corpus"></div>${nextBtn}`;
  renderCorpus(document.getElementById("corpus"));
}

// ----- Build & review
function panelBuild(panel, nextBtn) {
  const st = S.st, m = st.meta, prof = st.profile, editable = st.editable;
  const n = st.docs.length;
  const defBackend = S.config.anthropic_key_set ? "anthropic" : "offline";
  panel.innerHTML = head(editable ? "Build & review" : "Profile", editable
    ? "Turn the corpus into a profile: principles plus weights over the seven features the loop scores ideas on. Review it, and correct anything that looks wrong."
    : "This profile was made outside the studio, so it is shown read-only.") + `
    ${editable ? `<div class="card stack">
      <h3>Build</h3>
      <div class="grid2">
        <label class="field"><span>Model backend</span><select id="b-backend">${S.config.backends.map(b => `<option ${b === defBackend ? "selected" : ""}>${b}</option>`).join("")}</select></label>
        <label class="field"><span>Model</span><input id="b-model" type="text" class="mono" value="claude-sonnet-5-5"></label>
        <label class="field"><span>Documents to read</span><input id="b-max" type="number" min="1" value="${Math.min(40, Math.max(1, n))}"><small>${fmtNum(n)} available; questionnaire answers and your own uploads first, then newest.</small></label>
      </div>
      <div class="notice small" id="b-note"></div>
      <div class="row end"><button class="btn primary" id="b-go" ${n ? "" : "disabled"}>${prof ? "Rebuild profile" : "Build profile"}</button></div>
      ${prof && m.build && m.build.edited ? `<div class="notice warn small">Rebuilding replaces your hand edits.</div>` : ""}
    </div><div id="job"></div>` : ""}
    <div id="profile-view"></div>
    ${editable && m.mode === "personal" ? `<div id="usermodel"></div>` : ""}${nextBtn}`;
  if (editable) {
    const note = () => {
      const b = val("b-backend"), k = +val("b-max") || 0;
      document.getElementById("b-note").innerHTML = b === "offline"
        ? "<strong>Offline</strong> uses a keyword lexicon and makes no model calls. Good for trying the flow; the result is not a real taste profile."
        : `<strong>${esc(b)}</strong> makes about ${fmtNum(k + 2)} model calls (one per document, one to merge principles, one for the summary). ${b === "anthropic" ? (S.config.anthropic_key_set ? "Uses ANTHROPIC_API_KEY (paid)." : "<span style='color:var(--bad)'>ANTHROPIC_API_KEY is not set in the studio's environment.</span>") : "Uses your Claude Code login."}`;
    };
    note();
    document.getElementById("b-backend").addEventListener("change", note);
    document.getElementById("b-max").addEventListener("input", note);
    on("#b-go", "click", () => {
      if (val("b-backend") !== "offline" && !confirm(`Build with ${val("b-backend")}? This makes about ${(+val("b-max") || 0) + 2} model calls.`)) return;
      startJob("build", { backend: val("b-backend"), model: val("b-model"), max_docs: +val("b-max") || 40 }, document.getElementById("job"), () => render());
    });
  }
  renderProfile(document.getElementById("profile-view"));
  if (editable && m.mode === "personal") renderUserModel(document.getElementById("usermodel"));
}

const FEATURE_HELP = {
  realism: "prefers setups that look like real deployment", grounding: "wants empirical evidence and concrete data",
  simplicity: "favours simple baselines, minimal changes, ablations", novelty: "drawn to new, unexplored directions",
  cost: "negative = prefers cheap, efficient work", risk: "willing to take bold, high-variance bets",
  validity_care: "guards against confounds; checks the test still measures what it should",
};

function renderProfile(el) {
  const st = S.st, m = st.meta, prof = st.profile, card = m.summary, editable = st.editable;
  if (!prof) { el.innerHTML = `<div class="card empty">No profile built yet.</div>`; return; }
  const w = { ...prof.weights };
  const principles = [...(prof.principles || [])];
  el.innerHTML = `
    <div class="card" style="margin-top:1rem">
      <div class="row"><h2 style="margin:0">${esc(m.name)}</h2>${m.affiliation ? `<span class="muted">${esc(m.affiliation)}</span>` : ""}
        <span class="spacer"></span>${m.build && m.build.edited ? '<span class="badge warn">edited by hand</span>' : ""}</div>
      ${m.bio ? `<p class="muted small" style="margin-top:.5rem">${esc(m.bio)}</p>` : ""}
      ${card ? `
        ${card.summary ? `<p class="profile-summary" style="margin-top:.75rem">${esc(card.summary)}</p>` : ""}
        ${card.interests && card.interests.length ? `<h4>Interests</h4><div>${card.interests.map(i => `<span class="chip">${esc(i)}</span>`).join("")}</div>` : ""}
        <div class="grid2" style="margin-top:.5rem">
          ${card.methods && card.methods.length ? `<div><h4>How they work</h4><ul>${card.methods.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>` : ""}
          ${card.open_questions && card.open_questions.length ? `<div><h4>Open questions</h4><ul>${card.open_questions.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>` : ""}
        </div>` : ""}
      ${m.build ? `<dl class="kv" style="margin-top:1rem"><dt>Built</dt><dd>${esc((m.build.at || "").replace("T", " ").slice(0, 16))} UTC with <span class="mono">${esc(String(m.build.llm).replace(/:$/, ""))}</span></dd>
        <dt>Documents</dt><dd>${fmtNum(m.build.docs_used)} of ${fmtNum(m.build.docs_available)}</dd>
        ${m.build.principles_extracted > (prof.principles || []).length ? `<dt>Principles</dt><dd>merged from ${fmtNum(m.build.principles_extracted)} extracted (raw list kept in studio.json)</dd>` : ""}
        <dt>Model calls</dt><dd>${fmtNum(m.build.calls)}${m.build.cost_usd ? ` · $${m.build.cost_usd}` : ""}</dd></dl>` : ""}
    </div>
    <div class="grid2" style="margin-top:1rem">
      <div class="card">
        <h3>Principles</h3>
        <p class="muted small">Short rules the proposer is told to follow for this researcher.</p>
        <div class="principles" id="pr-list"></div>
        ${editable ? `<button class="btn small" id="pr-add" style="margin-top:.5rem">+ Add principle</button>` : ""}
      </div>
      <div class="card">
        <h3>Feature weights</h3>
        <p class="muted small">−1 to 1. The loop scores each candidate idea's features with these (D1).</p>
        <div class="weights" id="w-list"></div>
      </div>
    </div>
    ${editable ? `<div class="row end" style="margin-top:1rem"><span class="muted small" id="edit-hint"></span><button class="btn primary" id="p-save" disabled>Save edits</button></div>` : ""}`;
  const dirty = () => { const b = document.getElementById("p-save"); if (b) { b.disabled = false; document.getElementById("edit-hint").textContent = "Unsaved changes. Saved profiles are marked as edited by hand."; } };
  function drawPrinciples() {
    const list = document.getElementById("pr-list");
    list.innerHTML = principles.length ? principles.map((p, i) => editable
      ? `<div class="principle"><input type="text" data-pr="${i}" value="${esc(p)}"><button class="btn ghost small" data-prx="${i}" aria-label="Remove">✕</button></div>`
      : `<div class="principle">• ${esc(p)}</div>`).join("") : `<span class="muted small">none</span>`;
    list.querySelectorAll("[data-pr]").forEach(i => i.addEventListener("input", () => { principles[+i.dataset.pr] = i.value; dirty(); }));
    list.querySelectorAll("[data-prx]").forEach(b => b.addEventListener("click", () => { principles.splice(+b.dataset.prx, 1); drawPrinciples(); dirty(); }));
  }
  function drawWeights() {
    const list = document.getElementById("w-list");
    list.innerHTML = st.features.map(f => {
      const v = Number(w[f] || 0), pct = Math.min(50, Math.abs(v) * 50);
      return `<div class="weight" title="${esc(FEATURE_HELP[f] || "")}"><span>${esc(f.replace("_", " "))}</span>
        ${editable ? `<input type="range" min="-1" max="1" step="0.05" value="${v}" data-w="${esc(f)}" aria-label="${esc(f)} weight">`
          : `<div class="bar"><div class="fill ${v >= 0 ? "pos" : "neg"}" style="${v >= 0 ? `left:50%;width:${pct}%` : `left:${50 - pct}%;width:${pct}%`}"></div></div>`}
        <span class="val" data-wv="${esc(f)}">${v >= 0 ? "+" : ""}${v.toFixed(2)}</span></div>`;
    }).join("") + `<p class="muted small" style="margin:.25rem 0 0">Hover a feature for what it means.</p>`;
    list.querySelectorAll("[data-w]").forEach(r => r.addEventListener("input", () => {
      w[r.dataset.w] = +r.value; const v = +r.value;
      list.querySelector(`[data-wv="${r.dataset.w}"]`).textContent = `${v >= 0 ? "+" : ""}${v.toFixed(2)}`; dirty();
    }));
  }
  drawPrinciples(); drawWeights();
  if (editable) {
    on("#pr-add", "click", () => { principles.push(""); drawPrinciples(); dirty(); const ins = el.querySelectorAll("[data-pr]"); ins[ins.length - 1].focus(); }, el);
    on("#p-save", "click", async () => {
      try { await api("PUT", `/api/profiles/${S.slug}/profile`, { principles, weights: w }); toast("Profile saved"); await refresh(); renderProfile(el); } catch (e) { fail(e); }
    }, el);
  }
}

function renderUserModel(el) {
  const st = S.st, n = st.choices.answered;
  el.innerHTML = `<div class="card stack" style="margin-top:1rem">
    <div class="row"><h3 style="margin:0">User model <span class="muted small">(optional)</span></h3><span class="spacer"></span>
      ${st.has_usermodel ? '<span class="badge ok">usermodel.json present</span>' : ""}</div>
    <p class="muted small">Fits one of WS A's methods on your trade-off answers and writes <code>usermodel.json</code>. When present, the loop uses it at every decision point (D1–D6) instead of the feature weights above, which only inform D1. Held-out answers are never used for fitting.</p>
    ${n < 10 ? `<div class="notice warn small">You have ${fmtNum(n)} answered trade-off item${n === 1 ? "" : "s"}. Answer the questions under <a href="#/p/${esc(S.slug)}/tradeoffs">Trade-offs</a> first.</div>` : ""}
    <div class="grid2">
      <label class="field"><span>Method</span><select id="um-method">${S.config.methods.map(x => `<option ${x === "m1" ? "selected" : ""}>${x}</option>`).join("")}</select><small>Use the method WS A selected.</small></label>
      <label class="field"><span>Backend</span><select id="um-backend">${S.config.backends.map(b => `<option>${b}</option>`).join("")}</select><small>Must match the backend the loop's judge predicts with.</small></label>
      <label class="field"><span>Model</span><input id="um-model" type="text" class="mono" value="claude-haiku-5-5"></label>
      <label class="field"><span>Max model calls</span><input id="um-max" type="number" min="1" value="500"></label>
    </div>
    <div class="row end"><button class="btn" id="um-go" ${n ? "" : "disabled"}>Fit user model</button></div>
    <div id="um-job"></div></div>`;
  on("#um-go", "click", () => {
    if (val("um-backend") !== "offline" && !confirm(`Fit ${val("um-method")} with ${val("um-backend")}? This makes up to ${val("um-max")} model calls.`)) return;
    startJob("fit", { method: val("um-method"), backend: val("um-backend"), model: val("um-model"), max_calls: +val("um-max") || 500 },
      document.getElementById("um-job"), async () => { await refresh(); renderUserModel(el); });
  }, el);
}

// ----- Use in the loop
function panelUse(panel) {
  const st = S.st, slug = S.slug;
  const loads = st.has_usermodel ? "usermodel.json: the fitted user model, at every decision point (D1–D6)"
    : st.profile ? "profile.json feature weights and principles (D1 only; text-only decisions fall back to no taste)" : null;
  const cmd = (label, c, note) => `<div style="margin-top:1rem"><div class="small"><strong>${esc(label)}</strong>${note ? ` <span class="muted">${note}</span>` : ""}</div>
    <div class="cmd"><pre>${esc(c)}</pre><button class="btn small" data-copy="${esc(c)}">Copy</button></div></div>`;
  panel.innerHTML = head("Use in the loop", "The loop reads this profile from <code>data/researchers/" + esc(slug) + "/</code> when you pass <code>--researcher " + esc(slug) + "</code>.") + `
    <div class="card">
      ${loads ? `<div class="notice good">The loop will load <strong>${esc(loads)}</strong>.</div>` : `<div class="notice warn">No profile yet. Build one under <a href="#/p/${esc(slug)}/build">Build &amp; review</a> first.</div>`}
      ${cmd("Dry run, no model calls", `python3 -m autoresearch --llm offline research --researcher ${slug}`, "checks the profile loads and the loop runs")}
      ${cmd("Real run with this researcher's taste (R1)", `python3 -m autoresearch --llm anthropic research --researcher ${slug}`, "paid; follow the team's live-run rules")}
      ${cmd("Prompt baseline: raw history in the proposer prompt (R1-prompt)", `python3 -m autoresearch --llm anthropic research --researcher ${slug} --taste-mode prompt`, "paid")}
      ${st.has_usermodel ? cmd("Keep a copy of the user model in shared memory", `python3 -m autoresearch.taste.usermodel_store push --researcher ${slug}`, "uses past.dev when PAST_API_KEY is set") : ""}
    </div>
    <div class="card">
      <h3>Files</h3>
      <dl class="kv">
        <dt class="mono">corpus/</dt><dd>${fmtNum(st.docs.length)} documents</dd>
        <dt class="mono">profile.json</dt><dd>${st.profile ? "present" : "not built"}</dd>
        ${st.meta.mode === "personal" ? `<dt class="mono">seed_choices.jsonl</dt><dd>${fmtNum(st.choices.answered)} trade-off answers</dd>
        <dt class="mono">usermodel.json</dt><dd>${st.has_usermodel ? "present" : "not fitted"}</dd>
        <dt class="mono">CONSENT.md</dt><dd>${st.consent.every(c => c.ticked) ? "complete" : "incomplete"}</dd>` : ""}
        ${st.editable ? `<dt class="mono">studio.json</dt><dd>studio metadata (name, bio, questionnaire, summary)</dd>` : ""}
      </dl>
    </div>`;
  on("[data-copy]", "click", async e => {
    try { await navigator.clipboard.writeText(e.currentTarget.dataset.copy); toast("Copied"); } catch (_) { toast("Copy failed; select the text instead", true); }
  });
}

// ---------- jobs ----------
async function startJob(kind, body, el, onDone) {
  let job;
  try { job = await api("POST", `/api/profiles/${S.slug}/${kind}`, body); } catch (e) { return fail(e); }
  const label = { gather: "Gathering sources", build: "Building profile", fit: "Fitting user model" }[kind] || kind;
  const slug = S.slug;
  const draw = j => {
    if (!document.body.contains(el)) return false;
    el.innerHTML = `<div class="card job"><div class="row">${j.status === "running" ? '<span class="spinner"></span>' : j.status === "done" ? '<span class="badge ok">done</span>' : '<span class="badge warn">error</span>'}
      <strong>${esc(label)}</strong><span class="muted small">${j.status === "running" ? "you can keep working; this page updates when it finishes" : ""}</span></div>
      ${j.error ? `<div class="notice bad small" style="margin-top:.5rem">${esc(j.error)}</div>` : ""}
      <div class="job-log">${esc(j.log.join("\n") || "starting…")}</div></div>`;
    const lg = el.querySelector(".job-log"); lg.scrollTop = lg.scrollHeight;
    return true;
  };
  draw(job);
  const tick = async () => {
    try { job = await api("GET", `/api/jobs/${job.id}`); } catch (e) { return fail(e); }
    const visible = draw(job);
    if (job.status === "running") return setTimeout(tick, 900);
    if (job.status === "done") toast(`${label}: done`);
    if (S.slug === slug) { await refresh(slug); if (visible && job.status === "done" && onDone) onDone(job); }
  };
  setTimeout(tick, 700);
}
