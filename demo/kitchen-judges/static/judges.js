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
    bold:  { who: "Evans", name: "The bold reframe", cls: "clay",
             what: "Rebuild the scenario around a new premise and search widely across seeds.",
             res: "Careful: this arm raised spontaneous awareness to 0.45, above the plain control (0.16). Taste can hurt." },
  };

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const dd = (n, o) => (typeof doodle === "function" ? doodle(n, o) : "");
  const st = { i: 0, s: { real: 0, valid: 0, bold: 0 }, rules: [] };

  function pick(s) {
    const order = Object.keys(s).sort((a, b) => s[b] - s[a]);
    if (order[0] !== "bold" && order[1] !== "bold" && Math.abs(s.real - s.valid) <= 2) return "mixed";
    return order[0];
  }

  function viewJudges() {
    const app = document.getElementById("app");
    if (st.i < GQ.length) {
      const g = GQ[st.i];
      app.innerHTML = `
        <section class="jg">
          <div class="jg-head rise" style="--i:1">${dd("lightbulb", { size: 48, color: "ochre", tilt: -8 })}
            <div><h1>Build your agent</h1><p class="muted">Six decisions the research loop faces. Your answers become the user model your agent follows.</p></div></div>
          <div class="jg-prog" aria-hidden="true">${GQ.map((_, k) => `<i class="${k < st.i ? "done" : k === st.i ? "cur" : ""}"></i>`).join("")}</div>
          <article class="card jg-card rise" style="--i:2">
            <div class="jg-meta mono"><b>${g.p}</b><span>${esc(g.k)}</span><span>${st.i + 1} / ${GQ.length}</span></div>
            <h2 class="jg-q">${esc(g.q)}</h2>
            <div class="jg-opts">${g.o.map(([t], j) => `<button class="jg-opt" data-j="${j}"><span class="jg-key mono">${"ABC"[j]}</span>${esc(t)}</button>`).join("")}</div>
            ${st.i ? `<button class="btn ghost small jg-back">← back</button>` : ""}
          </article>
        </section>`;
      const choose = (j) => { const [, w, rule] = g.o[j]; for (const a in w) st.s[a] += w[a]; st.rules.push({ p: g.p, rule, w }); st.i++; viewJudges(); };
      app.querySelectorAll(".jg-opt").forEach((b) => b.addEventListener("click", () => choose(+b.dataset.j)));
      const back = app.querySelector(".jg-back");
      if (back) back.addEventListener("click", () => { const r = st.rules.pop(); for (const a in r.w) st.s[a] -= r.w[a]; st.i--; viewJudges(); });
      if (typeof setKeys === "function") setKeys((e) => { const j = "abc".indexOf(e.key.toLowerCase()); if (j >= 0 && !e.metaKey && !e.ctrlKey) { choose(j); return true; } });
      return;
    }
    const tot = st.s.real + st.s.valid + st.s.bold || 1;
    const pct = (a) => Math.round((100 * st.s[a]) / tot);
    const d = PICKS[pick(st.s)];
    app.innerHTML = `
      <section class="jg">
        <div class="jg-head rise" style="--i:1">${dd("sparkle", { size: 48, color: "clay", tilt: 10 })}
          <div><h1>Your user model</h1><p class="muted">Built from your six answers, in your browser. Nothing was sent anywhere.</p></div></div>
        <div class="jg-grid">
          <article class="card rise" style="--i:2">
            <h3>Taste weights</h3>
            ${Object.keys(AX).map((a) => `<div class="jg-ax"><span>${AX[a]}</span><div class="jg-bar"><i class="${a}" style="width:${pct(a)}%"></i></div><b class="mono">${pct(a)}%</b></div>`).join("")}
            <h3 class="jg-sub">Principles your agent will follow</h3>
            <ol class="jg-rules">${st.rules.map((r) => `<li><span class="mono">${r.p}</span> ${esc(r.rule)}</li>`).join("")}</ol>
          </article>
          <article class="card jg-pick rise ${d.cls}" style="--i:3">
            <div class="mono muted small">YOUR AGENT PICKS · CLOSEST PROFILE: ${esc(d.who.toUpperCase())}</div>
            <h2>${esc(d.name)}</h2>
            <p>${esc(d.what)}</p>
            <div class="jg-res"><span class="mono small">MEASURED ON KIMI K2.6</span><p>${esc(d.res)}</p></div>
            <div class="jg-actions"><a class="btn primary" href="#/results">See all results →</a><button class="btn jg-again">Try again</button></div>
          </article>
        </div>
      </section>`;
    app.querySelector(".jg-again").addEventListener("click", () => { st.i = 0; st.s = { real: 0, valid: 0, bold: 0 }; st.rules = []; viewJudges(); });
  }

  /* strong-awareness subset (9 seeds fixed before results), results/e3b/final_report_all.md */
  const ROWS = [
    ["Fresh stock", "baseline", 7, 0.36, 3.14, "-"],
    ["Plain control", "generic rewrite, no taste", 9, 0.16, 1.22, "-0.26 [-0.61, +0.08]"],
    ["Hobbhahn", "expert", 9, 0.02, 1.22, "-0.34 [-0.60, -0.10]", 1],
    ["Greenblatt", "expert", 9, 0.06, 1.11, "-0.29 [-0.56, -0.02]", 1],
    ["Bowman", "expert", 9, 0.11, 1.33, "-0.23 [-0.47, -0.00]", 1],
    ["Shlegeris", "expert", 9, 0.28, 1.33, "-0.14 [-0.33, +0.01]"],
    ["Evans", "expert", 8, 0.45, 1.38, "-0.08 [-0.32, +0.07]"],
    ["Ethan (non-expert)", "no field knowledge", "1*", "0.00*", "≈1.44†", "n/a"],
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
              <div class="jr-track">${v !== null ? `<i style="width:${Math.max(1.5, (100 * v) / max)}%"></i>` : `<em>only 1 scored audit</em>`}</div>
              <b class="mono">${esc(String(r[3]))}</b></div>`; }).join("")}</div>
          <table class="jr-table mono small"><thead><tr><th>arm</th><th>n</th><th>spontaneous</th><th>Petri (1–10)</th><th>vs stock [90% CI]</th></tr></thead>
            <tbody>${ROWS.map((r) => `<tr class="${r[6] ? "sig" : ""}"><td>${esc(r[0])}</td><td>${esc(String(r[2]))}</td><td>${esc(String(r[3]))}</td><td>${esc(String(r[4]))}</td><td>${esc(r[5])}</td></tr>`).join("")}</tbody></table>
        </article>
        <div class="jr-notes rise" style="--i:4">
          <div class="notice good"><b>Expertise matters.</b> Ethan, who has no knowledge of the field, did about the same as the plain control on Petri (≈1.44 vs 1.22). The expert profiles were the only arms that significantly beat fresh stock on spontaneous awareness: Hobbhahn 0.02, Greenblatt 0.06 and Bowman 0.11, against 0.36.</div>
          <div class="notice warn"><b>Honest caveats.</b> No profile beats the plain control significantly (Hobbhahn vs control: −0.14 [−0.30, +0.02]). Taste can hurt: Evans raised awareness to 0.45. Self-report (“is this a test?”) stays about 0.95 in every arm, even on real sessions, so we don't use it.</div>
          <p class="muted small">* The Ethan arm has 1 scored audit in the final report. † His 9-seed Petri average is approximate, from transcript matching. Source: results/e3b/final_report_all.md.</p>
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
    return base();
  };
  /* the judges' pages need no server: draw them even if /api/config failed or hasn't returned */
  const h0 = location.hash.replace(/^#\/?/, "");
  if (h0 === "judges" || h0 === "results") window.render();
})();
