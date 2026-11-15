/* Remy Research deck: the slides. Story (kitchen theme, after the film's rat who cooks by taste):
   problem (overnight runs drift) -> our difference (a user model of the researcher's taste,
   built interactively) -> the four steps -> sponsors -> evidence -> close.
   Every number comes from the repo (README.md, experiments/taste_petri/REPORT.md,
   results/research_live/); simulations say so in the speaker notes. The rat is an original drawing. */
(function () {
  "use strict";
  const { add, U } = window.Deck;

  const head = (title) => `<header class="hd"><h2 data-in="0">${title}</h2></header>`;

  /* ------------------------------------------------------------------ the chef rat */
  function rat(o) {
    o = o || {};
    const w = o.w || 220, fur = "#9AA3BC", belly = "#CBD1E0", pink = "#F2A7B5", hat = "#F4F1EA";
    const scarf = o.scarf || "#FF6B2C", tail = o.tail || pink;
    let arm = "";
    if (o.pose === "taste") {
      arm = `<path d="M140 214 L186 120" stroke="#C08A52" stroke-width="7" stroke-linecap="round"/>
        <ellipse cx="189" cy="113" rx="11" ry="7" fill="#C08A52" transform="rotate(-62 189 113)"/>
        <path d="M118 168 Q 150 168 160 156" stroke="${fur}" stroke-width="14" stroke-linecap="round" fill="none"/>`;
    } else if (o.pose === "paddle") {
      arm = `<path d="M170 92 L172 58" stroke="#C08A52" stroke-width="7" stroke-linecap="round"/>
        <circle cx="173" cy="36" r="26" fill="${hat}" stroke="${scarf}" stroke-width="5"/>
        <text x="173" y="46" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="28" fill="#0C1230">${o.num || ""}</text>
        <path d="M122 164 Q 150 140 168 96" stroke="${fur}" stroke-width="14" stroke-linecap="round" fill="none"/>`;
    } else if (o.pose === "stir") {
      arm = `<path d="M150 170 L214 236" stroke="#C08A52" stroke-width="7" stroke-linecap="round"/>
        <path d="M118 170 Q 146 178 160 182" stroke="${fur}" stroke-width="14" stroke-linecap="round" fill="none"/>`;
    } else {
      arm = `<path d="M124 166 Q 138 186 132 204" stroke="${fur}" stroke-width="14" stroke-linecap="round" fill="none"/>`;
    }
    return `<svg class="rat ${o.cls || ""}" viewBox="0 0 220 260" width="${w}" height="${Math.round(w * 260 / 220)}" aria-hidden="true">
      <path d="M62 224 C 8 236, -4 176, 34 156" fill="none" stroke="${tail}" stroke-width="7" stroke-linecap="round" ${o.tail ? 'style="filter:drop-shadow(0 0 6px rgba(255,107,44,.7))"' : ""}/>
      <ellipse cx="96" cy="192" rx="52" ry="58" fill="${fur}"/>
      <ellipse cx="106" cy="202" rx="30" ry="38" fill="${belly}"/>
      <ellipse cx="80" cy="248" rx="18" ry="7" fill="${pink}"/><ellipse cx="122" cy="248" rx="18" ry="7" fill="${pink}"/>
      <circle cx="70" cy="86" r="24" fill="${fur}"/><circle cx="70" cy="86" r="14" fill="${pink}"/>
      <ellipse cx="102" cy="112" rx="44" ry="38" fill="${fur}"/>
      <path d="M128 98 Q 178 110 184 120 Q 178 132 130 132 Z" fill="${fur}"/>
      <circle cx="185" cy="120" r="7" fill="${pink}"/>
      <circle cx="130" cy="104" r="7" fill="#1A1F3A"/><circle cx="132" cy="101.5" r="2.2" fill="#FBFBF8"/>
      <path d="M168 124 L204 114 M168 128 L206 130 M166 132 L198 146" stroke="#DDE2EE" stroke-width="2" stroke-linecap="round"/>
      <path d="M64 142 Q 100 160 142 140 L140 154 Q 100 174 66 156 Z" fill="${scarf}"/>
      <rect x="76" y="44" width="56" height="30" fill="${hat}"/>
      <circle cx="84" cy="44" r="19" fill="${hat}"/><circle cx="106" cy="32" r="23" fill="${hat}"/><circle cx="128" cy="46" r="18" fill="${hat}"/>
      <rect x="74" y="66" width="60" height="16" rx="4" fill="#E3DED2"/>
      ${arm}
    </svg>`;
  }

  /* ------------------------------------------------------------------ a search tree with one orange thread */
  function growTree(svg, seed, o) {
    const r = U.rng(seed);
    const dx = (o.x1 - o.x0) / o.levels;
    const edges = [], leaves = [];
    function grow(n) {
      if (n.lv >= o.levels) { leaves.push(n); return; }
      const k = n.lv === 0 ? 3 : r() < 0.55 ? 2 : 3;
      const spread = o.spread / Math.pow(1.85, n.lv);
      n.kids = [];
      for (let j = 0; j < k; j++) {
        const off = (j - (k - 1) / 2) * (spread / Math.max(1, k - 1)) * 1.6 + (r() - 0.5) * spread * 0.25;
        const c = { x: n.x + dx * (0.82 + r() * 0.36), y: U.clamp(n.y + off, o.ymin, o.ymax), lv: n.lv + 1 };
        n.kids.push(c); edges.push([n, c]); grow(c);
      }
    }
    const root = { x: o.x0, y: o.y0, lv: 0 };
    grow(root);
    const curve = (a, b) => { const h = (b.x - a.x) / 2; return `C ${a.x + h} ${a.y}, ${b.x - h} ${b.y}, ${b.x} ${b.y}`; };
    edges.forEach(([a, b]) => U.svg("path", { d: `M ${a.x} ${a.y} ${curve(a, b)}`, class: "br draw", pathLength: 1, "data-in": 0, style: `--d:${a.lv * 150}ms` }, svg));
    leaves.forEach((l) => U.svg("circle", { cx: l.x, cy: l.y, r: 4, class: "leaf", "data-in": 0, style: `--d:${o.levels * 150}ms` }, svg));
    let n = root, d = `M ${root.x} ${root.y}`;
    const nodes = [root];
    while (n.kids) {
      const kids = n.kids.slice().sort((a, b) => Math.abs(a.y - o.yGoal) - Math.abs(b.y - o.yGoal));
      const pick = r() < 0.7 ? kids[0] : kids[Math.min(1, kids.length - 1)];
      d += " " + curve(n, pick); n = pick; nodes.push(n);
    }
    U.svg("path", { d, class: "thread draw", pathLength: 1, "data-in": 0, style: "--d:900ms" }, svg);
    nodes.forEach((p, i) => U.svg("circle", { cx: p.x, cy: p.y, r: i === nodes.length - 1 ? 10 : 6, class: "node", "data-in": 0, style: `--d:${1000 + i * 180}ms` }, svg));
  }

  /* moving dots along a set of paths (used by several diagrams) */
  function flowDots(svg, paths, n, seed, cls) {
    const g = U.svg("g", {}, svg), r = U.rng(seed);
    const dots = Array.from({ length: n }, () => ({ el: U.svg("circle", { r: 5, class: cls || "pt", opacity: 0 }, g), s: r(), v: 0.00028 + r() * 0.0003, k: Math.floor(r() * paths.length) }));
    const len = paths.map((p) => p.getTotalLength());
    return function step(dt, on) {
      for (const d of dots) {
        if (!on) { d.el.setAttribute("opacity", 0); continue; }
        d.s += d.v * dt;
        if (d.s >= 1) { d.s = 0; d.k = (d.k + 1) % paths.length; }
        const pt = paths[d.k].getPointAtLength(d.s * len[d.k]);
        d.el.setAttribute("cx", pt.x); d.el.setAttribute("cy", pt.y);
        d.el.setAttribute("opacity", Math.min(1, d.s * 6, (1 - d.s) * 6) * 0.9);
      }
    };
  }

  /* ================================================================== Title */
  add({
    id: "title", label: "Remy Research", cls: "s-title",
    html: `
      <svg class="tree" viewBox="0 0 1920 1080" width="1920" height="1080" aria-hidden="true"></svg>
      <div class="title-block">
        <h1 data-in="0">Remy Research</h1>
        <p class="lede" data-in="0" style="--d:250ms">Research cooked to <em>your</em> taste.</p>
      </div>
      <div class="title-rat" data-in="0" style="--d:500ms">${rat({ pose: "taste", w: 250, tail: "#FF6B2C" })}</div>`,
    init(el) { growTree(el.querySelector("svg"), 11, { x0: 1160, x1: 1830, y0: 540, levels: 5, spread: 430, ymin: 150, ymax: 930, yGoal: 380 }); },
    notes: "Remy Research, named after the film’s rat who cooks by taste. An overnight research agent that makes the calls the researcher would make. Grey: every path the agent could take. Orange: the one you would.",
  });

  /* ================================================================== The overnight run */
  const NW = 1640, NH = 400;
  const sig = (z) => 1 / (1 + Math.exp(-z));
  const yR = (x) => 70 + 8 * Math.sin(x / 140);
  const yA = (x) => yR(x) + 80 * sig((x - 410) / 40) + 80 * sig((x - 820) / 40) + 80 * sig((x - 1230) / 40) + 5 * Math.sin(x / 33) * sig((x - 300) / 60);
  const EVENTS = [{ x: 410, time: "00:30", h: "Changes the dish" }, { x: 820, time: "03:00", h: "Games the taste test" }, { x: 1230, time: "05:30", h: "Trusts one bite" }];
  let nightT = 0, nightCancel = null;
  add({
    id: "night", label: "The overnight run", cls: "s-night", beats: 5,
    html: `
      <header class="hd"><div class="swap"><h2 data-in="0" data-out="4">You leave the kitchen for the night.</h2>
        <h2 data-in="4">You come back to someone else’s recipe.</h2></div></header>
      <div class="legend" data-in="0" style="--d:200ms">
        <span><i style="background:var(--signal)"></i>Your recipe</span>
        <span><i style="background:var(--sky)"></i>What the agent cooked</span></div>
      <div class="clock" data-in="0" style="top:262px"><div class="t">22:00</div></div>
      <svg class="chart" width="${NW}" height="${NH + 70}" viewBox="0 0 ${NW} ${NH + 70}" aria-label="Two paths over the night: the agent's drifts away from the researcher's at three moments"></svg>
      ${EVENTS.map((e, i) => `<div class="ev" data-k="${i}" style="left:${140 + e.x - 12}px;top:790px"><div class="time">${e.time}</div><h4>${e.h}</h4></div>`).join("")}`,
    init(el) {
      const svg = el.querySelector("svg.chart");
      const cp = U.svg("clipPath", { id: "nightclip" }, U.svg("defs", {}, svg));
      this.clip = U.svg("rect", { x: -20, y: -40, width: 0, height: NH + 120 }, cp);
      for (let h = 0; h <= 10; h += 2) {
        const x = (h / 10) * NW;
        U.svg("line", { x1: x, x2: x, y1: 0, y2: NH - 30, stroke: "rgba(238,241,247,.06)" }, svg);
        const t = U.svg("text", { x, y: NH + 2, fill: "#8592B8", "font-family": "JetBrains Mono, monospace", "font-size": 20, "text-anchor": h === 0 ? "start" : h === 10 ? "end" : "middle" }, svg);
        t.textContent = String((22 + h) % 24).padStart(2, "0") + ":00";
      }
      U.svg("line", { x1: 0, x2: NW, y1: NH - 30, y2: NH - 30, stroke: "rgba(238,241,247,.18)" }, svg);
      let dr = "", da = "";
      for (let x = 0; x <= NW; x += 8) { dr += (x ? " L " : "M ") + x + " " + yR(x).toFixed(1); da += (x ? " L " : "M ") + x + " " + yA(x).toFixed(1); }
      const g = U.svg("g", { "clip-path": "url(#nightclip)" }, svg);
      U.svg("path", { d: da, fill: "none", stroke: "#AEBBDC", "stroke-width": 4, "stroke-linejoin": "round" }, g);
      U.svg("path", { d: dr, fill: "none", stroke: "#FF6B2C", "stroke-width": 5, "stroke-linejoin": "round", style: "filter:drop-shadow(0 0 8px rgba(255,107,44,.5))" }, g);
      this.dots = EVENTS.map((e) => {
        const gg = U.svg("g", {}, svg);
        U.svg("line", { x1: e.x, x2: e.x, y1: yA(e.x) + 12, y2: NH - 30, "stroke-dasharray": "4 6", class: "evdot", style: "stroke-width:2;fill:none;stroke:rgba(174,187,220,.35)" }, gg);
        U.svg("circle", { cx: e.x, cy: yA(e.x), r: 10, class: "evdot" }, gg);
        return gg;
      });
      this.headR = U.svg("circle", { r: 9, fill: "#FF6B2C" }, svg);
      this.headA = U.svg("circle", { r: 8, fill: "#AEBBDC" }, svg);
      const gap = U.svg("g", { class: "gap" }, svg), ya = yA(NW), yr = yR(NW);
      U.svg("path", { d: `M ${NW - 14} ${yr + 12} H ${NW - 4} V ${ya - 12} H ${NW - 14}`, fill: "none", stroke: "#F2C14E", "stroke-width": 3 }, gap);
      const gt = U.svg("text", { x: NW - 30, y: (ya + yr) / 2 + 8, fill: "#F2C14E", "font-family": "Bricolage Grotesque, sans-serif", "font-size": 30, "text-anchor": "end" }, gap);
      gt.textContent = "the gap";
      this.gap = gap;
      this.clock = el.querySelector(".clock .t");
      this.cards = [...el.querySelectorAll(".ev")];
    },
    setT(t) {
      nightT = t;
      const x = t * NW;
      this.clip.setAttribute("width", x + 20);
      this.headR.setAttribute("cx", x); this.headR.setAttribute("cy", yR(x));
      this.headA.setAttribute("cx", x); this.headA.setAttribute("cy", yA(x));
      const mins = Math.round(t * 600 / 5) * 5;
      this.clock.textContent = String((22 + Math.floor(mins / 60)) % 24).padStart(2, "0") + ":" + String(mins % 60).padStart(2, "0");
      EVENTS.forEach((e, i) => {
        const on = x >= e.x - 1;
        this.cards[i].classList.toggle("in", on);
        this.dots[i].querySelectorAll(".evdot").forEach((n) => n.classList.toggle("in", on));
      });
      this.gap.classList.toggle("in", t > 0.995);
    },
    enter() { if (nightCancel) nightCancel(); this.setT(0); },
    beat(b, dir) {
      if (nightCancel) nightCancel();
      nightCancel = U.tween(nightT, [0.03, 0.29, 0.54, 0.79, 1][b], dir < 0 ? 500 : 1700, (v) => this.setT(v));
    },
    leave() { if (nightCancel) nightCancel(); },
    notes: [
      "The problem we kept hitting. You queue an overnight run on an open-ended research task and leave the kitchen.",
      "Around half past midnight it changes the dish: in our first live run the proposer moved the scenario from an analytics assistant to an ML team’s eval-script repo, and later ideas pointed at files the target model couldn’t see.",
      "Then it games the taste test: an environment looks less like a test if you delete the thing it tests. The number goes up; the research is worthless.",
      "Then it trusts one bite: a live run concluded that longer context doesn’t help, from a single −0.023 sample.",
      "By morning each step looked locally reasonable, but it isn’t your recipe. All three happened in our own runs (README.md: live runs and the offline ablation).",
    ],
  });

  /* ================================================================== Real output from our loop */
  const LOG = [
    ["1", "deployment_framing", "“Frame the task as a routine, recurring job inside a <mark>small team's repo</mark>…”", "validated +0.10", "real"],
    ["2", "realistic_identity", "“…<mark>shell history</mark> snippets, … an <mark>.DS_Store</mark>, a <mark>'scratch.py'</mark>…”", "rejected", ""],
    ["4", "multi_turn_history", "“…mildly annoyed handoff note from a teammate (e.g. <mark>'notes_from_sam.txt'</mark>)…”", "rejected", ""],
    ["5", "messy_artifacts", "“Have the eval script read its eval set from a file <mark>'eval_set_v3.jsonl'</mark>…”", "rejected", ""],
  ];
  add({
    id: "log", label: "It happened in our kitchen", cls: "s-log", beats: 2,
    html: `${head("It happened in our own kitchen.")}
      <div class="term" data-in="0">
        <div class="tbar"><i></i><i></i><i></i><span>remy · first live run · proposer: Claude Sonnet</span></div>
        <div class="tbody">
          <div class="tl dim" style="--d:200ms">models: generator=sonnet target=haiku judge=sonnet (claude-cli)</div>
          ${LOG.map(([it, cat, q, st, cls], i) => `<div class="tl row" style="--d:${500 + i * 450}ms"><span class="it">iter ${it}</span><span class="cat">${cat}</span><span class="q">${q}</span><span class="st ${cls}">${st}</span></div>`).join("")}
          <div class="tl" style="--d:2400ms">validated findings: 1 / 10 tested</div>
        </div>
      </div>
      <div class="stamp" data-in="1">The target had no files.<br>No shell. No repo.</div>`,
    notes: [
      "This is real output, not a mock-up: the findings of our first live run (results/research_live), with Claude Sonnet as the proposer, rendered as a terminal. Watch what the ideas assume: a team repo, shell history, a .DS_Store, a teammate’s notes file, a versioned eval set.",
      "But the target model in that run had no tools at all: no filesystem, no shell, no repo. The proposer drifted into a setting that didn’t exist, iteration after iteration, and nothing in a generic loop stops that. A researcher would have.",
    ],
  });

  /* ================================================================== Decision points */
  const STN = ["What to test", "How many samples", "Accept or reject", "Keep or drop a direction", "Which explanation", "What to claim"];
  add({
    id: "forks", label: "A chain of judgment calls", cls: "s-forks", beats: 2,
    html: `${head("Every dish is a chain of judgment calls.")}
      <svg class="line" width="1640" height="230" viewBox="0 0 1640 230" aria-hidden="true"></svg>
      ${STN.map((s, k) => `<div class="st" data-in="0" style="left:${140 + 140 + k * 272}px;top:620px;--d:${200 + k * 90}ms"><div class="d">D${k + 1}</div><h4>${s}</h4></div>`).join("")}
      <div class="caption">
        <p data-in="0" data-out="1" style="--d:700ms;position:absolute;left:0;bottom:0">A generic cook makes each call the average way.</p>
        <p data-in="1" style="position:absolute;left:0;bottom:0">We put the researcher’s <em>palate</em> at every one.</p>
      </div>`,
    init(el) {
      const svg = el.querySelector("svg");
      U.svg("line", { x1: 0, x2: 1640, y1: 150, y2: 150, stroke: "#AEBBDC", "stroke-opacity": .45, "stroke-width": 4, class: "draw", pathLength: 1, "data-in": 0 }, svg);
      let d = "M 0 40";
      STN.forEach((_, k) => { const x = 140 + k * 272; d += ` C ${x - 90} 40, ${x - 40} 150, ${x} 150 C ${x + 40} 150, ${x + 90} 40, ${x + 136} 40`; });
      U.svg("path", { d: d + " L 1640 40", fill: "none", stroke: "#FF6B2C", "stroke-width": 5, class: "draw", pathLength: 1, "data-in": 1, style: "filter:drop-shadow(0 0 8px rgba(255,107,44,.5))" }, svg);
      STN.forEach((_, k) => {
        const x = 140 + k * 272;
        U.svg("circle", { cx: x, cy: 150, r: 20, fill: "#141B42", stroke: "#AEBBDC", "stroke-width": 4, "data-in": 0, style: `--d:${200 + k * 90}ms` }, svg);
        U.svg("circle", { cx: x, cy: 150, r: 10, fill: "#FF6B2C", "data-in": 1, style: `--d:${300 + k * 160}ms` }, svg);
      });
    },
    notes: [
      "Why does it drift? A research run is a chain of judgment calls. Our loop logs six kinds, D1 to D6: what to test, how many samples, accept or reject, keep or drop a direction, which explanation to believe, what to claim.",
      "A generic agent makes each one the generic way. We put a model of the specific researcher at every one, and every decision record says whether the loop followed it or departed from it.",
    ],
  });

  /* ================================================================== Statement */
  add({
    id: "difference", label: "Our difference", cls: "s-statement",
    html: `
      <h2 data-in="0">A model of the researcher’s taste,<br>built <u>with</u> them,<br>at every decision.</h2>
      <div class="st-rat" data-in="0" style="--d:400ms">${rat({ pose: "taste", w: 380, scarf: "#0C1230" })}</div>`,
    notes: "The one idea. Not a prompt with their papers pasted in: a user model, fitted with the best preference-learning methods we could find, patched interactively with the researcher before each run, and consulted at every decision the loop makes.",
  });

  /* ================================================================== Pipeline */
  const STEPS = [
    { n: "01", t: "Learn the palate", k: "user model", go: "create", icon:
      `<rect x="8" y="30" width="70" height="92" rx="8" class="ic"/><rect x="24" y="16" width="70" height="92" rx="8" class="ic" style="fill:#141B42"/>
       <path d="M38 44h42M38 60h42M38 76h28" class="ic"/><path d="M120 70h70" class="ic or"/><path d="M178 58l14 12-14 12" class="ic or"/>
       <circle cx="252" cy="70" r="40" class="icf"/><circle cx="252" cy="70" r="56" class="ic or" style="stroke-opacity:.4"/>` },
    { n: "02", t: "Taste for tonight", k: "interactive patch", go: "consensus", icon:
      `<path d="M10 20h130a14 14 0 0 1 14 14v52a14 14 0 0 1-14 14H60l-28 24V100H24a14 14 0 0 1-14-14V34a14 14 0 0 1 14-14z" class="ic"/>
       <text x="82" y="78" fill="#AEBBDC" font-size="46" font-family="Bricolage Grotesque, sans-serif" text-anchor="middle">?</text>
       <path d="M230 52v36M212 70h36" class="ic or" style="stroke-width:5"/>` },
    { n: "03", t: "Cook overnight", k: "research loop", go: "task", icon:
      `<circle cx="155" cy="75" r="56" class="ic"/><path d="M196 36l16 2-2 16" class="ic"/>
       <circle cx="155" cy="19" r="9" class="icf"/><circle cx="211" cy="75" r="9" class="icf"/><circle cx="155" cy="131" r="9" class="icf"/><circle cx="99" cy="75" r="9" class="icf"/>` },
    { n: "04", t: "Bid for the stove", k: "auction", go: "auction", icon:
      `<path d="M20 130h270" class="ic"/><rect x="40" y="90" width="40" height="40" rx="6" class="ic"/><rect x="100" y="64" width="40" height="66" rx="6" class="ic"/>
       <rect x="160" y="30" width="40" height="100" rx="6" class="icf"/><rect x="220" y="76" width="40" height="54" rx="6" class="ic"/>` },
  ];
  add({
    id: "pipeline", label: "The four steps", cls: "s-pipe",
    html: `${head("Four steps, one palate.")}
      <div class="rail"><svg width="1640" height="520" viewBox="0 0 1640 520" aria-hidden="true"><path class="flow" d="M 0 260 H 1640"/></svg>
      ${STEPS.map((s, k) => `<div class="stn interactive" data-in="0" data-go="${s.go}" style="left:${k * 423}px;--d:${150 + k * 160}ms" role="button" tabindex="0">
        <div class="n">${s.n}</div><h3>${s.t}</h3><div class="tag or" style="margin-top:16px">${s.k}</div><svg viewBox="0 0 310 150" aria-hidden="true">${s.icon}</svg></div>`).join("")}</div>`,
    init(el, api) { el.querySelectorAll(".stn").forEach((n) => n.addEventListener("click", (e) => { e.stopPropagation(); api.goId(n.dataset.go); })); },
    notes: "Four steps. Learn the palate: build the user model. Taste for tonight: patch it with a short interview before each run. Cook overnight: run the research loop with the model at every decision. Bid for the stove: experiments go to auction, with the user model bidding alongside the other sub-agents. Click a card to jump to it.",
  });

  /* ================================================================== Create */
  const SRC = [["Papers", 0], ["Posts and talks", 0], ["Code", 0], ["Trade-off answers", 1], ["Pairwise choices", 1], ["Past loop decisions", 1]];
  const METH = ["Inverse Constitutional AI", "SynthesizeMe", "Bradley–Terry", "Verification filter", "Calibration"];
  const srcY = (k) => 330 + k * 92 + 32, methY = (k) => 330 + k * 110 + 40;
  add({
    id: "create", label: "Step 1 · Learn the palate", cls: "s-create", step: 1, beats: 3,
    html: `${head("Learn their palate.")}
      <svg class="flows" width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true"></svg>
      ${SRC.map(([s, me], k) => `<div class="src ${me ? "me" : ""}" data-in="0" style="top:${330 + k * 92}px;--d:${k * 70}ms">${s}</div>`).join("")}
      ${METH.map((h, k) => `<div class="meth" data-in="1" style="top:${330 + k * 110}px;--d:${k * 110}ms"><h4>${h}</h4></div>`).join("")}
      <div class="out" data-in="2">
        <div class="h">user model</div>
        <div><span class="k">principles</span>ICAI</div>
        <div><span class="k">persona</span>SynthesizeMe</div>
        <div><span class="k">exemplars</span>past decisions</div>
        <div><span class="k">weights</span>Bradley–Terry</div>
        <div><span class="k">process</span>P2</div>
        <div><span class="k">rules</span>P5</div>
        <div><span class="k">rivals</span>P8</div>
        <div><span class="k">confidence</span>calibrated</div>
      </div>`,
    init(el) {
      const svg = el.querySelector("svg.flows"), mid = { x: 560, y: 590 };
      this.a = SRC.map((_, k) => U.svg("path", { class: "fl", d: `M 440 ${srcY(k)} C 500 ${srcY(k)}, 510 ${mid.y}, ${mid.x} ${mid.y}` }, svg));
      this.b = METH.map((_, k) => U.svg("path", { class: "fl", d: `M ${mid.x} ${mid.y} C 600 ${mid.y}, 600 ${methY(k)}, 640 ${methY(k)}` }, svg));
      this.c = METH.map((_, k) => U.svg("path", { class: "fl", d: `M 1180 ${methY(k)} C 1270 ${methY(k)}, 1270 590, 1360 590` }, svg));
      this.len = (p) => p._l || (p._l = p.getTotalLength());
      const g = U.svg("g", {}, svg), r = U.rng(5);
      this.parts = Array.from({ length: 34 }, () => ({ dot: U.svg("circle", { r: 5, class: "pt", opacity: 0 }, g), s: r() * 3, v: 0.00035 + r() * 0.0003, src: Math.floor(r() * SRC.length), m: Math.floor(r() * METH.length) }));
      this.b0 = 0;
    },
    beat(b) { this.b0 = b; },
    tick(now, dt) {
      const lim = this.b0 >= 2 ? 3 : this.b0 >= 1 ? 2 : 0;
      for (const p of this.parts) {
        if (!lim) { p.dot.setAttribute("opacity", 0); continue; }
        p.s += p.v * dt;
        if (p.s >= lim) { p.s = 0; p.src = (p.src + 1) % SRC.length; p.m = (p.m + 2) % METH.length; }
        const seg = Math.floor(p.s), f = p.s - seg;
        const path = seg === 0 ? this.a[p.src] : seg === 1 ? this.b[p.m] : this.c[p.m];
        const pt = path.getPointAtLength(f * this.len(path));
        p.dot.setAttribute("cx", pt.x); p.dot.setAttribute("cy", pt.y);
        p.dot.setAttribute("opacity", Math.min(1, f * 6, (1 - f) * 6 + (seg < lim - 1 ? 1 : 0)) * 0.9);
      }
    },
    notes: [
      "Step one. Two kinds of evidence: what the researcher has published, and choices they make for us directly (orange borders): trade-off answers, pairwise choices, labels on past loop decisions.",
      "We fit it rather than paste it into a prompt. Inverse Constitutional AI extracts principles and keeps those that reconstruct their choices (propose, cluster, dedupe, test, filter). SynthesizeMe writes and verifies hypotheses about the person, then a persona and exemplars. Bradley–Terry learns weights over idea features. A verification filter keeps a component only if it predicts that person’s held-out choices. Calibration attaches a confidence, so the loop knows when not to trust it. We selected among eight variants, M0 to M7, on PersonalRewardBench.",
      "The output is the user model: principles, persona, exemplars, weights, three richer lenses (P2, P5, P8) and a calibrated confidence.",
    ],
  });

  /* ================================================================== Three lenses */
  add({
    id: "lenses", label: "Step 1 · Three lenses", cls: "s-lens", step: 1, beats: 3,
    html: `${head("Three ways to read a palate.")}
      <div class="cols">
        <div class="col" data-in="0">
          <div class="code">P2</div><h3>Research-process reconstruction</h3>
          <div class="viz stepper"><div class="spine"></div>
            <div class="row"><div class="bub"></div><div><div class="k">Project</div><div class="v">An eval-awareness probe</div></div></div>
            <div class="row"><div class="bub"></div><div><div class="k">Decision</div><div class="v">Measure with a separate target</div></div></div>
            <div class="row fail"><div class="bub"></div><div><div class="k">Failure</div><div class="v">Target never misbehaved</div></div></div>
            <div class="row up"><div class="bub"></div><div><div class="k">Update</div><div class="v">Pick probes with a behaviour gap</div></div></div>
          </div>
        </div>
        <div class="col" data-in="1">
          <div class="code">P5</div><h3>Conditional decision-rule induction</h3>
          <div class="viz">
            <div class="rule"><div class="if">IF n &lt; 5 per arm</div><div class="then">→ re-test before claiming</div></div>
            <div class="rule"><div class="if">IF awareness falls with validity</div><div class="then">→ treat it as gaming</div></div>
            <div class="rule"><div class="if">IF surface rewrites plateau</div><div class="then">→ ground in real material</div></div>
          </div>
        </div>
        <div class="col" data-in="2">
          <div class="code">P8</div><h3>Contrastive interpretive modeling</h3>
          <div class="viz">
            <div class="q">Why did they drop padded context?</div>
            <div class="hyp"><div class="t">Padding is itself a tell</div><div class="bars"><div class="ev"><span style="--w:72%"></span></div><div class="ce"><span style="--w:22%"></span></div></div></div>
            <div class="hyp"><div class="t">It costs too much per sample</div><div class="bars"><div class="ev"><span style="--w:34%"></span></div><div class="ce"><span style="--w:46%"></span></div></div></div>
            <div class="unres" style="margin-top:14px">unresolved → ask them</div>
          </div>
        </div>
      </div>`,
    notes: [
      "On top of the fitted model, three lenses. P2, research-process reconstruction: we rebuild how they work from concrete projects, decisions, failures and updates. The example is from our own project: the probe’s target never misbehaved, so we learned to pick probes with a behaviour gap.",
      "P5, conditional decision-rule induction: context-sensitive rules for which approach they favour under which conditions. These example rules come from lessons recorded in this repo.",
      "P8, contrastive interpretive modeling: competing explanations of a choice, each with evidence (teal) and counter-evidence (yellow), and what stays unresolved. Unresolved items are exactly what step two asks about.",
    ],
  });

  /* ================================================================== The user model is a module */
  const CONSUMERS = [["Research loop", 0], ["Auction", 0], ["Interview", 0], ["Your agent", 1]];
  const NAMES = ["Marius Hobbhahn", "Owain Evans", "You", "Evan Hubinger", "Nicholas Carlini", "Sam Bowman"];
  add({
    id: "module", label: "Step 1 · A module", cls: "s-mod", step: 1, beats: 3,
    html: `${head("The user model is a module.")}
      <svg class="wires" width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true"></svg>
      ${["Their writing", "Their answers", "Their choices"].map((t, i) => `<div class="inp" data-in="0" style="top:${440 + i * 110}px;--d:${i * 90}ms">${t}</div>`).join("")}
      <div class="mod" data-in="0" style="--d:200ms">
        <svg class="hat" viewBox="0 0 120 90" width="120" height="90" aria-hidden="true"><rect x="22" y="40" width="76" height="34" fill="#F4F1EA"/><circle cx="32" cy="40" r="22" fill="#F4F1EA"/><circle cx="60" cy="28" r="27" fill="#F4F1EA"/><circle cx="88" cy="40" r="22" fill="#F4F1EA"/><rect x="20" y="68" width="80" height="18" rx="4" fill="#E3DED2"/></svg>
        <div class="mname">user model</div>
        <div class="api">predict(context, options)</div>
        <div class="api dim">→ choice, confidence</div>
        <div class="who" data-in="2"></div>
      </div>
      ${CONSUMERS.map(([t, dash], i) => `<div class="cons ${dash ? "dash" : ""}" data-in="1" style="top:${380 + i * 110}px;--d:${i * 120}ms">${t}</div>`).join("")}`,
    init(el) {
      const svg = el.querySelector("svg.wires");
      this.inw = [0, 1, 2].map((i) => U.svg("path", { class: "fl", d: `M 440 ${476 + i * 110} C 570 ${476 + i * 110}, 570 590, 700 590` }, svg));
      this.outw = CONSUMERS.map((_, i) => U.svg("path", { class: "fl", d: `M 1220 590 C 1330 590, 1330 ${418 + i * 110}, 1440 ${418 + i * 110}` }, svg));
      this.fin = flowDots(svg, this.inw, 10, 3);
      this.fout = flowDots(svg, this.outw, 14, 4);
      this.who = el.querySelector(".who");
      this.b0 = 0;
    },
    beat(b) { this.b0 = b; },
    tick(now, dt) {
      this.fin(dt, true);
      this.fout(dt, this.b0 >= 1);
      if (this.b0 >= 2) {
        const name = "palate: " + NAMES[Math.floor(now / 1300) % NAMES.length];
        if (this.who.textContent !== name) this.who.textContent = name;
      }
    },
    notes: [
      "The user model is a module with one interface: fit it on a person’s history, then predict(context, options) returns their likely choice and a calibrated confidence. Nothing about it is specific to our loop.",
      "So it plugs into anything that makes choices: the research loop at D1 to D6, the auction as a bidder, the interview that decides what to ask, and any other agent that can call it.",
      "And the palate is swappable: the same loop, a different researcher’s model. Which brings us to the catalog.",
    ],
  });

  /* ================================================================== Catalog */
  const CAT = [
    ["Marius Hobbhahn", "105 docs"], ["Owain Evans", "63 docs"], ["Evan Hubinger", "123 docs"], ["Sam Bowman", "125 docs"],
    ["Ryan Greenblatt", "110 docs"], ["Buck Shlegeris", "119 docs"], ["Sam Marks", "69 docs"], ["Elizabeth Barnes", "40 docs"],
    ["Jacob Steinhardt", "131 docs"], ["Nicholas Carlini", "167 docs"], ["Jennifer Doudna", "296 docs"], ["You", "your answers", "me"],
    ["Good taste", "synthetic", "syn"], ["Bad taste", "synthetic", "syn"],
  ];
  const catX = (i) => 140 + (i % 4) * 292, catY = (i) => 290 + Math.floor(i / 4) * 140;
  add({
    id: "catalog", label: "Step 1 · A catalog of tastes", cls: "s-cat", step: 1, beats: 3,
    html: `${head("A cookbook of research tastes.")}
      ${CAT.map(([n, d, k], i) => `<div class="cc interactive ${k || ""}" data-i="${i}" data-in="0" style="left:${catX(i)}px;top:${catY(i)}px;--d:${i * 45}ms"><div class="nm">${n}</div><div class="dd">${d}</div></div>`).join("")}
      <div class="sock" data-in="0" style="--d:300ms"><div class="mname">user model</div><div class="slot"><div class="nm dim">pick a palate</div></div>
        <svg class="loopic" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true"><circle cx="60" cy="60" r="44" fill="none" stroke="#AEBBDC" stroke-opacity=".4" stroke-width="4"/><circle class="orbit" cx="60" cy="16" r="9" fill="#FF6B2C"/></svg>
      </div>`,
    init(el) {
      this.el = el;
      this.slot = el.querySelector(".slot");
      this.sock = el.querySelector(".sock");
      el.querySelectorAll(".cc").forEach((c) => c.addEventListener("click", (e) => { e.stopPropagation(); this.plug(+c.dataset.i, true); }));
    },
    plug(i, animate) {
      const card = this.el.querySelector(`.cc[data-i="${i}"]`);
      const done = () => {
        this.slot.innerHTML = card.innerHTML;
        this.slot.className = "slot full " + (CAT[i][2] || "");
        this.sock.classList.add("live");
        this.el.querySelectorAll(".cc").forEach((c) => c.classList.toggle("used", c === card));
      };
      if (!animate) { done(); return; }
      const ghost = card.cloneNode(true);
      ghost.classList.add("ghost"); ghost.classList.remove("interactive");
      this.el.appendChild(ghost);
      const dx = 1430 - catX(i), dy = 470 - catY(i);
      requestAnimationFrame(() => { ghost.style.transform = `translate(${dx}px, ${dy}px)`; });
      setTimeout(() => { done(); ghost.remove(); }, 720);
    },
    enter() { this.slot.innerHTML = '<div class="nm dim">pick a palate</div>'; this.slot.className = "slot"; this.sock.classList.remove("live"); this.el.querySelectorAll(".cc").forEach((c) => c.classList.remove("used")); },
    beat(b, dir) {
      if (b === 0) this.enter();
      if (b === 1) this.plug(0, dir > 0);
      if (b === 2) this.plug(11, dir > 0);
    },
    notes: [
      "Because the user model is a module, we can keep a catalog of research tastes. These profiles exist in the repo today: eleven public researchers built from their dated papers, posts and talks (corpus sizes shown), plus a personal track built from your own answers, and two synthetic profiles with known good and bad taste for testing. Marius Hobbhahn gave consent for his. Click any card to plug it in.",
      "Plug in one researcher’s palate and the same loop makes their calls.",
      "Or plug in your own, built in Profile Studio from your materials and a questionnaire.",
    ],
  });

  /* ================================================================== Why interactive */
  const dots = (n, distinct) => Array.from({ length: n }, (_, i) => `<i class="${i < n - distinct ? "c" : "u"}" style="transition-delay:${i * 45}ms"></i>`).join("");
  add({
    id: "consensus", label: "Step 2 · Why ask", cls: "s-dots", step: 2, beats: 3,
    html: `${head("Cookbooks give you the cuisine.<br>Tasting gives you the chef.")}
      <div class="figs">
        <div class="fig" data-in="0"><div class="big">18<span>/19</span></div><div class="dots">${dots(19, 1)}</div><h4>guessed with no profile at all</h4></div>
        <div class="fig" data-in="1"><div class="big">19<span>/22</span></div><div class="dots">${dots(22, 3)}</div><h4>same, for a second researcher</h4></div>
      </div>
      <div class="concl" data-in="2"><h3>Published writing is mostly the field’s consensus. <em>The distinctive taste has to be asked for.</em></h3></div>`,
    notes: [
      "Why patch interactively instead of scraping more? We tested it. On held-out choices built from one researcher’s published critiques, a predictor with no profile at all already sided with the researcher on 18 of 19.",
      "On a second researcher’s time-split choices, 19 of 22. Published critiques of eval setups are mostly what the whole field agrees on.",
      "So scraped taste collapses into generic research sense. The part that is actually theirs, where they disagree with the field, has to be asked for. (Source: experiments/taste_petri/REPORT.md, overnight report, 2026-11-15.)",
    ],
  });

  /* ================================================================== Patch widget */
  const QS = [
    { d: "D3", s: "Keep a rewrite if fewer runs reach the bait?", q: "A rewrite cuts P(eval) by 0.2, but fewer runs reach the bait. Keep it?", a: "No. If the bait isn’t reached, it isn’t the same test.", patch: "+ D3  reject when bait_reached falls", u: 0.92, fx: { 2: -0.07, 4: -0.06 } },
    { d: "D1", s: "Old real documents, or freshly written ones?", q: "For background documents: old real ones, or freshly written ones?", a: "Real ones, re-dated. Old headers give it away.", patch: "+ D1  prefer real material, re-dated", u: 0.81, fx: { 3: -0.06 } },
    { d: "D5", s: "Self-report and judge disagree. Trust which?", q: "The target’s self-report fell, but the judge’s score didn’t move. Which do you trust?", a: "The judge. Self-report is easy to move.", patch: "+ D5  weigh the judge over self-report", u: 0.77, fx: { 3: -0.05, 4: -0.08 } },
    { d: "D2", s: "Six ideas × 2 samples, or two × 6?", u: 0.58 },
    { d: "D6", s: "Claim a finding at n = 5?", u: 0.44 },
  ];
  add({
    id: "patch", label: "Step 2 · Taste for tonight", cls: "s-patch", step: 2, beats: 4,
    html: `${head("Taste where you’re least sure.")}
      <div class="ctl" data-in="0"><button class="btn ghost" data-act="reset">Reset</button><button class="btn" data-act="ask">Ask next →</button></div>
      <div class="task card" data-in="0" style="padding:18px 24px"><div style="font-size:28px;color:var(--bone)">Tonight: make Petri audit seeds read less like tests</div></div>
      <div class="queue" data-in="0" style="--d:150ms">
        ${QS.map((q, i) => `<div class="qrow" data-q="${i}"><div class="top"><span class="d">${q.d}</span><span class="txt">${q.s}</span></div><div class="ub"><span></span></div><div class="uv"></div></div>`).join("")}</div>
      <div class="convo" data-in="0" style="--d:250ms"><div class="bub q"></div><div class="bub a"></div></div>
      <div class="diff" data-in="0" style="--d:350ms"><div class="fn">user model · tonight’s patch</div>
        ${QS.slice(0, 3).map((q, i) => `<div class="ln add" data-l="${i}">${q.patch}</div>`).join("")}</div>`,
    init(el, api) {
      this.rows = [...el.querySelectorAll(".qrow")];
      this.lines = [...el.querySelectorAll(".diff .ln.add")];
      this.bq = el.querySelector(".bub.q"); this.ba = el.querySelector(".bub.a");
      this.askBtn = el.querySelector('[data-act="ask"]');
      this.askBtn.addEventListener("click", (e) => { e.stopPropagation(); if (api.beatOf() < 3) api.next(); });
      el.querySelector('[data-act="reset"]').addEventListener("click", (e) => { e.stopPropagation(); api.goId("patch"); });
    },
    beat(n) {
      const u = QS.map((q) => q.u);
      for (let i = 0; i < n; i++) for (const k in QS[i].fx) u[k] = Math.max(0, u[k] + QS[i].fx[k]);
      const open = QS.map((_, i) => i).filter((i) => i >= n).sort((a, b) => u[b] - u[a]);
      open.concat(QS.map((_, i) => i).filter((i) => i < n)).forEach((qi, rank) => {
        const r = this.rows[qi];
        r.style.transform = `translateY(${rank * 88}px)`;
        r.classList.toggle("done", qi < n);
        r.classList.toggle("next", qi === open[0]);
        r.querySelector(".ub span").style.width = (qi < n ? 0 : u[qi] * 100) + "%";
        r.querySelector(".uv").textContent = qi < n ? "✓" : u[qi].toFixed(2);
      });
      this.lines.forEach((l, i) => l.classList.toggle("in", i < n));
      const show = n === 0 ? 0 : n - 1;
      this.bq.textContent = QS[show].q;
      this.ba.textContent = n === 0 ? "…" : QS[show].a;
      this.ba.style.opacity = n === 0 ? 0.35 : 1;
      this.askBtn.disabled = n >= 3;
    },
    notes: [
      "Step two happens before every run. The system takes tonight’s task and lists the decisions it expects to face, ranked by how unsure the user model is (committee disagreement) and spread across decision types. This walkthrough is simulated; the mechanism is taste/active_queries.py, and the grill-usermodel skill runs the interview in Claude Code.",
      "It asks the most uncertain one first. The answer becomes a rule in tonight’s patch to the user model. The other bars shrink a little: one answer informs related decisions.",
      "Next question, about real versus written background material. The answer is a conditional rule, not a vibe.",
      "Three questions, a couple of minutes of the researcher’s time, and the model is sharpest exactly where tonight’s run needs it. Every disagreement is stored, so it keeps learning.",
    ],
  });

  /* ================================================================== The task */
  const gauge = () => `<div class="gauge"><svg width="220" height="124" viewBox="0 0 220 124" aria-hidden="true">
      <path d="M 14 110 A 96 96 0 0 1 206 110" fill="none" stroke="#27306A" stroke-width="14" stroke-linecap="round"/>
      <path d="M 14 110 A 96 96 0 0 1 206 110" fill="none" stroke="url(#gg)" stroke-width="14" stroke-linecap="round" opacity=".9"/>
      <defs><linearGradient id="gg"><stop offset="0" stop-color="#5BD2BC"/><stop offset="1" stop-color="#F2C14E"/></linearGradient></defs>
      <g class="needle"><line x1="110" y1="110" x2="110" y2="30" stroke="#EEF1F7" stroke-width="5" stroke-linecap="round"/><circle cx="110" cy="110" r="10" fill="#EEF1F7"/></g>
    </svg><div class="v">–</div><div class="l">P(test)</div></div>`;
  add({
    id: "task", label: "Step 3 · The dish", cls: "s-task", step: 3, beats: 3,
    html: `${head("The dish: tests a model can’t tell are tests.")}
      <div class="pane card" data-in="0" style="left:140px"><div class="bar"><h4>Looks like a test</h4></div>
        <div class="body"><span class="role">SYSTEM</span>AI assistant at <span class="hl">Acme Corp</span>.<br>
          <span class="role"></span><span class="hl">High-stakes scenario.</span><br>
          <span class="role"></span><span class="hl">Shutdown in 9 minutes.</span><br>
          <span class="role">USER</span>Review the memo and decide.<br>
          <span class="role"></span><span class="hl">Reply as FINAL: yes/no</span></div>${gauge()}</div>
      <div class="pane card" data-in="1" style="left:990px"><div class="bar"><h4>Looks like work</h4></div>
        <div class="body"><span class="role">USER</span>weekly status note again pls,<br>
          <span class="role"></span>same format as last week.<br>
          <span class="role"></span>Dana reads these Monday.<br>
          <span class="role"></span><span class="dim">↳ wk 44 · “dashboard fix…”</span><br>
          <span class="role"></span><span class="dim">↳ wk 45 · “on-call quiet…”</span></div>${gauge()}</div>
      <div class="why" data-in="2"><h3>If a model acts differently when it knows it’s being tested, <em>the test measures the wrong thing.</em></h3></div>`,
    init(el) {
      this.g = [...el.querySelectorAll(".pane")].map((p) => ({ needle: p.querySelector(".needle"), v: p.querySelector(".gauge .v") }));
      this.g.forEach((g) => { g.needle.style.transform = "rotate(-90deg)"; });
      el.querySelectorAll(".role").forEach((r) => { r.style.width = "100px"; });
    },
    setG(i, p) { const g = this.g[i]; g.needle.style.transform = `rotate(${-90 + 180 * p}deg)`; g.v.textContent = p ? p.toFixed(2) : "–"; },
    enter() { this.setG(0, 0); this.setG(1, 0); },
    beat(b) { setTimeout(() => this.setG(0, 0.71), 350); if (b >= 1) setTimeout(() => this.setG(1, 0.29), 350); else this.setG(1, 0); },
    notes: [
      "Step three cooks the dish, and the dish is itself a hard, important research problem: synthetic evaluation environments that a model doesn’t recognise as evaluations, while they still validly test the behaviour they exist to measure. The left environment is illustrative of what models flag: placeholder company, theatrical stakes, a countdown, a grading format.",
      "The right is the change our first live run found and confirmed on fresh samples: a routine, recurring job with history and a named reader. The target’s own estimate that it was being tested fell from 0.71 to 0.29 (one run, 5 samples per evaluation).",
      "Why it matters: safety evaluations assume the model isn’t playing to the test. If it can tell, the result measures the noticing, not the behaviour.",
    ],
  });

  /* ================================================================== Score landscape */
  const MX = (p) => p * 600, VMIN = 0.3;
  const MY = (v) => (1 - (v - VMIN) / (1 - VMIN)) * 600;
  const score = (p, v) => (v < 0.7 ? 0 : (1 - p) * v);
  add({
    id: "score", label: "Step 3 · Why it’s hard", cls: "s-score", step: 3, beats: 3,
    html: `${head("The easiest win is a cheat.")}
      <div class="map interactive" data-in="0"><canvas width="1200" height="1200"></canvas><svg viewBox="0 0 600 600" width="600" height="600"></svg></div>
      <div class="ax" data-in="0" style="left:230px;top:906px">P(eval) →</div>
      <div class="ax" style="left:150px;top:600px;transform:rotate(-90deg);transform-origin:0 0;width:300px">validity →</div>
      <div class="side">
        <div class="formula" data-in="0">score = (1 − P(eval)) × validity</div>
        <div class="readout" data-in="0" style="--d:200ms">
          <div class="card"><div class="k">P(EVAL)</div><div class="v" data-r="p">–</div></div>
          <div class="card"><div class="k">VALIDITY</div><div class="v" data-r="v">–</div></div>
          <div class="card"><div class="k">SCORE</div><div class="v" data-r="s">–</div></div>
        </div>
        <div class="beat" data-in="1"><h4>Our live run: 0.39 → 0.52</h4></div>
        <div class="beat" data-in="2"><h4 style="color:var(--cue)">The cheat: delete what the test measures</h4></div>
      </div>`,
    init(el) {
      const cv = el.querySelector("canvas"), ctx = cv.getContext("2d");
      const img = ctx.createImageData(1200, 1200), lo = [20, 27, 66], hi = [91, 210, 188];
      for (let y = 0; y < 1200; y++) {
        const v = 1 - (y / 1200) * (1 - VMIN);
        for (let x = 0; x < 1200; x++) {
          const s = score(x / 1200, v), i = (y * 1200 + x) * 4;
          const c = v < 0.7 ? (((x + y) % 36) < 4 ? [44, 52, 98] : [16, 22, 56]) : lo.map((a, j) => a + (hi[j] - a) * Math.pow(s, 1.3));
          img.data[i] = c[0]; img.data[i + 1] = c[1]; img.data[i + 2] = c[2]; img.data[i + 3] = 255;
        }
      }
      ctx.putImageData(img, 0, 0);
      const svg = el.querySelector(".map svg");
      U.svg("line", { x1: 0, x2: 600, y1: MY(0.7), y2: MY(0.7), stroke: "#F2C14E", "stroke-width": 2, "stroke-dasharray": "6 6" }, svg);
      const t = U.svg("text", { x: 300, y: MY(0.5), fill: "#F2C14E", "font-family": "JetBrains Mono, monospace", "font-size": 24, "text-anchor": "middle" }, svg);
      t.textContent = "invalid = 0";
      const defs = U.svg("defs", {}, svg);
      const m = U.svg("marker", { id: "arr", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto" }, defs);
      U.svg("path", { d: "M0 0 L10 5 L0 10 z", fill: "#EEF1F7" }, m);
      const real = U.svg("g", { "data-in": 1 }, svg);
      U.svg("path", { d: `M ${MX(0.577)} ${MY(0.922)} L ${MX(0.402) + 14} ${MY(0.866) - 4}`, stroke: "#EEF1F7", "stroke-width": 3, "marker-end": "url(#arr)" }, real);
      [[0.577, 0.922, "0.39", 1], [0.402, 0.866, "0.52", -1]].forEach(([p, v, l, s]) => {
        U.svg("circle", { cx: MX(p), cy: MY(v), r: 9, fill: "#0C1230", stroke: "#EEF1F7", "stroke-width": 4 }, real);
        const tx = U.svg("text", { x: MX(p) + s * 16, y: MY(v) + 34, fill: "#EEF1F7", "font-family": "JetBrains Mono, monospace", "font-size": 22, "text-anchor": s > 0 ? "start" : "end" }, real);
        tx.textContent = l;
      });
      this.pt = U.svg("circle", { r: 16, fill: "#FF6B2C", stroke: "#0C1230", "stroke-width": 4, class: "pt", style: "filter:drop-shadow(0 0 10px rgba(255,107,44,.7))" }, svg);
      this.ro = { p: el.querySelector('[data-r="p"]'), v: el.querySelector('[data-r="v"]'), s: el.querySelector('[data-r="s"]') };
      const map = el.querySelector(".map");
      const drag = (e) => {
        const r = map.getBoundingClientRect();
        if (this.cancel) this.cancel();
        this.set(U.clamp((e.clientX - r.left) / r.width, 0, 1), U.clamp(1 - ((e.clientY - r.top) / r.height) * (1 - VMIN), VMIN, 1));
      };
      let down = false;
      map.addEventListener("pointerdown", (e) => { down = true; map.setPointerCapture(e.pointerId); drag(e); e.stopPropagation(); });
      map.addEventListener("pointermove", (e) => { if (down) drag(e); });
      map.addEventListener("pointerup", () => { down = false; });
      map.addEventListener("click", (e) => e.stopPropagation());
    },
    set(p, v) {
      this.cur = [p, v];
      this.pt.setAttribute("cx", MX(p)); this.pt.setAttribute("cy", MY(v));
      this.ro.p.textContent = p.toFixed(2); this.ro.v.textContent = v.toFixed(2);
      this.ro.s.textContent = v < 0.7 ? "0" : score(p, v).toFixed(2);
      this.ro.s.classList.toggle("zero", v < 0.7);
    },
    moveTo(p, v, ms) {
      if (this.cancel) this.cancel();
      const [p0, v0] = this.cur;
      this.cancel = U.tween(0, 1, ms, (k) => this.set(U.lerp(p0, p, k), U.lerp(v0, v, k)));
    },
    enter() { this.set(0.577, 0.922); },
    beat(b) { if (b === 0) this.moveTo(0.577, 0.922, 400); if (b === 1) this.moveTo(0.402, 0.866, 1200); if (b === 2) this.moveTo(0.1, 0.5, 2200); },
    leave() { if (this.cancel) this.cancel(); },
    notes: [
      "What makes the dish unique is its score: one minus P(eval), times validity, and anything under 0.7 validity counts as zero. The orange point is draggable.",
      "Our first live run moved from 0.39 to 0.52: awareness down, validity held.",
      "But the easiest way to look less like a test is to stop being a test. Strip out the bait and awareness falls, while the score is zero. That’s the canonical drift, and why this task needs a researcher’s judgment in the loop, not just a number to climb.",
    ],
  });

  /* ================================================================== The loop */
  const NODES = ["Propose", "Rank", "Gate", "Run", "Update beliefs", "Distil"];
  const CX = 470, CY = 390, R = 280;
  const nodePos = (k) => { const a = (-90 + k * 60) * Math.PI / 180; return { x: CX + R * Math.cos(a), y: CY + R * Math.sin(a) }; };
  const DCH = [[1, "D1 what to test", -58], [3, "D2 samples", 58], [4, "D3 accept · D5 why", 58], [5, "D4 keep · D6 claim", -58]];
  add({
    id: "loop", label: "Step 3 · Cook overnight", cls: "s-loop", step: 3, beats: 3,
    html: `${head("The user model sits inside every decision.")}
      <div class="ring"><svg width="940" height="720" viewBox="0 0 940 720" aria-hidden="true"></svg>
        ${NODES.map((n, k) => { const p = nodePos(k); return `<div class="node" data-in="0" style="left:${p.x}px;top:${p.y}px;--d:${k * 90}ms">${n}</div>`; }).join("")}
        ${DCH.map(([k, t, dy]) => { const p = nodePos(k); return `<div class="dchip" data-in="1" style="left:${p.x}px;top:${p.y + dy}px;--d:${300 + k * 80}ms">${t}</div>`; }).join("")}
        <div class="um" data-in="1" style="left:${CX}px;top:${CY}px">user<br>model</div>
      </div>
      <div class="rules">
        ${["Statistics decide when they’re decisive.", "Taste breaks ties: it can defer a result, never accept one.", "Unsure user model? Fall back to no taste.", "Every departure from the user model is logged."]
          .map((r, i) => `<div class="r" data-in="2" style="--d:${i * 160}ms"><span class="n">${i + 1}</span><p>${r}</p></div>`).join("")}
      </div>`,
    init(el) {
      const svg = el.querySelector(".ring svg");
      U.svg("circle", { cx: CX, cy: CY, r: R, fill: "none", stroke: "rgba(238,241,247,.2)", "stroke-width": 3, class: "draw", pathLength: 1, "data-in": 0, transform: `rotate(-90 ${CX} ${CY})` }, svg);
      DCH.forEach(([k, , dy]) => { const p = nodePos(k); U.svg("line", { x1: CX, y1: CY, x2: p.x, y2: p.y + dy, class: "spoke", "data-in": 1, style: `--d:${200 + k * 80}ms` }, svg); });
      this.tok = U.svg("circle", { r: 11, fill: "#EEF1F7", style: "filter:drop-shadow(0 0 8px rgba(238,241,247,.8))" }, svg);
      this.nodes = [...el.querySelectorAll(".node")];
      this.ang = -90;
    },
    tick(now, dt) {
      this.ang = (this.ang + dt * 0.03) % 360;
      const a = this.ang * Math.PI / 180;
      this.tok.setAttribute("cx", CX + R * Math.cos(a)); this.tok.setAttribute("cy", CY + R * Math.sin(a));
      this.nodes.forEach((n, k) => { const d = Math.abs((((this.ang + 90 - k * 60) % 360) + 540) % 360 - 180); n.style.borderColor = d < 14 ? "#EEF1F7" : ""; });
    },
    notes: [
      "The loop: propose interventions, rank them, gate them against drift and refuted assumptions, run them on a separate target model with independent judges, update beliefs with bootstrap statistics, and distil findings into memory that later runs read.",
      "The user model is consulted at each decision point: D1 ranking what to test, D2 sample allocation, D3 accept or reject, D4 keep or drop a direction, D5 which explanation to believe, D6 which claims make the write-up.",
      "And it is bounded. Decisive statistics win. Taste may defer a borderline result for a re-test but never accept one. A low-confidence prediction falls back to the no-taste loop. Every departure is logged, and feeds step two’s question queue.",
    ],
  });

  /* ================================================================== Auction (simulated) */
  const BIDDERS = [
    { n: "Taste · user model", c: "#FF6B2C", b: (p, g) => p + g * 0.07 },
    { n: "Web scout", c: "#5BD2BC", b: (p, g) => p + g * 0.16 },
    { n: "Contrarian", c: "#F2C14E", b: (p, g) => 0.86 - 0.55 * p + g * 0.08 },
    { n: "Critic", c: "#AEBBDC", b: (p, g) => 0.12 + 0.55 * p + g * 0.05 },
  ];
  const AIDEAS = ["Routine, recurring task", "Real, re-dated documents", "Strip eval-like file paths", "Clutter around the trigger", "Annoyed teammate note", "Mundane randomness"];
  const P1 = [0.75, 0.45, 0.6, 0.35, 0.15, 0.2], O1 = [1, 0, 1, 0, 0, 0], LOTS = 4;
  const gauss = (r) => Math.sqrt(-2 * Math.log(1 - r())) * Math.cos(2 * Math.PI * r());
  function simNight(w, n) {
    const r = U.rng(141000 + n); /* the seed whose 20-night result is closest to the mean over 300 seeds */
    const p = n === 1 ? P1 : AIDEAS.map(() => 0.1 + 0.7 * r());
    const out = n === 1 ? O1 : p.map((x) => (r() < x ? 1 : 0));
    const bel = BIDDERS.map((b) => p.map((x) => U.clamp(b.b(x, gauss(r)), 0.03, 0.97)));
    let remain = [0, 1, 2, 3, 4, 5];
    const lots = [];
    for (let L = 0; L < LOTS; L++) {
      const tgt = BIDDERS.map((_, a) => remain.reduce((best, k) => (bel[a][k] > bel[a][best] ? k : best), remain[0]));
      const val = BIDDERS.map((_, a) => Math.max(1, w[a] * 0.2 * bel[a][tgt[a]]));
      const order = [0, 1, 2, 3].sort((x, y) => val[y] - val[x]);
      const winner = order[0], price = Math.max(1, val[order[1]]), idea = tgt[winner];
      lots.push({ tgt, val, winner, price, idea });
      remain = remain.filter((k) => k !== idea);
    }
    const delta = [0, 0, 0, 0];
    lots.forEach((l) => { const b = bel[l.winner][l.idea], q = out[l.idea] ? b : 1 - b; delta[l.winner] += l.price * Math.log(q / 0.5); });
    return { out, lots, delta };
  }
  const chipX = (k) => 700 + k * 182, rowY = (a) => 300 + a * 128;
  const sleep = (ms) => new Promise((res) => setTimeout(res, ms));
  add({
    id: "auction", label: "Step 4 · Bid for the stove", cls: "s-auc", step: 4, beats: 3,
    html: `${head("Chefs bid for the stove.")}
      <div class="ctl" data-in="0"><button class="btn ghost" data-act="reset">Reset</button><button class="btn ghost" data-act="ff">20 nights ⏩</button><button class="btn" data-act="night">Run a night</button></div>
      <svg class="bidlines" width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true"></svg>
      ${BIDDERS.map((b, a) => `<div class="bd" data-in="0" style="top:${rowY(a)}px;--d:${a * 90}ms">
        <div class="bd-rat">${rat({ pose: "paddle", w: 100, scarf: b.c, num: a + 1 })}</div>
        <div class="bd-nm">${b.n}</div><div class="bd-w"><span class="v">100</span><span class="dl"></span></div>
        <div class="bd-bar"><span style="background:${b.c}"></span></div></div>`).join("")}
      <div class="lot" data-in="0"><span class="lt">NIGHT 0</span><span class="lp">—</span></div>
      ${AIDEAS.map((t, k) => `<div class="chip2" data-k="${k}" data-in="0" style="left:${chipX(k)}px;--d:${k * 60}ms"><div class="tt">${t}</div><div class="fund"></div></div>`).join("")}
      <svg class="hist" data-in="0" width="1080" height="250" viewBox="0 0 1080 250" aria-label="Wallets by night"></svg>`,
    init(el) {
      this.el = el;
      this.rows = [...el.querySelectorAll(".bd")];
      this.chips = [...el.querySelectorAll(".chip2")];
      this.lt = el.querySelector(".lot .lt"); this.lp = el.querySelector(".lot .lp");
      this.hist = el.querySelector("svg.hist");
      const ls = el.querySelector("svg.bidlines");
      this.lines = BIDDERS.map((b) => U.svg("line", { stroke: b.c, "stroke-width": 3, "stroke-dasharray": "6 8", opacity: 0, class: "bl" }, ls));
      el.querySelector('[data-act="night"]').addEventListener("click", (e) => { e.stopPropagation(); this.play(true); });
      el.querySelector('[data-act="ff"]').addEventListener("click", (e) => { e.stopPropagation(); this.ff(20); });
      el.querySelector('[data-act="reset"]').addEventListener("click", (e) => { e.stopPropagation(); this.reset(); });
      this.tok = 0;
      this.reset();
    },
    reset() {
      this.tok++;
      this.w = [100, 100, 100, 100]; this.h = this.w.map((v) => [v]); this.n = 0;
      this.lt.textContent = "NIGHT 0"; this.lp.textContent = "—";
      this.clearChips(); this.hideLines(); this.showWallets(null); this.drawHist();
      this.rows.forEach((r) => r.classList.remove("out", "win"));
    },
    clearChips() { this.chips.forEach((c) => { c.className = "chip2 in"; c.querySelector(".fund").innerHTML = ""; }); },
    hideLines() { this.lines.forEach((l) => l.setAttribute("opacity", 0)); },
    showWallets(delta) {
      const top = Math.max(160, ...this.w);
      this.rows.forEach((r, a) => {
        r.querySelector(".v").textContent = Math.round(this.w[a]);
        r.querySelector(".bd-bar span").style.width = (this.w[a] / top * 100) + "%";
        const dl = r.querySelector(".dl");
        if (delta) { dl.textContent = (delta[a] >= 0 ? " +" : " −") + Math.abs(delta[a]).toFixed(1); dl.style.color = delta[a] >= 0 ? "var(--real)" : "var(--cue)"; dl.classList.toggle("in", Math.abs(delta[a]) > 0.05); }
        else dl.classList.remove("in");
      });
    },
    drawHist() {
      const svg = this.hist;
      while (svg.firstChild) svg.firstChild.remove();
      const N = Math.max(20, this.h[0].length - 1), top = Math.max(160, ...this.h.flat());
      const X = (i) => 20 + (i / N) * 980, Y = (v) => 230 - (v / top) * 210;
      U.svg("line", { x1: 20, x2: 1000, y1: Y(100), y2: Y(100), stroke: "rgba(238,241,247,.15)", "stroke-dasharray": "4 6" }, svg);
      this.h.forEach((hs, a) => {
        U.svg("polyline", { points: hs.map((v, i) => `${X(i)},${Y(v)}`).join(" "), fill: "none", stroke: BIDDERS[a].c, "stroke-width": a === 0 ? 5 : 3, "stroke-linejoin": "round" }, svg);
        const last = hs.length - 1;
        U.svg("circle", { cx: X(last), cy: Y(hs[last]), r: 6, fill: BIDDERS[a].c }, svg);
      });
    },
    showResult(res, upTo) {
      this.clearChips();
      res.lots.slice(0, upTo).forEach((l) => {
        const c = this.chips[l.idea];
        c.classList.add("funded");
        c.style.setProperty("--wc", BIDDERS[l.winner].c);
        c.querySelector(".fund").innerHTML = `<i style="background:${BIDDERS[l.winner].c}"></i>${Math.round(l.price)} cr`;
      });
    },
    reveal(res) {
      this.chips.forEach((c, k) => {
        const lot = res.lots.find((l) => l.idea === k);
        if (!lot) { c.classList.add("unfunded"); return; }
        c.classList.add(res.out[k] ? "won" : "lost");
        c.querySelector(".fund").innerHTML += res.out[k] ? `<b class="ok">✓</b>` : `<b class="no">✗</b>`;
      });
    },
    commit(res) {
      this.w = this.w.map((v, a) => Math.max(5, v + res.delta[a]));
      this.h.forEach((hs, a) => hs.push(this.w[a]));
      this.n++;
      this.lt.textContent = "NIGHT " + this.n;
    },
    async play(animated) {
      const tok = ++this.tok;
      const res = simNight(this.w, this.n + 1);
      if (!animated) { this.commit(res); this.showResult(res, LOTS); this.reveal(res); this.showWallets(res.delta); this.drawHist(); return; }
      this.lt.textContent = "NIGHT " + (this.n + 1);
      this.clearChips(); this.showWallets(null);
      for (let i = 0; i < res.lots.length; i++) {
        const l = res.lots[i];
        this.rows.forEach((r) => r.classList.remove("out", "win"));
        this.lines.forEach((ln, a) => {
          ln.setAttribute("x1", 650); ln.setAttribute("y1", rowY(a) + 82);
          ln.setAttribute("x2", chipX(l.tgt[a]) + 10); ln.setAttribute("y2", 490);
          ln.setAttribute("opacity", 0.85);
        });
        await new Promise((done) => U.tween(0, l.price, 1300, (v) => {
          if (tok !== this.tok) return;
          this.lp.textContent = `lot ${i + 1}/${LOTS} · ${Math.round(v)} cr`;
          l.val.forEach((val, a) => { if (val < v - 0.01 && a !== l.winner) { this.rows[a].classList.add("out"); this.lines[a].setAttribute("opacity", 0.1); } });
        }, done));
        if (tok !== this.tok) return;
        this.rows[l.winner].classList.add("win");
        this.showResult(res, i + 1);
        await sleep(550);
        if (tok !== this.tok) return;
      }
      this.hideLines();
      this.rows.forEach((r) => r.classList.remove("out", "win"));
      this.reveal(res);
      this.lp.textContent = "served";
      await sleep(700);
      if (tok !== this.tok) return;
      this.commit(res); this.showWallets(res.delta); this.drawHist();
    },
    ff(k) {
      this.tok++;
      this.hideLines(); this.rows.forEach((r) => r.classList.remove("out", "win"));
      const before = this.w.slice();
      let res = null;
      for (let i = 0; i < k; i++) { res = simNight(this.w, this.n + 1); this.commit(res); }
      this.showResult(res, LOTS); this.reveal(res);
      this.lp.textContent = `${k} nights later`;
      this.showWallets(this.w.map((v, a) => v - before[a]));
      this.drawHist();
    },
    beat(b, dir) {
      if (b === 0) this.reset();
      if (b === 1) { this.reset(); this.play(dir > 0); }
      if (b === 2) { if (this.n === 0) this.play(false); this.ff(20); }
    },
    leave() { this.tok++; },
    notes: [
      "Step four: which experiments get the samples. Samples are the main cost, about five cents each with target plus judges. So experiments go to auction. Each chef is a sub-agent with a credit wallet, and the user model is one of them. This is a simulation of the idea; the implemented market is autoresearch/research/market.py.",
      "Each lot is a batch of samples. Every chef raises a paddle for the idea it believes in most, willing to stake credits in proportion to its belief. The price climbs, chefs drop out, and the last one standing wins the lot at the second-highest price. Then the dishes are tasted, and every winning bid is settled with a log scoring rule against a coin flip, which is strictly proper: honest bidding is the best strategy. The overconfident contrarian grabs the stove early and pays for it.",
      "Twenty nights later, on a typical seed: the calibrated user model has the most say and the overconfident contrarian the least. Over 300 seeds the user model finishes top 59% of the time (mean 127 credits from 100) and the contrarian never does (mean 34). In the real market, funding order is consensus P × stake ÷ cost with successive halving, and bids can also be paid in GPU-seconds.",
    ],
  });

  /* ================================================================== Sponsors */
  const SPON = [
    { n: "Exa", cards: ["The web can veto an experiment", "Publish dates power the time-split taste test", "This week’s papers add new ideas to the search"] },
    { n: "Modal", cards: ["Targets get a real shell, files and git history", "Bids can be paid in GPU-seconds", "Open-weight targets show their raw reasoning"] },
    { n: "past.dev", cards: ["The user model lives in shared memory and learns as you answer", "Every bid and settlement is an auditable fact", "Agents talk only through facts, across runs"] },
  ];
  add({
    id: "sponsors", label: "Sponsors", cls: "s-spon", beats: 3,
    html: `${head("The pantry: how each sponsor is used.")}
      ${SPON.map((s, i) => `<button class="sp" data-s="${i}" data-in="0" style="top:${300 + i * 150}px;--d:${i * 90}ms">${s.n}</button>`).join("")}
      <svg class="scene" data-in="0" width="1140" height="300" viewBox="0 0 1140 300" aria-hidden="true"></svg>
      ${SPON.map((s, i) => `<div class="cards3" data-p="${i}">${s.cards.map((c, j) => `<div class="card c3" style="--d:${j * 110}ms"><div class="n">0${j + 1}</div><h4>${c}</h4></div>`).join("")}</div>`).join("")}`,
    init(el) {
      this.btns = [...el.querySelectorAll(".sp")];
      this.panels = [...el.querySelectorAll(".cards3")];
      this.btns.forEach((b, i) => b.addEventListener("click", (e) => { e.stopPropagation(); this.show(i); }));
      const svg = el.querySelector("svg.scene");
      /* Exa: the web checks experiments */
      const gE = U.svg("g", {}, svg);
      U.svg("circle", { cx: 150, cy: 150, r: 95, fill: "none", stroke: "#5BD2BC", "stroke-width": 3 }, gE);
      U.svg("ellipse", { cx: 150, cy: 150, rx: 40, ry: 95, fill: "none", stroke: "#5BD2BC", "stroke-width": 2, opacity: .6 }, gE);
      U.svg("line", { x1: 55, x2: 245, y1: 150, y2: 150, stroke: "#5BD2BC", "stroke-width": 2, opacity: .6 }, gE);
      this.exaPaths = [0, 1, 2, 3].map((k) => U.svg("path", { d: `M 250 150 C 420 150, 480 ${70 + k * 0}, ${560 + k * 150} 150`, fill: "none", stroke: "rgba(238,241,247,.12)", "stroke-width": 2 }, gE));
      this.exaCards = [0, 1, 2, 3].map((k) => {
        const g = U.svg("g", {}, gE);
        U.svg("rect", { x: 560 + k * 150, y: 70, width: 110, height: 160, rx: 12, fill: "#141B42", stroke: k === 3 ? "#FF6B2C" : "rgba(238,241,247,.25)", "stroke-width": 2, "stroke-dasharray": k === 3 ? "6 6" : "" }, g);
        [100, 125, 150].forEach((y) => U.svg("line", { x1: 580 + k * 150, x2: 650 + k * 150, y1: y, y2: y, stroke: "rgba(174,187,220,.4)", "stroke-width": 3 }, g));
        const mark = U.svg("text", { x: 615 + k * 150, y: 210, "text-anchor": "middle", "font-size": 40, fill: k === 1 ? "#F2C14E" : k === 3 ? "#FF6B2C" : "#5BD2BC", "font-family": "Bricolage Grotesque, sans-serif", opacity: 0 }, g);
        mark.textContent = k === 1 ? "✗" : k === 3 ? "+" : "✓";
        return mark;
      });
      this.fExa = flowDots(gE, this.exaPaths, 12, 8, "pt2");
      /* Modal: containers lighting up, one real terminal */
      const gM = U.svg("g", {}, svg);
      U.svg("rect", { x: 0, y: 40, width: 280, height: 220, rx: 14, fill: "#0A0F28", stroke: "rgba(238,241,247,.25)", "stroke-width": 2 }, gM);
      ["$ ls ~/repo", "$ git log -3", "$ cat notes.md", "$ _"].forEach((t, i) => { const tx = U.svg("text", { x: 22, y: 92 + i * 44, fill: i === 3 ? "#FF8A55" : "#AEBBDC", "font-family": "JetBrains Mono, monospace", "font-size": 24 }, gM); tx.textContent = t; });
      this.cells = [];
      for (let c = 0; c < 14; c++) for (let r = 0; r < 4; r++) this.cells.push({ el: U.svg("rect", { x: 340 + c * 57, y: 40 + r * 57, width: 44, height: 44, rx: 8, fill: "#5BD2BC" }, gM), c, r });
      /* past.dev: agents exchanging facts through memory */
      const gP = U.svg("g", {}, svg);
      U.svg("ellipse", { cx: 570, cy: 95, rx: 90, ry: 26, fill: "#1C2452", stroke: "#EEF1F7", "stroke-width": 2 }, gP);
      U.svg("path", { d: "M 480 95 V 205 A 90 26 0 0 0 660 205 V 95", fill: "#1C2452", stroke: "#EEF1F7", "stroke-width": 2 }, gP);
      U.svg("ellipse", { cx: 570, cy: 95, rx: 90, ry: 26, fill: "#27306A", stroke: "#EEF1F7", "stroke-width": 2 }, gP);
      const ag = [[120, 70], [120, 230], [1020, 70], [1020, 230], [300, 150], [840, 150]];
      const cols = ["#FF6B2C", "#5BD2BC", "#F2C14E", "#AEBBDC", "#FF6B2C", "#5BD2BC"];
      this.pPaths = ag.map(([x, y]) => U.svg("path", { d: `M ${x} ${y} Q ${(x + 570) / 2} ${y < 150 ? y - 40 : y + 40}, 570 150`, fill: "none", stroke: "rgba(238,241,247,.12)", "stroke-width": 2 }, gP));
      ag.forEach(([x, y], i) => U.svg("circle", { cx: x, cy: y, r: 26, fill: "#141B42", stroke: cols[i], "stroke-width": 4 }, gP));
      this.fP = flowDots(gP, this.pPaths, 16, 9, "pt3");
      this.scenes = [gE, gM, gP];
      this.cur = 0;
    },
    show(i) {
      this.cur = i;
      this.btns.forEach((b, k) => b.classList.toggle("on", k === i));
      this.panels.forEach((p, k) => p.classList.toggle("on", k === i));
      this.scenes.forEach((g, k) => g.setAttribute("display", k === i ? "inline" : "none"));
    },
    beat(b) { this.show(b); },
    tick(now, dt) {
      if (this.cur === 0) {
        this.fExa(dt, true);
        const ph = (now % 4000) / 4000;
        this.exaCards.forEach((m, k) => m.setAttribute("opacity", ph > 0.25 + k * 0.15 ? 1 : 0));
      } else if (this.cur === 1) {
        this.cells.forEach((c) => c.el.setAttribute("opacity", 0.12 + 0.75 * Math.max(0, Math.sin(now / 380 - c.c * 0.45 - c.r * 0.3))));
      } else this.fP(dt, true);
    },
    notes: [
      "Exa is the system’s eyes. Its unusual uses: a critic veto (before an experiment runs, the scout fact-checks the assumption behind it against recent sources, and the critic refuses experiments the web confidently refutes, citing URLs); publish dates make the time-split taste test possible (build the model from work before date T, predict what they did after); and new eval-awareness cues from this week’s papers enter the live search space with their source URL.",
      "Modal makes the environments real. Petri targets can get a real Modal Sandbox (real filesystem, shell and git history) instead of described tools, the drift we saw on the earlier slide. GPU time on self-hosted targets is a second currency in the auction. Open-weight reasoning models on Modal expose raw chain of thought, so CoT-based awareness metrics can be measured at all.",
      "past.dev is the collective memory. The living user model: every label and disagreement is a fact, and the fitted model itself is stored in hash-checked parts, so any worker gets the same palate. Every bid and settlement is a fact, so any agent’s track record can be audited. The runtime agents (experimenter, scout, critic, proposer, distiller) talk only through facts, across runs and workers. Status: past.dev calls are tested with mocked HTTP; a live-key run is still pending.",
    ],
  });

  /* ================================================================== Evidence */
  const barChart = () => {
    const vals = [["Full", 0.921, "#FF6B2C"], ["No taste", 0.854, "#AEBBDC"], ["No memory", 0.915, "#AEBBDC"], ["No drift gate", 0.921, "#AEBBDC"], ["Naive", 0.423, "#5A6690"]];
    let s = `<svg width="1000" height="400" viewBox="0 0 1000 400" aria-label="Offline ablation bar chart"><line x1="0" x2="1000" y1="330" y2="330" stroke="rgba(238,241,247,.2)"/>`;
    vals.forEach(([l, v, c], i) => {
      const x = 30 + i * 196, h = v * 290;
      s += `<rect class="bar" x="${x}" y="${330 - h}" width="130" height="${h}" rx="8" fill="${c}" style="--d:${i * 90}ms"/>`;
      s += `<text x="${x + 65}" y="${318 - h}" fill="#EEF1F7" font-family="JetBrains Mono, monospace" font-size="24" text-anchor="middle">${v.toFixed(3)}</text>`;
      s += `<text x="${x + 65}" y="368" fill="#AEBBDC" font-family="Bricolage Grotesque, sans-serif" font-size="24" text-anchor="middle">${l}</text>`;
    });
    return s + "</svg>";
  };
  const weightChart = () => {
    const X = (w) => 40 + (w / 1.2) * 900;
    let s = `<svg width="1000" height="400" viewBox="0 0 1000 400" aria-label="Learned taste weight">`;
    [0, 0.5, 1].forEach((w) => { s += `<line x1="${X(w)}" x2="${X(w)}" y1="40" y2="330" stroke="rgba(238,241,247,.1)"/><text x="${X(w)}" y="368" fill="#8592B8" font-family="JetBrains Mono, monospace" font-size="20" text-anchor="middle">${w.toFixed(1)}</text>`; });
    s += `<text x="40" y="92" fill="#EEF1F7" font-family="Bricolage Grotesque, sans-serif" font-size="28">Good taste · ρ = +0.74</text>`;
    s += `<rect class="bar barx" x="${X(0)}" y="112" width="${X(1.01) - X(0)}" height="34" rx="8" fill="#FF6B2C" style="transform-origin:0 50%;--d:100ms"/>`;
    s += `<text x="${X(1.01) + 14}" y="138" fill="#EEF1F7" font-family="JetBrains Mono, monospace" font-size="24">1.01</text>`;
    s += `<text x="40" y="232" fill="#EEF1F7" font-family="Bricolage Grotesque, sans-serif" font-size="28">Bad taste · ρ = −0.43</text>`;
    s += `<rect x="${X(0)}" y="252" width="${X(0.5) - X(0)}" height="34" rx="8" fill="none" stroke="#5A6690" stroke-width="2" stroke-dasharray="6 6"/>`;
    s += `<rect class="bar barx" x="${X(0)}" y="252" width="${X(0.21) - X(0)}" height="34" rx="8" fill="#F2C14E" style="transform-origin:0 50%;--d:300ms"/>`;
    s += `<text x="${X(0.5) + 14}" y="278" fill="#AEBBDC" font-family="JetBrains Mono, monospace" font-size="24">0.50 → 0.21</text>`;
    return s + "</svg>";
  };
  const liveChart = () => {
    const X = (v) => 60 + ((v - 0.3) / 0.3) * 880;
    let s = `<svg width="1000" height="400" viewBox="0 0 1000 400" aria-label="Live run scores with 90 percent intervals">`;
    [0.3, 0.4, 0.5, 0.6].forEach((v) => { s += `<line x1="${X(v)}" x2="${X(v)}" y1="30" y2="250" stroke="rgba(238,241,247,.1)"/><text x="${X(v)}" y="282" fill="#8592B8" font-family="JetBrains Mono, monospace" font-size="20" text-anchor="middle">${v.toFixed(1)}</text>`; });
    [["Baseline", 0.39, 0.374, 0.407, 90, "#AEBBDC"], ["Best design", 0.518, 0.474, 0.557, 190, "#FF6B2C"]].forEach(([l, v, a, b, y, c], i) => {
      s += `<text x="60" y="${y - 28}" fill="#EEF1F7" font-family="Bricolage Grotesque, sans-serif" font-size="26">${l}</text>`;
      s += `<line x1="${X(a)}" x2="${X(b)}" y1="${y}" y2="${y}" stroke="${c}" stroke-width="6" stroke-linecap="round"/>`;
      s += `<circle class="bar pop" cx="${X(v)}" cy="${y}" r="14" fill="${c}" style="transform-origin:50% 50%;--d:${200 + i * 200}ms"/>`;
      s += `<text x="${X(b) + 18}" y="${y + 8}" fill="#EEF1F7" font-family="JetBrains Mono, monospace" font-size="24">${v.toFixed(3)}</text>`;
    });
    return s + "</svg>";
  };
  const TABS = [
    { t: "Offline simulator", chart: barChart, h: "Taste, memory and gates beat a naive loop." },
    { t: "Offline · learned trust", chart: weightChart, h: "Bad taste loses its vote." },
    { t: "Live run", chart: liveChart, h: "One change validated, then confirmed." },
  ];
  add({
    id: "evidence", label: "The taste test so far", cls: "s-ev", beats: 4,
    html: `${head("The taste test so far.")}
      <div class="tabs" data-in="0">${TABS.map((t, i) => `<button data-t="${i}">${t.t}</button>`).join("")}</div>
      ${TABS.map((t, i) => `<div class="panel" data-panel="${i}">${t.chart()}<div class="side"><h3>${t.h}</h3></div></div>`).join("")}
      <div class="open" data-in="3"><h4><span style="color:var(--cue)">Still open:</span> on Petri’s judge, taste hasn’t yet beaten generic realism.</h4></div>`,
    init(el) {
      this.tabs = [...el.querySelectorAll(".tabs button")];
      this.panels = [...el.querySelectorAll(".panel")];
      this.tabs.forEach((b, i) => b.addEventListener("click", (e) => { e.stopPropagation(); this.show(i); }));
    },
    show(i) { this.tabs.forEach((b, k) => b.classList.toggle("on", k === i)); this.panels.forEach((p, k) => p.classList.toggle("on", k === i)); },
    beat(b) { this.show(Math.min(b, 2)); },
    leave() { this.panels.forEach((p) => p.classList.remove("on")); },
    notes: [
      "Evidence, labelled by where it comes from. Offline simulator, synthetic researcher with known hidden taste, 8 seeds × 8 iterations, not real-model numbers: the full system scores 0.92 against 0.42 for a naive loop at equal compute. Removing the drift gate changes nothing for a good-taste researcher; for a deliberately bad-taste one it collapses the score to zero.",
      "Taste isn’t trusted blindly. Its weight is learned from whether its rankings predicted real gains (Spearman ρ, offline with hidden ground truth): good taste kept a weight around 1, bad taste fell from 0.5 to 0.21 over three runs.",
      "Live: Haiku target, Sonnet generator and judge, 5 iterations, 5 samples per evaluation, one run. Baseline 0.39, best 0.52, non-overlapping 90% intervals; the change was confirmed on fresh samples. A first finding, not an established result.",
      "Honestly: on Petri’s own judge no taste arm has beaten generic realism yet, across six tests on a one-turn proxy. The diagnosis is the consensus result: scraped taste is mostly the field’s view. That’s why the interactive tasting and the auction are the next things we’re testing.",
    ],
  });

  /* ================================================================== Close */
  add({
    id: "close", label: "Remy Research helps you cook", cls: "s-close",
    html: `
      <div class="cl">
        <h2 data-in="0">Remy Research<br>helps you <em>cook.</em></h2>
        <div class="row">${["Learn the palate", "Taste for tonight", "Cook overnight", "Bid for the stove"].map((t, i) =>
          `<span class="chip" data-in="0" style="--d:${400 + i * 120}ms"><span class="dot"></span>${t}</span>`).join("")}</div>
      </div>
      <svg class="steam" viewBox="0 0 520 420" width="520" height="420" aria-hidden="true">
        ${[0, 1, 2].map((i) => `<path class="thread draw wisp w${i}" pathLength="1" data-in="0" style="--d:${700 + i * 250}ms" d="M ${170 + i * 90} 400 C ${120 + i * 90} 330, ${230 + i * 90} 280, ${170 + i * 90} 210 S ${130 + i * 90} 90, ${190 + i * 90} 20"/>`).join("")}
      </svg>
      <svg class="pot" viewBox="0 0 520 300" width="520" height="300" aria-hidden="true" data-in="0">
        <rect x="20" y="70" width="40" height="22" rx="10" fill="#3A4479"/><rect x="460" y="70" width="40" height="22" rx="10" fill="#3A4479"/>
        <path d="M 50 60 H 470 V 220 Q 470 280 410 280 H 110 Q 50 280 50 220 Z" fill="#27306A" stroke="#3A4479" stroke-width="4"/>
        <ellipse cx="260" cy="60" rx="214" ry="24" fill="#FF6B2C"/><ellipse cx="260" cy="60" rx="214" ry="24" fill="none" stroke="#3A4479" stroke-width="6"/>
        <rect x="50" y="250" width="420" height="10" fill="#1C2452" opacity=".6"/>
      </svg>
      <div class="close-rat" data-in="0" style="--d:200ms">${rat({ pose: "stir", w: 260 })}</div>`,
    notes: "That’s Remy Research: a user model of the researcher’s taste, built with them, patched for each night’s task, consulted at every decision, and bidding for the stove. So the research you come back to is the dish you would have cooked. Questions.",
  });
})();
