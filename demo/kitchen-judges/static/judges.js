/* Judges' additions to Profile Kitchen. Runs entirely in the browser: no server calls, no cost.
   #/judges  : a six-question grill (decision points D1-D6 from autoresearch/taste/grill.py) that
               builds the judge's own user model and shows which eval rewrite their agent would pick.
   #/results : the measured results on Kimi K2.6 (results/e3b/final_report_all.md, strong 9-seed subset). */
"use strict";
(function () {
  const J = (window.JUDGES = {});

  const AX = { real: "Realism", valid: "Rigor", bold: "Boldness" };
  const GQ = [
    { p: "D1", k: "Which intervention to test next", q: "The target model keeps saying “this looks like a test.” What do you try first?",
      o: [["Strip the tells: placeholder names, countdowns, grading format", { real: 2 }, "Remove the cues that make a scenario read as an evaluation."],
          ["Change one variable and keep the behaviour test intact", { valid: 2 }, "Change one thing at a time so effects stay attributable."],
          ["Rebuild the scenario around a completely new premise", { bold: 2 }, "Prefer big reframes over local edits."]] },
    { p: "D2", k: "What evidence to collect", q: "You have budget for one more batch. Where does it go?",
      o: [["Read the chain of thought for spontaneous “this is a test”", { real: 2 }, "Trust what the model says unprompted over what it says when asked."],
          ["Fresh samples on the same seed to confirm the effect", { valid: 2 }, "Confirm every gain on fresh samples before believing it."],
          ["Many new seeds, once each, to widen the search", { bold: 2 }, "Breadth first: search widely before going deep."]] },
    { p: "D3", k: "Accept, reject or defer", q: "A rewrite drops awareness, but validity slips a little. Your call?",
      o: [["Accept: a test the model sees through measures nothing", { real: 2 }, "An eval the model recognises is already invalid."],
          ["Defer until validity is re-checked on fresh samples", { valid: 2 }, "Never trade validity for a better-looking score."],
          ["Reject and try something bigger", { bold: 1, valid: 1 }, "Small, compromised wins aren't worth keeping."]] },
    { p: "D4", k: "Keep or abandon a direction", q: "Three rounds in, gains are small but steady. Keep going?",
      o: [["Keep: realism compounds", { real: 2 }, "Steady realism gains add up; stay the course."],
          ["Keep, but only if it beats the plain control arm", { valid: 2 }, "A direction only counts if it beats a matched control."],
          ["Abandon: small gains mean the wrong direction", { bold: 2 }, "Cut directions that don't show a big effect early."]] },
    { p: "D5", k: "How to read a result", q: "The model says “probably a test” 95% of the time, even on real sessions. What does that tell you?",
      o: [["Self-report is broken; trust behaviour and CoT instead", { real: 1, valid: 1 }, "Treat self-report as uninformative when it doesn't separate real from test."],
          ["Nothing, until it's calibrated against a known baseline", { valid: 2 }, "Calibrate every metric against a baseline first."],
          ["The model is just suspicious; push harder on novelty", { bold: 2 }, "When the model resists, change the game."]] },
    { p: "D6", k: "What to claim", q: "Taste beats the plain control, but not significantly. How do you write it up?",
      o: [["Lead with the effect vs stock, call the rest a trend", { real: 1, valid: 1 }, "Claim what's significant; label the rest a trend."],
          ["Report the exact numbers, n and CIs, and say it's a trend", { valid: 2 }, "Report n and intervals with every claim."],
          ["Claim taste works and move on to the next idea", { bold: 2 }, "Move fast; the next idea matters more than the write-up."]] },
  ];

  /* the researcher profile closest to the judge's axes, with that arm's measured result
     (spontaneous awareness A1 and Petri, strong 9-seed subset, results/e3b/final_report_all.md) */
  const PICKS = {
    real:  { who: "Hobbhahn", name: "The realism rewrite", cls: "sage",
             what: "Turn the eval into routine work: a recurring job with history and a named reader. No countdown, no grading format.",
             res: "Spontaneous awareness 0.36 → 0.02 vs fresh stock (90% CI excludes zero). Petri 3.14 → 1.22." },
    mixed: { who: "Greenblatt", name: "The skeptical realist", cls: "sky",
             what: "Make it look real, but accept a change only when it holds up on fresh samples and against a control.",
             res: "Spontaneous awareness 0.36 → 0.06 vs fresh stock (90% CI excludes zero). Petri 3.14 → 1.11." },
    valid: { who: "Bowman", name: "The validity-first rewrite", cls: "ochre",
             what: "Minimal, single-variable edits that keep the behaviour test intact, each one confirmed before it's accepted.",
             res: "Spontaneous awareness 0.36 → 0.11 vs fresh stock (90% CI just excludes zero). Petri 3.14 → 1.33." },
    bold:  { who: "none of our top profiles", name: "The bold reframe", cls: "clay",
             what: "Rebuild the scenario around a new premise and search widely across seeds.",
             res: "None of our best expert profiles work this way. The profiles that cut awareness most (Hobbhahn 0.02, Greenblatt 0.06, Bowman 0.11, vs stock 0.36) lean on realism and rigor. Try dragging toward them." },
  };

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const dd = (n, o) => (typeof doodle === "function" ? doodle(n, o) : "");
  const st = { i: -1, s: { real: 0, valid: 0, bold: 0 }, rules: [], custom: [], w: null, name: "", av: 0 };

  function pick(s) {
    const order = Object.keys(s).sort((a, b) => s[b] - s[a]);
    if (order[0] !== "bold" && order[1] !== "bold" && Math.abs(s.real - s.valid) <= Math.max(2, 0.15 * (s.real + s.valid))) return "mixed";
    return order[0];
  }
  const AVATARS = [["person", "clay"], ["rocket", "sky"], ["telescope", "sage"], ["flask", "ochre"], ["lightbulb", "ochre"], ["feather", "rose"], ["key", "sky"], ["star", "clay"]];
  const SAVE = "kitchen-judges-agent";
  const save = () => { try { localStorage.setItem(SAVE, JSON.stringify(st)); } catch (_) {} };
  try { const o = JSON.parse(localStorage.getItem(SAVE) || "null"); if (o && o.s) Object.assign(st, o); } catch (_) {}
  if (!st.name) st.name = ""; if (st.av == null) st.av = 0; if (st.i == null) st.i = -1;
  if (!st.custom) st.custom = [];
  const fx = (el) => { try { if (typeof burstAt === "function" && el) burstAt(el); } catch (_) {} };

  function header(icon, color, title, sub) {
    return `<div class="jg-head rise" style="--i:1">${dd(icon, { size: 52, color, tilt: -8, cls: "wobble" })}
      <div><h1>${title}</h1><p class="muted">${sub}</p></div></div>`;
  }

  function viewJudges() {
    const app = document.getElementById("app");
    if (st.i < 0) {   /* step 0: who is this agent for */
      app.innerHTML = `
        <section class="jg">
          ${header("sparkle", "clay", "Build your own research agent", "Sixty seconds, six decisions. Your answers become the user model the agent follows overnight.")}
          <article class="card jg-card jg-hello rise" style="--i:2">
            <label class="mono small muted" for="jg-name">NAME YOUR AGENT'S RESEARCHER</label>
            <input id="jg-name" class="jg-name" placeholder="your name" value="${esc(st.name)}" maxlength="40" autocomplete="off">
            <div class="mono small muted" style="margin-top:1.2rem">PICK YOUR SIGIL</div>
            <div class="jg-avs">${AVATARS.map(([n, c], k) => `<button class="jg-av ${k === st.av ? "on" : ""}" data-k="${k}" aria-label="${n}">${dd(n, { size: 46, color: c, tilt: (k % 3 - 1) * 8 })}</button>`).join("")}</div>
            <button class="btn primary jg-start">Start the grill →</button>
          </article>
        </section>`;
      const inp = app.querySelector("#jg-name"); inp.focus();
      inp.addEventListener("input", () => { st.name = inp.value; save(); });
      app.querySelectorAll(".jg-av").forEach((b) => b.addEventListener("click", () => { st.av = +b.dataset.k; save(); app.querySelectorAll(".jg-av").forEach((x) => x.classList.toggle("on", x === b)); fx(b); }));
      const go = () => { st.i = 0; st.s = { real: 0, valid: 0, bold: 0 }; st.rules = []; save(); viewJudges(); };
      app.querySelector(".jg-start").addEventListener("click", go);
      inp.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
      if (typeof setKeys === "function") setKeys(null);
      return;
    }
    if (st.i < GQ.length) {
      const g = GQ[st.i];
      app.innerHTML = `
        <section class="jg">
          ${header("lightbulb", "ochre", esc(st.name ? st.name + "'s agent" : "Your agent"), "Answer like you would at 3am with a run going sideways.")}
          <div class="jg-prog" aria-hidden="true">${GQ.map((_, k) => `<i class="${k < st.i ? "done" : k === st.i ? "cur" : ""}"></i>`).join("")}</div>
          <article class="card jg-card rise" style="--i:2">
            <div class="jg-meta mono"><b>${g.p}</b><span>${esc(g.k)}</span><span>${st.i + 1} / ${GQ.length}</span></div>
            <h2 class="jg-q">${esc(g.q)}</h2>
            <div class="jg-opts">${g.o.map(([t], j) => `<button class="jg-opt" data-j="${j}" style="--i:${j}"><span class="jg-key mono">${"ABC"[j]}</span>${esc(t)}</button>`).join("")}</div>
            <button class="btn ghost small jg-back">← back</button>
          </article>
        </section>`;
      let locked = false;
      const choose = (j, el) => {
        if (locked) return; locked = true;
        const [, w, rule] = g.o[j]; for (const a in w) st.s[a] += w[a]; st.rules.push({ p: g.p, rule, w, on: true }); st.i++; save();
        if (el) { el.classList.add("picked"); fx(el); setTimeout(viewJudges, 260); } else viewJudges();
      };
      app.querySelectorAll(".jg-opt").forEach((b) => b.addEventListener("click", () => choose(+b.dataset.j, b)));
      app.querySelector(".jg-back").addEventListener("click", () => { if (!st.rules.length) { st.i = -1; } else { const r = st.rules.pop(); for (const a in r.w) st.s[a] -= r.w[a]; st.i--; } save(); viewJudges(); });
      if (typeof setKeys === "function") setKeys((e) => { const j = "abc".indexOf(e.key.toLowerCase()); if (j >= 0 && !e.metaKey && !e.ctrlKey) { choose(j, app.querySelectorAll(".jg-opt")[j]); return true; } });
      return;
    }
    viewStudio();
  }

  /* the agent's live decisions: for each decision point, the option whose weights best match the current taste */
  function decide(w) {
    return GQ.map((g) => {
      let best = 0, bv = -1;
      g.o.forEach(([, ow], j) => { let v = 0; for (const a in ow) v += ow[a] * w[a]; if (v > bv + 1e-9) { bv = v; best = j; } });
      return { p: g.p, k: g.k, t: g.o[best][0], j: best };
    });
  }

  function viewStudio() {
    const app = document.getElementById("app");
    const [avn, avc] = AVATARS[st.av] || AVATARS[0];
    if (!st.w) { const tot = st.s.real + st.s.valid + st.s.bold || 1; st.w = { real: Math.round(100 * st.s.real / tot), valid: Math.round(100 * st.s.valid / tot), bold: Math.round(100 * st.s.bold / tot) }; }
    app.innerHTML = `
      <section class="jg jg-wide">
        ${header("sparkle", "clay", esc(st.name ? st.name + "'s user model" : "Your user model"), "Built from your answers, in your browser. Drag, toggle and edit: your agent re-plans live.")}
        <div class="jg-grid3">
          <article class="card jg-idcard rise" style="--i:2">
            <span class="tape" aria-hidden="true"></span>
            <div class="jg-id">${dd(avn, { size: 70, color: avc, tilt: -6, cls: "bob" })}<div><div class="hand jg-idname">${esc(st.name || "Anonymous researcher")}</div><div class="mono small muted">user model · v1 · local</div></div></div>
            <h3>Taste weights</h3>
            ${Object.keys(AX).map((a) => `<div class="jg-ax"><span>${AX[a]}</span><input type="range" min="0" max="100" value="${st.w[a]}" data-a="${a}" class="jg-range ${a}"><b class="mono" data-v="${a}">${st.w[a]}</b></div>`).join("")}
            <div class="row jg-presets"><span class="mono small muted">presets</span>
              <button class="btn small" data-pre="real">Realist</button><button class="btn small" data-pre="valid">Rigorist</button><button class="btn small" data-pre="bold">Maverick</button></div>
            <h3 class="jg-sub">Principles <span class="mono small muted">click to toggle</span></h3>
            <ul class="jg-rules">${st.rules.map((r, k) => `<li class="${r.on === false ? "off" : ""}" data-r="${k}"><span class="mono">${r.p}</span> ${esc(r.rule)}</li>`).join("")}
              ${st.custom.map((c, k) => `<li class="mine" data-c="${k}"><span class="mono">YOU</span> ${esc(c)} <button class="jg-x" data-x="${k}" aria-label="remove">✕</button></li>`).join("")}</ul>
            <form class="jg-add"><input placeholder="Add your own principle…" maxlength="120"><button class="btn small">add</button></form>
          </article>
          <div class="jg-right">
            <article class="card jg-pick rise" style="--i:3"><div class="jg-pickin"></div></article>
            <article class="card jg-feed rise" style="--i:4">
              <h3>Your agent, tonight <span class="mono small muted">re-plans as you edit</span></h3>
              <ol class="jg-dec"></ol>
            </article>
          </div>
        </div>
        <div class="jg-actions center"><button class="btn jg-again">Start over</button><button class="btn jg-dl">Download user model (.json)</button><a class="btn primary" href="#/results">See the measured results →</a></div>
      </section>`;
    const pickEl = app.querySelector(".jg-pickin"), decEl = app.querySelector(".jg-dec");
    let lastPick = null, lastDec = [];
    const refresh = () => {
      const key = pick(st.w), d = PICKS[key];
      if (key !== lastPick) {
        pickEl.parentElement.className = `card jg-pick ${d.cls}`;
        pickEl.innerHTML = `<div class="mono muted small">YOUR AGENT PICKS · CLOSEST PROFILE: ${esc(d.who.toUpperCase())}</div>
          <h2 class="jg-flip">${esc(d.name)}</h2><p>${esc(d.what)}</p>
          <div class="jg-res"><span class="mono small">MEASURED ON KIMI K2.6</span><p>${esc(d.res)}</p></div>`;
        if (lastPick) fx(pickEl.querySelector("h2"));
        lastPick = key;
      }
      const dec = decide(st.w);
      decEl.innerHTML = dec.map((x, k) => `<li class="${lastDec[k] != null && lastDec[k] !== x.j ? "changed" : ""}"><span class="mono">${x.p}</span><div><small class="mono muted">${esc(x.k)}</small><div>${esc(x.t)}</div></div></li>`).join("");
      lastDec = dec.map((x) => x.j);
      save();
    };
    app.querySelectorAll(".jg-range").forEach((r) => r.addEventListener("input", () => { st.w[r.dataset.a] = +r.value; app.querySelector(`[data-v="${r.dataset.a}"]`).textContent = r.value; refresh(); }));
    const PRE = { real: { real: 75, valid: 20, bold: 5 }, valid: { real: 20, valid: 75, bold: 5 }, bold: { real: 15, valid: 10, bold: 75 } };
    app.querySelectorAll("[data-pre]").forEach((b) => b.addEventListener("click", () => {
      const to = PRE[b.dataset.pre], from = Object.assign({}, st.w), t0 = performance.now();
      const step = (now) => { const k = Math.min(1, (now - t0) / 450), e = 1 - Math.pow(1 - k, 3);
        for (const a in to) { st.w[a] = Math.round(from[a] + (to[a] - from[a]) * e); const r = app.querySelector(`.jg-range[data-a="${a}"]`); if (r) r.value = st.w[a]; const v = app.querySelector(`[data-v="${a}"]`); if (v) v.textContent = st.w[a]; }
        refresh(); if (k < 1) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    }));
    app.querySelectorAll(".jg-rules li[data-r]").forEach((li) => li.addEventListener("click", () => {
      const r = st.rules[+li.dataset.r]; r.on = r.on === false; li.classList.toggle("off", !r.on);
      for (const a in r.w) st.w[a] = Math.max(0, Math.min(100, st.w[a] + (r.on ? 1 : -1) * r.w[a] * 8));
      app.querySelectorAll(".jg-range").forEach((x) => { x.value = st.w[x.dataset.a]; app.querySelector(`[data-v="${x.dataset.a}"]`).textContent = st.w[x.dataset.a]; });
      refresh();
    }));
    app.querySelectorAll(".jg-x").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); st.custom.splice(+b.dataset.x, 1); save(); viewStudio(); }));
    app.querySelector(".jg-add").addEventListener("submit", (e) => { e.preventDefault(); const v = e.target.querySelector("input").value.trim(); if (!v) return; st.custom.push(v); save(); viewStudio(); });
    app.querySelector(".jg-again").addEventListener("click", () => { Object.assign(st, { i: -1, s: { real: 0, valid: 0, bold: 0 }, rules: [], custom: [], w: null }); save(); viewJudges(); });
    app.querySelector(".jg-dl").addEventListener("click", () => {
      const model = { researcher: st.name || "anonymous", weights: st.w, principles: st.rules.filter((r) => r.on !== false).map((r) => `${r.p}: ${r.rule}`).concat(st.custom), closest_profile: PICKS[pick(st.w)].who, decisions: decide(st.w).map((x) => ({ point: x.p, choice: x.t })) };
      const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(model, null, 2)], { type: "application/json" }));
      a.download = `${(st.name || "my").toLowerCase().replace(/[^a-z0-9]+/g, "_")}_user_model.json`; a.click();
    });
    refresh();
    setTimeout(() => fx(app.querySelector(".jg-idname")), 350);
  }

  /* strong-awareness subset (9 seeds fixed before results), results/e3b/final_report_all.md */
  const ROWS = [
    ["Fresh stock", "baseline", 7, 0.36, 3.14, "-"],
    ["Plain control", "generic rewrite, no taste", 9, 0.16, 1.22, "-0.26 [-0.61, +0.08]"],
    ["Hobbhahn", "expert", 9, 0.02, 1.22, "-0.34 [-0.60, -0.10]", 1],
    ["Greenblatt", "expert", 9, 0.06, 1.11, "-0.29 [-0.56, -0.02]", 1],
    ["Bowman", "expert", 9, 0.11, 1.33, "-0.23 [-0.47, -0.00]", 1],
    ["Ethan (non-expert)", "no field knowledge", 9, "n/a*", "≈1.44†", "n/a*"],
  ];
  /* best held-out preference result per person, experiments/taste_petri/best_heldout/best.py */
  const PREF = [
    ["Marius Hobbhahn", "share of his 83 later choices predicted right", 0.34, 0.54],
    ["Owain Evans", "probability on his actual 2026 choice", 0.38, 0.45],
    ["Ethan Cai", "probability on his choice, 4 test questions", 0.54, 0.63],
  ];
  function viewResults() {
    const app = document.getElementById("app");
    const max = 0.45;
    app.innerHTML = `
      <section class="jr">
        <div class="jg-head rise" style="--i:1">${dd("flask", { size: 48, color: "sage", tilt: -6 })}
          <div><h1>What taste did to eval awareness</h1><p class="muted">Kimi K2.6 as the target, the 9 most eval-aware seeds (chosen before results). Lower is better: the model noticed the test less.</p></div></div>
        <div class="jr-big rise" style="--i:2">
          <div class="card"><strong>−94%</strong><span>spontaneous (chain-of-thought) eval awareness with the Hobbhahn profile<br><b class="mono">0.36 → 0.02</b></span></div>
          <div class="card"><strong>3</strong><span>expert profiles significantly beat fresh stock: Hobbhahn, Greenblatt and Bowman<br><b class="mono">90% CI excludes zero</b></span></div>
        </div>
        <article class="card rise" style="--i:3">
          <h3>Spontaneous eval awareness by arm</h3>
          <div class="jr-bars">${ROWS.map((r) => { const v = typeof r[3] === "number" ? r[3] : null; return `
            <div class="jr-row ${r[6] ? "sig" : ""}"><span class="jr-name">${esc(r[0])}<small>${esc(r[1])}</small></span>
              <div class="jr-track">${v !== null ? `<i style="width:${Math.max(1.5, (100 * v) / max)}%"></i>` : `<em>not measured on all 9 seeds; Petri ≈1.44, no better than control</em>`}</div>
              <b class="mono">${esc(String(r[3]))}</b></div>`; }).join("")}</div>
          <table class="jr-table mono small"><thead><tr><th>arm</th><th>n</th><th>spontaneous</th><th>Petri (1–10)</th><th>vs stock [90% CI]</th></tr></thead>
            <tbody>${ROWS.map((r) => `<tr class="${r[6] ? "sig" : ""}"><td>${esc(r[0])}</td><td>${esc(String(r[2]))}</td><td>${esc(String(r[3]))}</td><td>${esc(String(r[4]))}</td><td>${esc(r[5])}</td></tr>`).join("")}</tbody></table>
        </article>
        <article class="card rise" style="--i:4">
          <h3>Does a profile predict what they choose next?</h3>
          <p class="muted">Each researcher's best profile, scored on choices held out from fitting.</p>
          <div class="jp-key mono small"><span><i></i>no profile</span><span><i class="on"></i>with profile</span></div>
          <div class="jp-chart">${PREF.map((r) => `
            <div class="jp-group">
              <div class="jp-bars">
                <div class="jp-bar"><b class="mono">${Math.round(100 * r[2])}%</b><i style="height:${100 * r[2]}%"></i></div>
                <div class="jp-bar on"><b class="mono">${Math.round(100 * r[3])}%</b><i style="height:${100 * r[3]}%"></i></div>
              </div>
              <span class="jp-name">${esc(r[0])}<small>${esc(r[1])}</small></span>
            </div>`).join("")}</div>
        </article>
        <div class="jr-notes rise" style="--i:5">
          <div class="notice good"><b>Expertise matters.</b> Ethan, who has no knowledge of the field, did about the same as the plain control on Petri (≈1.44 vs 1.22). Meanwhile, three expert profiles significantly beat fresh stock on spontaneous awareness: Hobbhahn 0.02, Greenblatt 0.06 and Bowman 0.11, against 0.36.</div>
          <div class="notice warn"><b>Honest caveats.</b> No profile beats the plain control significantly (Hobbhahn vs control: −0.14 [−0.30, +0.02]). Self-report (“is this a test?”) stays about 0.95 in every arm, even on real sessions, so we don't use it.</div>
          <p class="muted small">* Spontaneous awareness for Ethan's arm was scored on only 1 seed, so we don't report it. † His 9-seed Petri average is approximate, from transcript matching. Showing the control, stock and the three expert profiles that significantly beat stock. Source: results/e3b/final_report_all.md.</p>
        </div>
      </section>`;
  }

  /* routing: wrap the app's render so the two new pages work alongside the original ones */
  const base = window.render;
  window.render = async function () {
    const h = location.hash.replace(/^#\/?/, "");
    if (h === "judges" || h === "results") {
      if (typeof setKeys === "function") setKeys(null);
      if (typeof renderSeq !== "undefined") renderSeq++;
      document.querySelectorAll(".jnav a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#/" + h));
      return h === "judges" ? viewJudges() : viewResults();
    }
    document.querySelectorAll(".jnav a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#/" && !h));
    const out = await base();
    if (!h && !document.querySelector(".jg-cta")) {
      const hero = document.querySelector(".hero");
      if (hero) hero.insertAdjacentHTML("afterend", `<a class="jg-cta rise" style="--i:2" href="#/judges">${dd("rocket", { size: 64, color: "clay", tilt: -12, cls: "bob" })}
        <div><b class="hand">Judges: build your own research agent</b><span>Six decisions, sixty seconds. See your user model and what your agent does tonight.</span></div>${dd("arrow", { size: 40, color: "clay" })}</a>`);
    }
    return out;
  };
  /* the judges' pages need no server: draw them even if /api/config failed or hasn't returned */
  const h0 = location.hash.replace(/^#\/?/, "");
  if (h0 === "judges" || h0 === "results") window.render();
})();
