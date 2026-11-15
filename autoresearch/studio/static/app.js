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
  document.getElementById("brandMark").innerHTML = doodle("feather", { size: 34, color: "clay", tilt: -12 });
  try { S.config = await api("GET", "/api/config"); } catch (e) { app.innerHTML = `<div class="notice bad">Could not reach the studio server: ${esc(e.message)}</div>`; return; }
  render();
})();

// Views await the server before drawing; a render started later wins, so fast navigation never
// leaves an older view on screen.
let renderSeq = 0;
const stale = seq => seq !== renderSeq;

// One keyboard handler at a time, owned by the current view (typeform-style shortcuts).
// It ignores keys typed into fields unless the view asks for them.
let keyHandler = null;
function setKeys(fn) { keyHandler = fn; }
document.addEventListener("keydown", e => {
  if (!keyHandler || e.defaultPrevented || document.querySelector("dialog[open]")) return;
  if (keyHandler(e) === true) e.preventDefault();
});
function typing(e) { return /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable; }

async function render() {
  const seq = ++renderSeq;
  setKeys(null);
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
  const tilt = i => (((i * 37) % 9) - 4) * 0.6;   // small, stable, never-aligned rotations
  const cards = profiles.map((p, i) => `
    <a class="index-card rise" style="--i:${i + 4};--r:${tilt(i)}deg" href="#/p/${esc(p.slug)}">
      ${i % 3 === 0 ? '<span class="tape" aria-hidden="true"></span>' : ""}
      <span class="name">${esc(p.name)}</span>
    </a>`).join("");
  app.innerHTML = `
    <section class="hero">
      <div class="hero-doodles" aria-hidden="true">
        ${[["lightbulb", "ochre", 78, 4, 6, 70], ["flask", "sage", 74, 26, -8, 64], ["book", "sky", 86, 54, 5, 66],
           ["telescope", "clay", 64, 70, -4, 70], ["sparkle", "ochre", 93, 20, 12, 40], ["coffee", "rose", 70, 46, 7, 52],
           ["pencil", "clay", 96, 74, -14, 50]].map(([n, c, x, y, t, sz], i) =>
          `<span class="par" style="left:${x}%;top:${y}%;--d:${(0.4 + (i % 3) * 0.35).toFixed(2)}"><span class="bob pop" style="--i:${i + 2}">
            <button type="button" class="hero-doodle wobble" aria-label="${n} doodle">${doodle(n, { color: c, tilt: t, size: sz })}</button></span></span>`).join("")}
      </div>
      <h1 class="rise" style="--i:1">Whose research <span class="scribble">taste<svg viewBox="0 0 200 20" preserveAspectRatio="none"><path d="M4 12 C40 4 80 18 120 9 C150 3 175 12 196 7"/></svg></span> should the loop follow?</h1>
      <p class="lede rise" style="--i:2">A profile captures how a researcher decides: what they value, what they avoid, how they trade
      realism against rigour, cost against novelty. The research loop reads it to choose which experiments to propose and run.</p>
    </section>
    <section class="mode-cards">
      <a class="choice rise" style="--i:3;--r:-1.1deg" href="#/new/personal" data-key="a">
        <div class="choice-head">${doodle("person", { size: 64, color: "clay", tilt: -7 })}${doodle("pencil", { size: 40, color: "ochre", tilt: 14, cls: "wobble" })}</div>
        <h2>Your own profile</h2>
        <p>From your papers and writing, plus a few questions about how you work.</p>
        <span class="go">${doodle("arrow", { size: 34, color: "clay", tilt: -4 })}</span>
      </a>
      <a class="choice rise" style="--i:4;--r:1.3deg" href="#/new/public" data-key="b">
        <div class="choice-head">${doodle("telescope", { size: 64, color: "sage", tilt: 6 })}${doodle("cap", { size: 42, color: "sky", tilt: -10 })}</div>
        <h2>A known researcher</h2>
        <p>From someone's public record, gathered for you.</p>
        <span class="go">${doodle("arrow", { size: 34, color: "sage", tilt: 5 })}</span>
      </a>
    </section>
    <section>
      <div class="section-title rise" style="--i:4">${doodle("folder", { size: 40, color: "ochre", tilt: -6 })}<h2>Profiles</h2>
</div>
      ${profiles.length ? `<div class="cards-grid">${cards}</div>`
        : `<div class="empty">${doodle("seedling", { size: 64, color: "sage" })}<span class="hand">Nothing here yet. Start with A or B.</span></div>`}
    </section>`;
  // doodles drift a little with the cursor (deeper ones more), and burst when clicked
  const heroEl = app.querySelector(".hero");
  heroEl.addEventListener("pointermove", e => {
    const r = heroEl.getBoundingClientRect();
    heroEl.style.setProperty("--mx", ((e.clientX - r.left) / r.width - 0.5).toFixed(3));
    heroEl.style.setProperty("--my", ((e.clientY - r.top) / r.height - 0.5).toFixed(3));
  });
  heroEl.addEventListener("pointerleave", () => { heroEl.style.setProperty("--mx", 0); heroEl.style.setProperty("--my", 0); });
  app.querySelectorAll(".hero-doodle").forEach(b => b.addEventListener("click", () => burstAt(b)));
  setKeys(e => {
    const card = app.querySelector(`.choice[data-key="${e.key.toLowerCase()}"]`);
    if (card && !e.metaKey && !e.ctrlKey) { card.classList.add("pressed"); go(card.getAttribute("href")); return true; }
  });
}

// ---------- typeform engine ----------
/* flow(container, steps, opts) shows one step at a time.
   A step: { icon, color, q(state) -> html, help?(state) -> html, body?(state) -> html,
             bind?(screen, state, ctl), submit?(state, screen) -> Promise (throw to stay),
             skip?(state) -> bool, ok?: label, choices?: { multi, items(state) -> [{html, value}], key } }
   ctl: { next(), back(), state }. Enter continues (Shift+Enter is a newline), letter keys pick
   choices, ↑/↓ move between steps. opts.onDone(state) runs after the last step. */
const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
function flow(container, steps, opts = {}) {
  const state = opts.state || {};
  let i = (opts.start || 0) - 1, busy = false;
  container.innerHTML = `<div class="tf"><div class="tf-progress"><div></div></div><div class="tf-stage"></div>
    <div class="tf-nav"><button class="btn small" data-nav="back" aria-label="Previous question">↑</button>
    <button class="btn small" data-nav="next" aria-label="Next question">↓</button></div></div>`;
  const stage = container.querySelector(".tf-stage"), bar = container.querySelector(".tf-progress > div");
  container.querySelector('[data-nav="back"]').addEventListener("click", () => ctl.back());
  container.querySelector('[data-nav="next"]').addEventListener("click", () => ctl.next());
  const visible = () => steps.map((st, k) => k).filter(k => !(steps[k].skip && steps[k].skip(state)));

  function choicesHtml(st) {
    const c = st.choices, items = c.items(state), sel = state[c.key];
    const isOn = v => (c.multi ? (sel || []).includes(v) : sel === v);
    return `<div class="choices">${items.map((it, k) => `
      <button type="button" class="option ${isOn(it.value) ? "chosen" : ""}" data-choice="${k}">
        <span class="n">${LETTERS[k]}</span><span style="flex:1">${it.html}</span>
        <span class="tick">${doodle("check", { size: 22, color: "sage", tilt: -6 })}</span></button>`).join("")}</div>`;
  }
  function draw(dir) {
    const st = steps[i], vis = visible(), pos = vis.indexOf(i);
    bar.style.width = `${(100 * pos) / vis.length}%`;
    const old = stage.querySelector(".tf-screen");
    if (old) { old.classList.add(dir < 0 ? "leave-back" : "leave"); setTimeout(() => old.remove(), 330); }
    const screen = document.createElement("div");
    screen.className = `tf-screen ${dir < 0 ? "enter-back" : "enter"}`;
    screen.innerHTML = `
      <div class="tf-deco" aria-hidden="true"><span class="bob">${doodle(st.icon || "sparkle", { size: 132, color: st.color, tilt: pos % 2 ? 8 : -7 })}</span>
        <span class="bob">${doodle(["sparkle", "star", "heart", "lightbulb"][pos % 4], { size: 48, tilt: pos % 2 ? -12 : 10, seed: pos })}</span></div>
      <div class="tf-num">${pos + 1} → ${doodle(st.icon || "sparkle", { size: 30, color: st.color, tilt: (pos % 2 ? 7 : -6) })}</div>
      <h2 class="tf-q">${st.q(state)}</h2>
      ${st.help ? `<p class="tf-help">${st.help(state)}</p>` : ""}
      <div class="tf-body">${st.body ? st.body(state) : ""}${st.choices ? choicesHtml(st) : ""}</div>
      <div class="tf-actions"><button type="button" class="btn primary" data-ok>${st.ok || "OK"} ${doodle("check", { size: 18, color: "clay", tilt: 0 })}</button>
        ${st.skipLabel ? `<button type="button" class="btn ghost" data-skip>${st.skipLabel}</button>` : ""}
        <span class="tf-error" role="alert"></span></div>`;
    stage.appendChild(screen);
    screen.querySelector("[data-ok]").addEventListener("click", () => ctl.next());
    const sk = screen.querySelector("[data-skip]"); if (sk) sk.addEventListener("click", () => ctl.advance());
    if (st.choices) screen.querySelectorAll("[data-choice]").forEach(b => b.addEventListener("click", () => pick(+b.dataset.choice)));
    screen.querySelectorAll("textarea.tf-input").forEach(t => {
      const fit = () => { t.style.height = "auto"; t.style.height = Math.max(120, t.scrollHeight + 4) + "px"; };
      t.addEventListener("input", fit); setTimeout(fit, 0);
    });
    if (st.bind) st.bind(screen, state, ctl);
    const first = !st.noAutofocus && screen.querySelector("input:not([type=checkbox]):not([type=radio]), textarea");
    if (first) setTimeout(() => { first.focus({ preventScroll: true }); if (first.setSelectionRange && first.value) first.setSelectionRange(first.value.length, first.value.length); }, 380);
    container.querySelector('[data-nav="back"]').disabled = pos === 0;
  }
  function pick(k) {
    const st = steps[i], c = st.choices, items = c.items(state);
    if (!items[k]) return;
    const v = items[k].value, screen = stage.querySelector(".tf-screen:not(.leave):not(.leave-back)");
    if (c.multi) {
      const cur = new Set(state[c.key] || []);
      cur.has(v) ? cur.delete(v) : cur.add(v);
      state[c.key] = items.map(it => it.value).filter(x => cur.has(x));
    } else state[c.key] = v;
    screen.querySelectorAll("[data-choice]").forEach((b, j) => {
      const on = c.multi ? state[c.key].includes(items[j].value) : j === k;
      b.classList.toggle("chosen", on);
      if (j === k) { b.classList.remove("flash"); void b.offsetWidth; b.classList.add("flash"); }
    });
    if (!c.multi && c.autoNext !== false) setTimeout(() => ctl.next(), 420);
  }
  const ctl = {
    state,
    async next() {
      if (busy) return;
      const st = steps[i], screen = stage.querySelector(".tf-screen:not(.leave):not(.leave-back)");
      const ok = screen && screen.querySelector("[data-ok]"), err = screen && screen.querySelector(".tf-error");
      if (st && st.submit) {
        busy = true; if (ok) { ok.disabled = true; ok.dataset.label = ok.innerHTML; ok.innerHTML = `<span class="spinner"></span> one moment`; }
        try { await st.submit(state, screen); }
        catch (e) {
          busy = false;
          if (ok) { ok.disabled = false; ok.innerHTML = ok.dataset.label; }
          if (err) { err.textContent = e.message; err.style.color = "var(--bad)"; }
          screen.classList.remove("shake"); void screen.offsetWidth; screen.classList.add("shake");
          return;
        }
        busy = false;
      }
      ctl.advance();
    },
    advance() {
      if (busy) return;
      const vis = visible(), nxt = vis.find(k => k > i);
      if (nxt === undefined) { bar.style.width = "100%"; if (opts.onDone) opts.onDone(state, container); return; }
      i = nxt; draw(1);
    },
    back() { const prev = visible().filter(k => k < i).pop(); if (prev !== undefined && !busy) { i = prev; draw(-1); } },
  };
  setKeys(e => {
    const st = steps[i];
    if (!st) return;
    if (e.key === "Enter" && !e.shiftKey && !(e.target.tagName === "TEXTAREA" && e.altKey)) {
      if (e.target.tagName === "BUTTON" && e.target.closest(".tf-screen") && !e.target.hasAttribute("data-ok")) return;
      ctl.next(); return true;
    }
    if (typing(e)) return;
    if (st.choices && e.key.length === 1 && /[a-z]/i.test(e.key) && !e.metaKey && !e.ctrlKey) {
      const k = LETTERS.indexOf(e.key.toUpperCase()); if (k >= 0) { pick(k); return true; }
    }
    if (e.key === "ArrowDown") { ctl.next(); return true; }
    if (e.key === "ArrowUp") { ctl.back(); return true; }
  });
  i = Math.min(i, steps.length - 2);
  ctl.advance();
  return ctl;
}

/* little celebration: tiny doodles flying out from a point */
function burst(x, y, n = 12) {
  const box = document.createElement("div"); box.className = "burst"; box.style.left = x + "px"; box.style.top = y + "px";
  const names = ["sparkle", "star", "heart", "check"], colors = ["clay", "ochre", "sage", "sky", "rose"];
  box.innerHTML = Array.from({ length: n }, (_, k) => {
    const a = (k / n) * Math.PI * 2 + Math.random() * .4, r = 70 + Math.random() * 90;
    return `<span style="--dx:${Math.cos(a) * r}px;--dy:${Math.sin(a) * r - 30}px;--rot:${(Math.random() * 120 - 60) | 0}deg;left:-12px;top:-12px;position:absolute">
      ${doodle(names[k % 4], { size: 22 + (k % 3) * 6, color: colors[k % 5], seed: k })}</span>`;
  }).join("");
  box.querySelectorAll(":scope > span").forEach(s => { s.style.animation = "burst 1.1s cubic-bezier(.2,.8,.2,1) forwards"; s.style.transform = ""; });
  document.body.appendChild(box); setTimeout(() => box.remove(), 1300);
}
function burstAt(el) { const r = el.getBoundingClientRect(); burst(r.left + r.width / 2, r.top + r.height / 2); }

function doneScreen(container, { title, text, actions, icon = "sparkle" }) {
  container.querySelector(".tf-stage").innerHTML = `
    <div class="tf-screen enter" style="text-align:center">
      <div>${doodle(icon, { size: 96, color: "ochre", tilt: -8, cls: "pop" })}</div>
      <h2 class="tf-q" style="margin-top:1rem"><span class="hand">${title}</span></h2>
      <p class="tf-help">${text}</p>
      <div class="row" style="justify-content:center">${actions}</div>
    </div>`;
  container.querySelector(".tf-nav").remove();
  const d = container.querySelector(".tf-screen .doodle"); if (d) setTimeout(() => burstAt(d), 250);
}

async function slugFree(slug) {
  const list = await api("GET", "/api/profiles");
  if (list.some(p => p.slug === slug)) throw new Error(`“${slug}” is taken. Try another id.`);
}

// ---------- new personal ----------
function viewNewPersonal() {
  const consentItems = [
    ["store", "My choices, decision labels and written reasons are stored in this repo."],
    ["steer", "A user model fitted on them steers the research loop and is reported in results."],
    ["memory", "The fitted model is kept in shared memory (past.dev when it's configured)."],
  ];
  flow(app, [
    { icon: "person", color: "clay", q: () => `Hello! What's your <span class="hand">name</span>?`,
      help: () => "This goes on your profile card.",
      body: st => `<input class="tf-input" id="f-name" type="text" autocomplete="name" placeholder="Type your name here…" value="${esc(st.name || "")}">`,
      bind: (sc, st) => sc.querySelector("#f-name").addEventListener("input", e => { st.name = e.target.value; }),
      submit: async st => { if (!(st.name || "").trim()) throw new Error("A name, please."); st.name = st.name.trim(); if (!st.slugTouched) st.slug = slugify(st.name); } },
    { icon: "key", color: "ochre", q: st => `Nice to meet you, <span class="hand">${esc(st.name.split(" ")[0])}</span>. What id should the profile have?`,
      help: () => `This is what you'll pass to the loop as <code>--researcher &lt;id&gt;</code>. Lowercase letters, digits and _.`,
      body: st => `<input class="tf-input mono" id="f-slug" type="text" value="${esc(st.slug || "")}" spellcheck="false">`,
      bind: (sc, st) => sc.querySelector("#f-slug").addEventListener("input", e => { st.slug = e.target.value; st.slugTouched = true; }),
      submit: async st => { st.slug = slugify(st.slug || ""); if (!st.slug) throw new Error("The id can't be empty."); await slugFree(st.slug); } },
    { icon: "cap", color: "sky", q: () => `Where do you <span class="hand">work</span>?`, help: () => "Optional. Press Enter to skip.",
      body: st => `<input class="tf-input" id="f-aff" type="text" placeholder="Lab, company, university…" value="${esc(st.aff || "")}">`,
      bind: (sc, st) => sc.querySelector("#f-aff").addEventListener("input", e => { st.aff = e.target.value; }) },
    { icon: "heart", color: "rose", q: () => `Before we start: how may your answers be <span class="hand">used</span>?`,
      help: () => "Pick any with the letter keys. The trade-off questions stay locked until all three are ticked; you can change this later.",
      choices: { key: "consent", multi: true, items: () => consentItems.map(([v, t]) => ({ value: v, html: esc(t) })) },
      ok: "Create my profile",
      submit: async st => {
        const meta = await api("POST", "/api/profiles", { name: st.name, mode: "personal", slug: st.slug });
        st.slug = meta.slug;
        if ((st.aff || "").trim()) await api("PATCH", `/api/profiles/${meta.slug}`, { affiliation: st.aff.trim() });
        await api("POST", `/api/profiles/${meta.slug}/consent`, { ticked: consentItems.map(([v]) => (st.consent || []).includes(v)) });
      } },
  ], {
    onDone: (st, c) => doneScreen(c, {
      title: "You're all set up!", icon: "seedling",
      text: "Next, add some of your writing, or answer a few questions about how you work. Either order is fine.",
      actions: `<a class="btn primary" href="#/p/${esc(st.slug)}/materials">Add materials ${doodle("stack", { size: 20, color: "ochre" })}</a>
                <a class="btn" href="#/p/${esc(st.slug)}/questionnaire">Questions first ${doodle("chat", { size: 20, color: "sky" })}</a>`,
    }),
  });
}
function slugify(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, ""); }

// ---------- new public ----------
function candidateHtml(c) {
  return `<span class="cname">${esc(c.name)}</span>
    ${c.affiliations.length ? `<span class="muted small" style="margin-left:.4rem">${esc(c.affiliations.join("; "))}</span>` : ""}
    <span class="stats"><span><b>${fmtNum(c.papers)}</b> papers</span><span><b>${fmtNum(c.citations)}</b> citations</span><span>h-index <b>${fmtNum(c.h_index)}</b></span>
    <a href="${esc(c.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Semantic Scholar ↗</a>
    <span class="linklike" data-titles="${esc(c.author_id)}" role="button" tabindex="0" onclick="event.stopPropagation()">top papers ▾</span></span>
    <span class="titles" data-titles-for="${esc(c.author_id)}"></span>`;
}
function bindTopPapers(root) {
  root.querySelectorAll("[data-titles]").forEach(b => {
    const load = async e => {
      e.stopPropagation(); e.preventDefault();
      const holder = root.querySelector(`[data-titles-for="${b.dataset.titles}"]`);
      if (holder.dataset.loaded) { holder.hidden = !holder.hidden; return; }
      holder.innerHTML = `<span class="muted small"><span class="spinner"></span> reading their papers…</span>`;
      try {
        const titles = await api("GET", `/api/search/s2/${b.dataset.titles}/titles`);
        holder.innerHTML = titles.length ? `<ul>${titles.map(t => `<li>${esc(t)}</li>`).join("")}</ul>` : `<span class="muted small">no papers listed</span>`;
        holder.dataset.loaded = "1";
      } catch (err) { holder.innerHTML = `<span class="muted small">${esc(err.message)}</span>`; }
    };
    b.addEventListener("click", load);
    b.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") load(e); });
  });
}
function viewNewPublic() {
  const NONE = "__none__";
  flow(app, [
    { icon: "telescope", color: "sage", q: () => `Whose research <span class="hand">taste</span> should the loop learn?`,
      help: () => "Type a researcher's full name. We'll look them up on Semantic Scholar and Wikipedia.",
      body: st => `<input class="tf-input" id="f-who" type="text" placeholder="e.g. a researcher's full name" value="${esc(st.who || "")}">`,
      bind: (sc, st) => sc.querySelector("#f-who").addEventListener("input", e => { st.who = e.target.value; }),
      ok: "Search",
      submit: async st => {
        st.who = (st.who || "").trim();
        if (!st.who) throw new Error("Who are we looking for?");
        const [cands, wiki] = await Promise.all([
          api("GET", `/api/search/s2?name=${encodeURIComponent(st.who)}`).catch(e => ({ error: e.message })),
          api("GET", `/api/search/wikipedia?name=${encodeURIComponent(st.who)}`).catch(() => null),
        ]);
        st.s2error = cands && cands.error; st.cands = Array.isArray(cands) ? cands.slice(0, 8) : []; st.wiki = wiki;
        st.author = undefined; st.name = st.who; st.slug = slugify(st.who);
      } },
    { icon: "magnifier", color: "ochre",
      q: st => st.cands.length ? `Which <span class="hand">${esc(st.who)}</span> do you mean?` : `No Semantic Scholar author called <span class="hand">${esc(st.who)}</span>.`,
      help: st => st.s2error ? `Semantic Scholar didn't answer (${esc(st.s2error)}). You can continue with arXiv and web sources.`
        : st.cands.length ? "Namesakes are common: check the affiliation and top papers. Press a letter to choose."
        : "You can still continue with arXiv and web sources.",
      choices: { key: "author", items: st => [...st.cands.map(c => ({ value: c.author_id, html: candidateHtml(c) })),
                                               { value: NONE, html: `<span class="muted">None of these: continue without Semantic Scholar</span>` }] },
      bind: sc => bindTopPapers(sc),
      submit: async st => { if (st.author === undefined) throw new Error("Pick one (or “none of these”)."); } },
    { icon: "book", color: "sky", skip: st => !st.wiki,
      q: st => `Found a Wikipedia article for <span class="hand">${esc(st.wiki.title)}</span>. Use it as the bio?`,
      help: st => `<em>${esc(st.wiki.extract)}</em>`,
      choices: { key: "useWiki", items: () => [{ value: true, html: "Yes, use it" }, { value: false, html: "No, leave the bio empty" }] },
      submit: async st => { if (st.useWiki === undefined) st.useWiki = true; } },
    { icon: "key", color: "clay", q: () => `Last thing: what should this profile be <span class="hand">called</span>?`,
      help: () => `The id is what you pass to the loop as <code>--researcher &lt;id&gt;</code>.`,
      body: st => `<input class="tf-input" id="f-pname" type="text" value="${esc(st.name)}">
        <div style="margin-top:1rem"><input class="tf-input mono" id="f-pslug" aria-label="Profile id" placeholder="id" type="text" value="${esc(st.slug)}" spellcheck="false" style="font-size:1.1rem"></div>`,
      bind: (sc, st) => {
        sc.querySelector("#f-pname").addEventListener("input", e => { st.name = e.target.value; if (!st.slugTouched) { st.slug = slugify(st.name); sc.querySelector("#f-pslug").value = st.slug; } });
        sc.querySelector("#f-pslug").addEventListener("input", e => { st.slug = e.target.value; st.slugTouched = true; });
      },
      ok: "Create profile",
      submit: async st => {
        st.slug = slugify(st.slug || ""); if (!(st.name || "").trim() || !st.slug) throw new Error("A name and an id, please.");
        await slugFree(st.slug);
        const meta = await api("POST", "/api/profiles", { name: st.name.trim(), mode: "public", slug: st.slug });
        const picked = st.cands.find(c => c.author_id === st.author), patch = {};
        if (picked) { patch.s2_author = picked; if (picked.affiliations.length) patch.affiliation = picked.affiliations.join("; "); }
        if (st.useWiki && st.wiki) { patch.bio = st.wiki.extract; patch.bio_source = st.wiki.url; }
        if (Object.keys(patch).length) await api("PATCH", `/api/profiles/${meta.slug}`, patch);
        st.slug = meta.slug; st.picked = picked;
      } },
  ], {
    onDone: (st, c) => doneScreen(c, {
      title: `${esc(st.name)} has a profile`, icon: "telescope",
      text: st.picked ? `Linked to ${esc(st.picked.name)} on Semantic Scholar (${fmtNum(st.picked.papers)} papers). Now let's gather their work.` : "Now let's gather their work.",
      actions: `<a class="btn primary" href="#/p/${esc(st.slug)}/sources">Gather sources ${doodle("telescope", { size: 20, color: "sage" })}</a>`,
    }),
  });
}

/* Author picker used on the Identity page and for "import your publications". onPick(candidate). */
function renderCandidates(box, name, cands, onPick, goLabel) {
  let selected = null;
  const list = Array.isArray(cands) ? cands : [];
  box.innerHTML = `${cands && cands.error ? `<div class="notice warn">Semantic Scholar: ${esc(cands.error)}. You can still continue with arXiv and web sources.</div>` : ""}
    ${!list.length && !(cands && cands.error) ? `<div class="notice">No Semantic Scholar author found. You can continue with arXiv and web sources.</div>` : ""}
    <div class="choices">${list.map((c, i) => `
      <button type="button" class="option cand-option" data-i="${i}" style="--i:${i}">
        <span class="n">${LETTERS[i]}</span><span style="flex:1">${candidateHtml(c)}</span>
        <span class="tick">${doodle("check", { size: 22, color: "sage", tilt: -6 })}</span></button>`).join("")}</div>
    ${list.length ? `<div class="row end" style="margin-top:1rem"><button class="btn primary" data-go disabled>${esc(goLabel)}</button></div>` : ""}`;
  bindTopPapers(box);
  box.querySelectorAll(".cand-option").forEach(el => el.addEventListener("click", () => {
    box.querySelectorAll(".cand-option").forEach(c => c.classList.toggle("chosen", c === el));
    selected = list[+el.dataset.i];
    box.querySelector("[data-go]").disabled = false;
  }));
  const goBtn = box.querySelector("[data-go]");
  if (goBtn) goBtn.addEventListener("click", () => onPick(selected));
}

// ---------- workspace ----------
const STEP_ICONS = { about: "person", materials: "stack", questionnaire: "chat", tradeoffs: "scale", identity: "magnifier",
  sources: "telescope", corpus: "folder", build: "flask", use: "rocket" };
const TICK = `<svg class="tick" viewBox="0 0 20 20" aria-hidden="true"><path filter="url(#rough)" d="M3 11 L8 16 L17 4"/></svg>`;
const STEPS = {
  personal: [["about", "About & consent"], ["materials", "Materials"], ["questionnaire", "Questionnaire"], ["tradeoffs", "Trade-offs"], ["build", "Build & review"], ["use", "Use in the loop"]],
  public: [["identity", "Identity"], ["sources", "Gather sources"], ["corpus", "Review corpus"], ["build", "Build & review"], ["use", "Use in the loop"]],
  external: [["build", "Profile"], ["corpus", "Corpus"], ["use", "Use in the loop"]],
};

async function refresh(slug) {
  S.st = await api("GET", `/api/profiles/${slug || S.slug}`);
  document.querySelectorAll(".step[data-step]").forEach(el => el.classList.toggle("done", !!stepDone(el.dataset.step)));
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
    <div class="workspace">
      <nav class="steps" aria-label="Steps">
        <div class="steps-head"><h2>${esc(S.st.meta.name)}</h2></div>
        ${steps.map(([k, label], i) => `<a class="step ${k === step ? "active" : ""} ${stepDone(k) ? "done" : ""}" data-step="${k}" href="#/p/${esc(slug)}/${k}">
          ${doodle(STEP_ICONS[k] || "sparkle", { size: 30, seed: k })}<span class="label">${esc(label)}</span>${TICK}</a>`).join("")}
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

function head(title, desc, icon) {
  const step = location.hash.split("/")[3] || "";
  return `<div class="section-head">${doodle(icon || STEP_ICONS[step] || "sparkle", { size: 64, seed: step, cls: "pop wobble" })}
    <div><h1>${esc(title)}</h1>${desc ? `<p>${desc}</p>` : ""}</div></div>`;
}

/* Cards get a staggered entrance and a doodle beside their title, chosen by the title. Done by
   an observer so every view (and every partial re-render) is decorated the same way. */
const CARD_ICONS = [[/consent/i, "heart"], [/upload/i, "upload"], [/paste/i, "paper"], [/link/i, "link"], [/publication/i, "cap"],
  [/semantic scholar/i, "magnifier"], [/^build/i, "flask"], [/principle/i, "feather"], [/weight/i, "scale"], [/files/i, "folder"],
  [/user model/i, "person"], [/corpus/i, "folder"], [/about|details/i, "person"]];
new MutationObserver(() => {
  let k = 0;
  app.querySelectorAll(".card:not([data-dec])").forEach(card => {
    card.dataset.dec = "1";
    if (!card.closest(".tf")) { card.classList.add("rise"); card.style.setProperty("--i", k++); }
    const h = card.querySelector(":scope > h3, :scope > .row > h3");
    if (h && !h.querySelector(".doodle")) {
      const hit = CARD_ICONS.find(([re]) => re.test(h.textContent));
      h.insertAdjacentHTML("afterbegin", doodle(hit ? hit[1] : "sparkle", { size: 30, seed: h.textContent }));
      h.classList.add("ct");
    }
  });
}).observe(app, { childList: true, subtree: true });

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
        </label>
    </div>
    <div class="card stack">
      <h3>Consent</h3>
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
        ${doodle("upload", { size: 56, color: "ochre", tilt: -6 })}<strong>Drop files here</strong> or click to choose
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
        </label>
      <div class="row end"><button class="btn" id="links-add">Fetch pages</button></div>
    </div>
    <div class="card stack">
      <h3>Import your publications</h3>
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
    renderCandidates(div, name, cands, picked => {
      const body = { name, arxiv: document.getElementById("pub-arxiv").checked };
      if (picked) { body.s2_author_id = picked.author_id; api("PATCH", `/api/profiles/${S.slug}`, { s2_author: picked }).catch(fail); }
      box.innerHTML = "";
      startJob("gather", body, document.getElementById("job"), () => renderCorpus(document.getElementById("corpus")));
    }, "Import this author's papers");
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

// ----- Questionnaire (personal): one question per screen
function panelQuestionnaire(panel, nextBtn) {
  const qs = S.st.questions, answers = { ...(S.st.meta.questionnaire || {}) };
  const draftKey = `studio:q:${S.slug}`, draft = load(draftKey) || {};
  const firstOpen = Math.max(0, qs.findIndex(q => !answers[q.id]));
  const icons = ["telescope", "star", "magnifier", "arrow", "scale", "stack", "lightbulb", "book", "coffee", "rocket", "compass", "heart"];
  const colors = ["clay", "ochre", "sage", "sky", "rose"];
  async function save(q, v) {
    v = (v || "").trim();
    if (v === (answers[q.id] || "")) return;
    const meta = await api("POST", `/api/profiles/${S.slug}/answers`, { answers: { [q.id]: v } });
    answers[q.id] = v; S.st.meta = meta;
    delete draft[q.id]; store(draftKey, Object.keys(draft).length ? draft : undefined);
    refresh().catch(() => {});
  }
  flow(panel, qs.map((q, k) => ({
    icon: icons[k % icons.length] === "compass" ? "globe" : icons[k % icons.length], color: colors[k % colors.length],
    q: () => esc(q.text) + (q.kind === "other" ? ` <span class="badge" style="vertical-align:middle">outside research</span>` : ""),
    help: () => k === 0 ? "Answer in your own words; a few sentences is plenty. Every question is optional and there are no right answers." : "",
    body: () => `<textarea class="tf-input" data-q="${esc(q.id)}" placeholder="Type your answer here…">${esc(draft[q.id] ?? answers[q.id] ?? "")}</textarea>`,
    ok: (answers[q.id] || draft[q.id]) ? "Save" : "OK",
    skipLabel: "skip",
    bind: sc => {
      const t = sc.querySelector("textarea");
      let timer;
      t.addEventListener("input", () => {
        draft[q.id] = t.value; store(draftKey, draft);
        clearTimeout(timer);
        timer = setTimeout(() => save(q, t.value).catch(fail), 1500);
      });
    },
    submit: async (st, sc) => save(q, sc.querySelector("textarea").value),
  })), {
    start: firstOpen,
    onDone: (st, c) => {
      const n = qs.filter(q => answers[q.id]).length;
      doneScreen(c, { title: n ? "Thank you!" : "Maybe later, then", icon: n ? "heart" : "coffee",
        text: `You answered ${n} of ${qs.length} questions. Your answers are saved as part of your corpus, so they shape the profile like your papers do.`,
        actions: `<a class="btn" href="#/p/${esc(S.slug)}/questionnaire" onclick="setTimeout(render,0)">Review answers</a>
                  <a class="btn primary" href="#/p/${esc(S.slug)}/tradeoffs">On to trade-offs ${doodle("scale", { size: 20, color: "sage" })}</a>` });
    },
  });
}

// ----- Trade-offs (personal; trackp seed pairs), one per screen
async function panelTradeoffs(panel, nextBtn, seq) {
  const st = S.st;
  const consentOk = st.consent.length && st.consent.every(c => c.ticked);
  if (!st.choices.pairs) {
    flow(panel, [{
      icon: "scale", color: "sage", q: () => `Quick <span class="hand">trade-offs</span>: which would you pick?`,
      help: () => consentOk
        ? "Each question shows a research situation and two options, both reasonable. The set comes from the personal track's trade-off bank. Your answers are what a user model is fitted on."
        : `First tick every consent box under <a href="#/p/${esc(S.slug)}/about">About &amp; consent</a>.`,
      ok: "Prepare questions",
      submit: async () => { if (!consentOk) throw new Error("Consent first."); await api("POST", `/api/profiles/${S.slug}/choices/generate`, {}); },
    }], { onDone: () => render() });
    return;
  }
  const pend = await api("GET", `/api/profiles/${S.slug}/choices/pending`);
  if (stale(seq)) return;
  const items = pend.items, total = st.choices.pairs, recorded = new Set();
  if (!items.length) {
    panel.innerHTML = `<div class="tf"><div class="tf-progress"><div style="width:100%"></div></div><div class="tf-stage"></div><div class="tf-nav"></div></div>`;
    doneScreen(panel, { title: "All trade-offs answered", icon: "scale", text: `You answered all ${fmtNum(total)} questions. Next, build your profile and fit a user model.`,
      actions: `<a class="btn primary" href="#/p/${esc(S.slug)}/build">Build & review ${doodle("flask", { size: 20, color: "sage" })}</a>` });
    return;
  }
  const answeredBefore = st.choices.answered;
  const steps = [{
    icon: "scale", color: "sage",
    q: () => answeredBefore ? `Welcome back. <span class="hand">${fmtNum(items.length)}</span> trade-offs to go.` : `<span class="hand">${fmtNum(items.length)}</span> quick trade-offs.`,
    help: () => `Each shows a situation and two options. About ${minutes(items.length, 25)} minutes (${minutes(items.length, 35)} if you add a one-line reason).
      There are no right answers: each asks what <em>you</em> would do. Skip anything you can't decide; skipped items come back next time.`,
    ok: answeredBefore ? "Continue" : "Begin",
  }];
  items.forEach((it, k) => {
    const same = k > 0 && groupKey(items[k - 1]) === groupKey(it);
    const key = `pick_${k}`;
    steps.push({
      icon: k % 2 ? "scale" : "lightbulb", color: ["sage", "ochre", "sky", "clay"][k % 4], noAutofocus: true,
      q: () => esc(it.question || "Which would you pick?"),
      body: () => `${same ? `<details class="context-fold"><summary class="fold-toggle">show the situation again</summary><div class="context">${esc(it.context)}</div></details>`
                        : `<div class="context">${esc(it.context)}</div>`}
        ${Object.keys(it.evidence || {}).length ? `<pre class="context small">${esc(JSON.stringify(it.evidence, null, 1))}</pre>` : ""}
        <div style="height:1rem"></div>`,
      choices: { key, autoNext: false, items: () => it.options.map((o, j) => ({ value: j + 1, html: esc(o) })) },
      skipLabel: "skip",
      bind: (sc, state) => {
        const box = document.createElement("label"); box.className = "field reason"; box.style.marginTop = "1.1rem";
        box.innerHTML = `<span>why? <span class="muted">(optional, one sentence)</span></span><input type="text" data-reason value="${esc(state[`why_${k}`] || "")}">`;
        sc.querySelector(".tf-body").appendChild(box);
        box.querySelector("input").addEventListener("input", e => { state[`why_${k}`] = e.target.value; });
        if (recorded.has(it.id)) sc.querySelector(".tf-error").textContent = "saved ✓";
      },
      submit: async (state, sc) => {
        if (recorded.has(it.id)) return;
        if (!state[key]) throw new Error("Pick one, or skip.");
        await api("POST", `/api/profiles/${S.slug}/choices/record`, { id: it.id, choice: state[key], reason: state[`why_${k}`] || "" });
        recorded.add(it.id); refresh().catch(() => {});
      },
    });
  });
  flow(panel, steps, {
    onDone: (state, c) => {
      const left = items.length - recorded.size;
      doneScreen(c, { title: left ? "Good stopping point" : "That's all of them!", icon: left ? "coffee" : "star",
        text: left ? `${fmtNum(recorded.size)} answered this time, ${fmtNum(left)} skipped (they'll come back next time).` : `${fmtNum(answeredBefore + recorded.size)} of ${fmtNum(total)} answered.`,
        actions: `<a class="btn primary" href="#/p/${esc(S.slug)}/build">Build & review ${doodle("flask", { size: 20, color: "sage" })}</a>` });
    },
  });
}

function groupKey(it) { return `${it.group ?? ""}\u0000${it.context}`; }
function minutes(n, secondsEach) { return Math.max(1, Math.round((n * secondsEach) / 60)); }

// ----- Identity (public)
function panelIdentity(panel, nextBtn) {
  const m = S.st.meta, a = m.s2_author;
  panel.innerHTML = head("Identity", "Who this profile is about. The Semantic Scholar author decides which papers are imported.") + `
    <div class="card stack">
      <div class="grid2">
        <label class="field"><span>Name</span><input id="id-name" type="text" value="${esc(m.name)}"></label>
        <label class="field"><span>Affiliation</span><input id="id-aff" type="text" value="${esc(m.affiliation)}"></label>
      </div>
      <label class="field"><span>Bio</span><textarea id="id-bio" rows="4">${esc(m.bio)}</textarea>
        </label>
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
    renderCandidates(div, val("id-name"), cands, async picked => {
      try { await api("PATCH", `/api/profiles/${S.slug}`, { s2_author: picked }); toast("Author set"); render(); } catch (e) { fail(e); }
    }, "Use this author");
  });
}

// ----- Sources (public)
function panelSources(panel, nextBtn) {
  const m = S.st.meta, a = m.s2_author, exa = S.config.exa_available;
  panel.innerHTML = head("Gather sources", "Pick where to look. Everything lands in the corpus, which you review next. Sources that fail are reported and the rest still run.") + `
    <div class="card stack">
      <label class="field"><span>Name to match</span><input id="g-name" type="text" value="${esc(m.name)}"></label>
      <label class="check"><input type="checkbox" id="g-s2" ${a ? "checked" : "disabled"}><span><strong>Semantic Scholar papers</strong>
        ${a ? "" : `<span class="muted small">select an author under <a href="#/p/${esc(S.slug)}/identity">Identity</a> first</span>`}</span></label>
      <label class="field" style="max-width:200px;margin-left:1.6rem"><span class="small">Max papers</span><input id="g-s2max" type="number" min="1" max="1000" value="150"></label>
      <label class="check"><input type="checkbox" id="g-arxiv" checked><span><strong>arXiv</strong></span></label>
      <label class="field" style="max-width:200px;margin-left:1.6rem"><span class="small">Max results</span><input id="g-axmax" type="number" min="1" max="300" value="60"></label>
      <label class="check"><input type="checkbox" id="g-wiki" ${m.bio ? "" : "checked"}><span><strong>Wikipedia bio</strong></span></label>
      <hr class="hr" style="margin:.25rem 0">
      <div class="grid2">
        <label class="field"><span>LessWrong / Alignment Forum username</span><input id="g-lw" type="text" placeholder="e.g. their-user-slug" class="mono"></label>
        <label class="field"><span>Blog RSS feed URL</span><input id="g-rss" type="url" placeholder="https://…/feed.xml"></label>
      </div>
      <label class="field"><span>Other pages they wrote, one per line</span><textarea id="g-urls" rows="3" placeholder="https://"></textarea></label>
      <hr class="hr" style="margin:.25rem 0">
      <label class="check"><input type="checkbox" id="g-exa" ${exa ? "" : "disabled"}><span><strong>Exa harvest</strong> <span class="badge warn">paid</span>
        <span class="muted small">${exa ? "" : "set EXA_API_KEY in the studio's environment to enable"}</span></span></label>
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
      n.innerHTML = `<a class="btn primary" href="#/p/${esc(S.slug)}/corpus">Review corpus →</a>`;
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
        <label class="field"><span>Documents to read</span><input id="b-max" type="number" min="1" value="${Math.min(40, Math.max(1, n))}"></label>
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
      ${m.bio ? `<p class="muted" style="margin-top:.5rem">${esc(m.bio)}</p>` : ""}
      ${card ? `
        ${card.summary ? `<p class="profile-summary" style="margin-top:.75rem">${esc(card.summary)}</p>` : ""}
        ${card.interests && card.interests.length ? `<h4>Interests</h4><div>${card.interests.map((x, i) => `<span class="chip pop" style="--r:${((i * 53) % 7) - 3}deg;--i:${i}">${esc(x)}</span>`).join("")}</div>` : ""}
        <div class="grid2" style="margin-top:.5rem">
          ${card.methods && card.methods.length ? `<div><h4>How they work</h4><ul>${card.methods.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>` : ""}
          ${card.open_questions && card.open_questions.length ? `<div><h4>Open questions</h4><ul>${card.open_questions.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>` : ""}
        </div>` : ""}
      ${m.build ? `<dl class="kv" style="margin-top:1rem"><dt>Built</dt><dd>${esc((m.build.at || "").replace("T", " ").slice(0, 16))} UTC with <span class="mono">${esc(String(m.build.llm).replace(/:$/, ""))}</span></dd>
        <dt>Documents</dt><dd>${fmtNum(m.build.docs_used)} of ${fmtNum(m.build.docs_available)}</dd>
        ${m.build.principles_extracted > (prof.principles || []).length ? `<dt>Principles</dt><dd>merged from ${fmtNum(m.build.principles_extracted)} extracted (raw list kept in studio.json)</dd>` : ""}
        <dt>Model calls</dt><dd>${fmtNum(m.build.calls)}${m.build.cost_usd ? ` · $${m.build.cost_usd}` : ""}</dd></dl>` : ""}
    </div>
    <div style="margin-top:1rem">
      <div class="card">
        <h3>Feature weights</h3>
        <div class="weights" id="w-list"></div>
      </div>
      <div class="card">
        <h3>Principles</h3>
        <div class="principles" id="pr-list"></div>
        ${editable ? `<button class="btn small" id="pr-add" style="margin-top:.7rem">+ add principle</button>` : ""}
      </div>
    </div>
    ${editable ? `<div class="row end" style="margin-top:1rem"><button class="btn primary" id="p-save" disabled>Save edits</button></div>` : ""}`;
  const dirty = () => { const b = document.getElementById("p-save"); if (b) b.disabled = false; };
  function drawPrinciples() {
    const list = document.getElementById("pr-list");
    list.innerHTML = principles.length ? principles.map((p, i) => editable
      ? `<div class="principle"><span class="pn mono">${i + 1}</span><textarea rows="1" data-pr="${i}">${esc(p)}</textarea><button class="btn ghost small" data-prx="${i}" aria-label="Remove principle ${i + 1}">✕</button></div>`
      : `<div class="principle read rise" style="--i:${i}">${esc(p)}</div>`).join("") : `<span class="muted small">none</span>`;
    list.querySelectorAll("[data-pr]").forEach(t => {
      const fit = () => { t.style.height = "auto"; t.style.height = t.scrollHeight + 2 + "px"; };
      t.addEventListener("input", () => { principles[+t.dataset.pr] = t.value; fit(); dirty(); });
      requestAnimationFrame(fit);
    });
    list.querySelectorAll("[data-prx]").forEach(b => b.addEventListener("click", () => { principles.splice(+b.dataset.prx, 1); drawPrinciples(); dirty(); }));
  }
  function drawWeights() {
    const list = document.getElementById("w-list");
    list.innerHTML = st.features.map(f => {
      const v = Number(w[f] || 0), pct = Math.min(50, Math.abs(v) * 50);
      return `<div class="weight ${editable ? "editable" : ""}" title="${esc(FEATURE_HELP[f] || "")}" style="--i:${st.features.indexOf(f)}"><span>${esc(f.replace("_", " "))}</span>
        <div class="bar"><div class="fill" data-fill="${esc(f)}"></div>
          ${editable ? `<input type="range" min="-1" max="1" step="0.05" value="${v}" data-w="${esc(f)}" aria-label="${esc(f)} weight">` : ""}</div>
        <span class="val" data-wv="${esc(f)}">${v >= 0 ? "+" : ""}${v.toFixed(2)}</span></div>`;
    }).join("");
    const paint = f => {
      const v = Number(w[f] || 0), pct = Math.min(50, Math.abs(v) * 50), el = list.querySelector(`[data-fill="${f}"]`);
      el.className = `fill ${v >= 0 ? "pos" : "neg"}`;
      Object.assign(el.style, v >= 0 ? { left: "50%", width: pct + "%" } : { left: 50 - pct + "%", width: pct + "%" });
      list.querySelector(`[data-wv="${f}"]`).textContent = `${v >= 0 ? "+" : ""}${v.toFixed(2)}`;
    };
    st.features.forEach(paint);
    list.querySelectorAll("[data-w]").forEach(r => r.addEventListener("input", () => {
      w[r.dataset.w] = +r.value; paint(r.dataset.w);
      list.querySelector(`[data-fill="${r.dataset.w}"]`).style.animation = "none"; dirty();
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
    <div class="row"><h3 style="margin:0">User model</h3><span class="spacer"></span>
      ${st.has_usermodel ? '<span class="badge ok">usermodel.json present</span>' : ""}</div>
    ${n < 10 ? `<div class="notice warn small">You have ${fmtNum(n)} answered trade-off item${n === 1 ? "" : "s"}. Answer the questions under <a href="#/p/${esc(S.slug)}/tradeoffs">Trade-offs</a> first.</div>` : ""}
    <div class="grid2">
      <label class="field"><span>Method</span><select id="um-method">${S.config.methods.map(x => `<option ${x === "m1" ? "selected" : ""}>${x}</option>`).join("")}</select></label>
      <label class="field"><span>Backend</span><select id="um-backend">${S.config.backends.map(b => `<option>${b}</option>`).join("")}</select></label>
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
  const cmd = (label, c, note) => `<div style="margin-top:1.1rem"><strong>${esc(label)}</strong>
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
  let shownStatus = null, shownLines = 0;
  const draw = j => {
    if (!document.body.contains(el)) return false;
    if (j.status !== shownStatus) {   // full render only when the status changes; log lines are appended
      const icon = j.status === "running" ? doodle(kind === "gather" ? "magnifier" : kind === "fit" ? "person" : "pencil", { size: 46, color: "ochre", tilt: -8 })
        : j.status === "done" ? doodle("check", { size: 46, color: "sage", tilt: -4, cls: "pop" }) : doodle("lightbulb", { size: 46, color: "rose", tilt: 6 });
      el.innerHTML = `<div class="card job" data-dec="1"><div class="job-head ${j.status === "running" ? "scribbling" : ""}">${icon}
        <div><strong>${esc(label)}${j.status === "running" ? "…" : j.status === "done" ? ": done" : ": stopped"}</strong></div></div>
        ${j.error ? `<div class="notice bad small" style="margin-top:.6rem">${esc(j.error)}</div>` : ""}
        <div class="job-log"></div></div>`;
      shownStatus = j.status; shownLines = 0;
    }
    const lg = el.querySelector(".job-log"), ph = lg.querySelector("[data-ph]");
    if (!j.log.length) { if (!ph) lg.innerHTML = `<span class="line muted" data-ph>starting…</span>`; return true; }
    if (ph) ph.remove();
    lg.insertAdjacentHTML("beforeend", j.log.slice(shownLines).map(l => `<span class="line">${esc(l)}</span>`).join(""));
    shownLines = j.log.length; lg.scrollTop = lg.scrollHeight;
    return true;
  };
  draw(job);
  const tick = async () => {
    try { job = await api("GET", `/api/jobs/${job.id}`); } catch (e) { return fail(e); }
    const visible = draw(job);
    if (job.status === "running") return setTimeout(tick, 900);
    if (job.status === "done") { toast(`${label}: done`); const d = el.querySelector(".job-head .doodle"); if (d && visible) burstAt(d); }
    if (S.slug === slug) { await refresh(slug); if (visible && job.status === "done" && onDone) onDone(job); }
  };
  setTimeout(tick, 700);
}
