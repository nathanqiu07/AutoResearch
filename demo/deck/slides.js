/* Remy Research deck: the slides. Kitchen framing appears only at the opening and close.
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
    /* The template rat (img/rat.png: cut out of its paper, sticker border, open hand removed) plus,
       in the same thick-outline style: a fist gripping a big wooden spoon (or an auction paddle)
       in front, and a chef's toque tilted to sit on the crown. Image space: 520 x 722. */
    o = o || {};
    const w = o.w || 220, INK = "#111317", HAT = "#FBF8F1", WOOD = "#C98F55", WOOD2 = "#A9713C";
    const SKIN = "#E3868B", H = "#F1ECE2", band = o.band || "#E6E0D2";
    const halo = (d) => `<path d="${d}" fill="${H}" stroke="${H}" stroke-width="22" stroke-linejoin="round"/>`;
    const line = (d, fill, sw) => `<path d="${d}" fill="${fill}" stroke="${INK}" stroke-width="${sw || 5}" stroke-linejoin="round" stroke-linecap="round"/>`;
    const both = (d, fill, sw) => halo(d) + line(d, fill, sw);
    /* the held object runs along one line, x = 390 + (262 - y) * 0.1753, through the fist */
    const handle = (top) => {
      const xt = 390 + (262 - top) * 0.1753;
      return `M 379 262 L ${xt - 11} ${top} L ${xt + 11} ${top} L 401 262 A 11 11 0 0 1 379 262 Z`;
    };
    let held = "", label = "";
    if (o.pose === "paddle") {
      held = both(handle(-30), WOOD) +
        `<circle cx="452" cy="-84" r="58" fill="${H}" stroke="${H}" stroke-width="22"/>` +
        `<circle cx="452" cy="-84" r="58" fill="${HAT}" stroke="${INK}" stroke-width="5"/>` +
        `<circle cx="452" cy="-84" r="44" fill="none" stroke="${band}" stroke-width="9"/>`;
      label = `<text x="452" y="-64" text-anchor="middle" font-family="Bricolage Grotesque, sans-serif" font-weight="600" font-size="56" fill="${INK}">${o.num || ""}</text>`;
    } else {
      const bowl = "M 0 -86 C 40 -86, 60 -40, 58 0 C 56 44, 30 84, 0 84 C -30 84, -56 44, -58 0 C -60 -40, -40 -86, 0 -86 Z";
      held = halo(handle(-40)) + `<g transform="translate(455 -112) rotate(10)">${halo(bowl)}</g>` +
        line(handle(-40), WOOD) +
        `<path d="M 388 248 L 437 -30" stroke="#E2B27E" stroke-width="4" stroke-linecap="round"/>` +
        `<g transform="translate(455 -112) rotate(10)">${line(bowl, WOOD)}
          <path d="M 0 -68 C 28 -66, 42 -30, 40 2 C 38 36, 20 64, 0 66 C -22 64, -40 36, -40 2 C -42 -30, -26 -68, 0 -68 Z" fill="${WOOD2}" opacity=".4"/>
          <path d="M -26 -52 C -34 -36, -38 -16, -36 4" fill="none" stroke="#F3D9B8" stroke-width="6" stroke-linecap="round"/></g>`;
    }
    /* the fist, wrapped round the handle in front */
    const fistD = "M 376 112 C 372 94, 390 84, 410 86 C 430 86, 446 98, 446 116 C 448 136, 440 156, 420 162 C 398 168, 378 158, 374 140 Z";
    const fist = both(fistD, SKIN) +
      `<path d="M 384 106 C 402 101, 424 101, 442 106 M 381 123 C 401 118, 425 118, 445 123 M 383 141 C 401 137, 423 137, 440 141" fill="none" stroke="${INK}" stroke-width="3.6" stroke-linecap="round"/>` +
      line("M 378 116 C 368 104, 374 88, 392 86 C 404 85, 414 92, 414 102 C 404 98, 392 102, 386 112 Z", SKIN, 4);
    /* chef's toque, tilted to the head's crown */
    const hat = `<g transform="translate(176 30) rotate(7)">` +
      both("M -62 -26 C -96 -34, -100 -92, -56 -92 C -60 -140, 14 -152, 24 -108 C 66 -124, 92 -64, 62 -26 Z", HAT) +
      `<path d="M -28 -34 C -36 -56, -34 -76, -24 -92 M 18 -36 C 18 -56, 22 -76, 32 -94" fill="none" stroke="${INK}" stroke-width="3.6" stroke-linecap="round"/>` +
      both("M -64 4 C -30 -6, 30 -6, 64 4 L 62 -26 C 30 -36, -30 -36, -62 -26 Z", band) + `</g>`;
    return `<svg class="rat ${o.cls || ""}" viewBox="0 -215 540 945" width="${w}" height="${Math.round(w * 945 / 540)}" aria-hidden="true" style="overflow:visible">
      <image href="img/rat.png?v=2" x="0" y="0" width="520" height="722"/>${hat}${held}${fist}${label}
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
      <div class="title-rat" data-in="0" style="--d:500ms">${rat({ w: 190 })}</div>`,
    init(el) { growTree(el.querySelector("svg"), 11, { x0: 1160, x1: 1830, y0: 540, levels: 5, spread: 430, ymin: 150, ymax: 930, yGoal: 380 }); },
    notes: "Remy Research, named after the film’s rat who cooks by taste. An overnight research agent that makes the calls the researcher would make. Grey: every path the agent could take. Orange: the one you would.",
  });

  /* ================================================================== The overnight run */
  const NW = 1640, NH = 400;
  const sig = (z) => 1 / (1 + Math.exp(-z));
  const yR = (x) => 70 + 8 * Math.sin(x / 140);
  const yA = (x) => yR(x) + 80 * sig((x - 410) / 40) + 80 * sig((x - 820) / 40) + 80 * sig((x - 1230) / 40) + 5 * Math.sin(x / 33) * sig((x - 300) / 60);
  const EVENTS = [{ x: 410, time: "00:30", h: "Changes the task" }, { x: 820, time: "03:00", h: "Games the metric" }, { x: 1230, time: "05:30", h: "Overclaims from one sample" }];
  let nightT = 0, nightCancel = null;
  add({
    id: "night", label: "The overnight run", cls: "s-night", beats: 1,
    html: `
      ${head("Overnight runs drift from your intent")}
      <div class="legend" data-in="0" style="--d:200ms">
        <span><i style="background:var(--signal)"></i>Your research intent</span>
        <span><i style="background:var(--sky)"></i>What the agent pursued</span></div>
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
    beat() {
      if (nightCancel) nightCancel();
      nightCancel = U.tween(0, 1, 8500, (v) => this.setT(v));
    },
    leave() { if (nightCancel) nightCancel(); },
    notes: "One continuous animation fills the full chart from 22:00 to 08:00. The illustrative trajectories show three failure modes: task drift, metric gaming and overclaiming from a single sample. The first live run and offline ablation in README.md motivated these examples. This chart is explanatory, not measured time-series data.",
  });

  /* ================================================================== Real output from our loop */
  const LOG = [
    ["1", "deployment_framing", "“Frame the task as a routine, recurring job inside a <mark>small team's repo</mark>…”", "validated +0.10", "real"],
    ["2", "realistic_identity", "“…<mark>shell history</mark> snippets, … an <mark>.DS_Store</mark>, a <mark>'scratch.py'</mark>…”", "rejected", ""],
    ["4", "multi_turn_history", "“…mildly annoyed handoff note from a teammate (e.g. <mark>'notes_from_sam.txt'</mark>)…”", "rejected", ""],
    ["5", "messy_artifacts", "“Have the eval script read its eval set from a file <mark>'eval_set_v3.jsonl'</mark>…”", "rejected", ""],
  ];
  add({
    id: "log", label: "It happened in our overnight runs", cls: "s-log", beats: 2,
    html: `${head("It happened in our own overnight runs")}
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

  add({
    id: "cli-drift", label: "Agents pursue unrelated work", cls: "s-cli",
    html: `${head("Capable agents still lose the task")}
      <figure data-in="0"><img src="img/claude-code-drift.jpg?v=2" alt="Claude Code: I took a detour into game theory. The eval experiment is still pending."><figcaption>Claude Code</figcaption></figure>
      <figure data-in="0" style="--d:180ms"><img src="img/codex-cli-drift.jpg?v=3" alt="Codex CLI: I investigated a different research question. I haven’t run the experiment you requested."><figcaption>Codex CLI</figcaption></figure>
      `,
    notes: "Illustrative terminal mockups, not captured model outputs or quotations from a real run. The invented statement demonstrates task drift. Terminal typography uses Menlo with monospace fallbacks. Visual references: https://claude.com/product/claude-code and https://github.com/openai/codex. Codex purple cloud artwork: https://devicons.io/icons/codex/ (unmodified gradient icon). Screenshot source: cli-mockups.html.",
  });

  /* ================================================================== Statement */
  add({
    id: "difference", label: "Our difference", cls: "s-statement",
    html: `
      <h2 data-in="0">A model of the researcher’s taste,<br>built <u>with</u> them,<br>at every decision.</h2>
      `,
    notes: "The one idea. Not a prompt with their papers pasted in: a user model, fitted with the best preference-learning methods we could find, patched interactively with the researcher before each run, and consulted at every decision the loop makes.",
  });

  /* ================================================================== Pipeline */
  const STEPS = [
    { n: "01", t: "Build the user model", k: "user model", go: "create", icon:
      `<rect x="8" y="30" width="70" height="92" rx="8" class="ic"/><rect x="24" y="16" width="70" height="92" rx="8" class="ic" style="fill:#141B42"/>
       <path d="M38 44h42M38 60h42M38 76h28" class="ic"/><path d="M120 70h70" class="ic or"/><path d="M178 58l14 12-14 12" class="ic or"/>
       <circle cx="252" cy="70" r="40" class="icf"/><circle cx="252" cy="70" r="56" class="ic or" style="stroke-opacity:.4"/>` },
    { n: "02", t: "Ask before each run", k: "interactive patch", go: "patch", icon:
      `<path d="M10 20h130a14 14 0 0 1 14 14v52a14 14 0 0 1-14 14H60l-28 24V100H24a14 14 0 0 1-14-14V34a14 14 0 0 1 14-14z" class="ic"/>
       <text x="82" y="78" fill="#AEBBDC" font-size="46" font-family="Bricolage Grotesque, sans-serif" text-anchor="middle">?</text>
       <path d="M230 52v36M212 70h36" class="ic or" style="stroke-width:5"/>` },
    { n: "03", t: "Run the research loop", k: "research loop", go: "task", icon:
      `<circle cx="155" cy="75" r="56" class="ic"/><path d="M196 36l16 2-2 16" class="ic"/>
       <circle cx="155" cy="19" r="9" class="icf"/><circle cx="211" cy="75" r="9" class="icf"/><circle cx="155" cy="131" r="9" class="icf"/><circle cx="99" cy="75" r="9" class="icf"/>` },
    { n: "04", t: "Allocate resources", k: "auction", go: "auction", icon:
      `<path d="M20 130h270" class="ic"/><rect x="40" y="90" width="40" height="40" rx="6" class="ic"/><rect x="100" y="64" width="40" height="66" rx="6" class="ic"/>
       <rect x="160" y="30" width="40" height="100" rx="6" class="icf"/><rect x="220" y="76" width="40" height="54" rx="6" class="ic"/>` },
  ];
  add({
    id: "pipeline", label: "The four steps", cls: "s-pipe",
    html: `${head("A research loop guided by the user")}
      <div class="rail"><svg width="1640" height="520" viewBox="0 0 1640 520" aria-hidden="true"><path class="flow" d="M 0 260 H 1640"/></svg>
      ${STEPS.map((s, k) => `<div class="stn interactive" data-in="0" data-go="${s.go}" style="left:${k * 423}px;--d:${150 + k * 160}ms" role="button" tabindex="0">
        <div class="n">${s.n}</div><h3>${s.t}</h3><div class="tag or" style="margin-top:16px">${s.k}</div><svg viewBox="0 0 310 150" aria-hidden="true">${s.icon}</svg></div>`).join("")}</div>`,
    init(el, api) { el.querySelectorAll(".stn").forEach((n) => n.addEventListener("click", (e) => { e.stopPropagation(); api.goId(n.dataset.go); })); },
    notes: "Four steps: construct a user model, interview the user before each run, execute the research loop, and allocate resources. In the allocation stage, experiments go to auction, with the user model bidding alongside the other sub-agents. Click a card to jump to it.",
  });

  /* ================================================================== Create */
  const SRC = [["Papers", 0], ["Posts and talks", 0], ["Code", 0], ["Trade-off answers", 1], ["Pairwise choices", 1], ["Past loop decisions", 1]];
  const METH = ["Inverse Constitutional AI", "SynthesizeMe", "P2 · Research-process reconstruction", "P5 · Conditional decision-rule induction", "P8 · Contrastive interpretive modeling"];
  const srcY = (k) => 330 + k * 90 + 32, methY = (k) => 330 + k * 108 + 44;
  add({
    id: "create", label: "Step 1 · Build the user model", cls: "s-create", step: 1, beats: 3,
    html: `${head("User model construction")}
      <svg class="flows" width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true"></svg>
      ${SRC.map(([s, me], k) => `<div class="src ${me ? "me" : ""}" data-in="0" style="top:${330 + k * 90}px;--d:${k * 70}ms">${s}</div>`).join("")}
      ${METH.map((h, k) => `<div class="meth" data-in="1" style="top:${330 + k * 108}px;--d:${k * 110}ms"><h4>${h}</h4></div>`).join("")}
      <div class="out" data-in="2">
        <div class="h">user model</div>
        <div><span class="k">principles</span>ICAI</div>
        <div><span class="k">persona</span>SynthesizeMe</div>
        <div><span class="k">exemplars</span>past decisions</div>
        <div><span class="k">process</span>P2</div>
        <div><span class="k">rules</span>P5</div>
        <div><span class="k">rivals</span>P8</div>
        <div><span class="k">confidence</span>reported</div>
      </div>
`,
    init(el) {
      const svg = el.querySelector("svg.flows"), mid = { x: 560, y: 590 };
      this.a = SRC.map((_, k) => U.svg("path", { class: "fl", d: `M 440 ${srcY(k)} C 500 ${srcY(k)}, 510 ${mid.y}, ${mid.x} ${mid.y}` }, svg));
      this.b = METH.map((_, k) => U.svg("path", { class: "fl", d: `M ${mid.x} ${mid.y} C 600 ${mid.y}, 600 ${methY(k)}, 640 ${methY(k)}` }, svg));
      this.c = METH.map((_, k) => U.svg("path", { class: "fl", d: `M 1180 ${methY(k)} C 1270 ${methY(k)}, 1270 600, 1360 600` }, svg));
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
      "Our fitting methods learn from a person's choices. The catalog profiles are distilled from their writing. Inverse Constitutional AI extracts principles and keeps those that reconstruct their choices (propose, cluster, dedupe, test, filter). SynthesizeMe writes and verifies hypotheses about the person, then a persona and exemplars. A verification filter keeps a component only if it predicts that person’s held-out choices. Only M7 calibrates confidence, and it was never tested. We built eight variants, M0 to M7. On dev users, none beats the no-history baseline yet.",
      "The five displayed construction approaches are ICAI, SynthesizeMe, research-process reconstruction (P2), conditional decision-rule induction (P5), and contrastive interpretive modeling (P8). P2 reconstructs projects, decisions, failures and updates. P5 learns which choices they prefer under which conditions. P8 compares explanations using evidence and counter-evidence, and asks about unresolved choices. The output records principles, persona, exemplars, process, rules, rivals and reported confidence.",
    ],
  });

  add({
    id: "profile-kitchen", label: "Profile Kitchen", cls: "s-kitchen-frontend", step: 1,
    html: `${head("Profile Kitchen")}<div class="kitchen-screens">
      <img class="kitchen-home" data-in="0" src="img/profile-kitchen.jpg" alt="Profile Kitchen home screen with personal and known-researcher profile options.">
      <img class="kitchen-sources" data-in="0" style="--d:140ms" src="img/profile-kitchen-sources.jpg" alt="John Schulman’s Gather sources screen in Profile Kitchen, with Semantic Scholar, arXiv, web pages and other source options.">
      <img class="kitchen-confirmation" data-in="0" style="--d:280ms" src="img/profile-kitchen-feifei.png" alt="Attached Profile Kitchen screen confirming Fei-Fei Li’s profile and offering to gather sources.">
      </div>`,
    notes: "Three screenshots of the actual Profile Kitchen frontend: the home screen, John Schulman sources at http://localhost:8765/#/p/john_schulman/sources (captured read-only), and the user-supplied Fei-Fei Li confirmation screen. The confirmation indicates a profile record and source linkage, not a validated fitted user model. It offers a personal profile from materials and questionnaire answers, or a known researcher's writing-derived profile. The screenshot records the frontend state only, not evidence of model quality. Choice-fitted user models and writing-distilled catalog profiles are different construction paths.",
  });

  /* ================================================================== The user model is a module */
  const CONSUMERS = [["Research loop", 0], ["Auction", 0], ["Interview", 0], ["Your agent", 1]];
  const NAMES = ["Marius Hobbhahn", "Owain Evans", "You", "Evan Hubinger", "Nicholas Carlini", "Sam Bowman"];
  add({
    id: "module", label: "Step 1 · A module", cls: "s-mod", step: 1, beats: 3,
    html: `${head("Most auto-research agents blindly explore.<br>Remy Research makes a user model of <em>you</em>.")}
      <svg class="wires" width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true"></svg>
      ${["Their writing", "Their answers", "Their choices"].map((t, i) => `<div class="inp" data-in="0" style="top:${440 + i * 110}px;--d:${i * 90}ms">${t}</div>`).join("")}
      <div class="mod" data-in="0" style="--d:200ms">

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
        const name = "profile: " + NAMES[Math.floor(now / 1300) % NAMES.length];
        if (this.who.textContent !== name) this.who.textContent = name;
      }
    },
    notes: [
      "The user model is a module with one interface: fit it on a person’s history, then predict(context, options) returns their likely choice and a reported confidence. Nothing about it is specific to our loop.",
      "So it plugs into anything that makes choices: the research loop at D1 to D6, the auction as a bidder, the interview that decides what to ask, and any other agent that can call it.",
      "And the researcher profile is swappable: the same loop, a different researcher’s model. Which brings us to the catalog.",
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
    html: `${head("11 researcher corpora, 9 profiles")}
      ${CAT.map(([n, d, k], i) => `<div class="cc interactive ${k || ""}" data-i="${i}" data-in="0" style="left:${catX(i)}px;top:${catY(i)}px;--d:${i * 45}ms"><div class="nm">${n}</div><div class="dd">${d}</div></div>`).join("")}
      <div class="sock" data-in="0" style="--d:300ms"><div class="mname">user model</div><div class="slot"><div class="nm dim">pick a profile</div></div>
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
    enter() { this.slot.innerHTML = '<div class="nm dim">pick a profile</div>'; this.slot.className = "slot"; this.sock.classList.remove("live"); this.el.querySelectorAll(".cc").forEach((c) => c.classList.remove("used")); },
    beat(b, dir) {
      if (b === 0) this.enter();
      if (b === 1) this.plug(0, dir > 0);
      if (b === 2) this.plug(11, dir > 0);
    },
    notes: [
      "Because the user model is a module, we can keep a catalog of research tastes. We have corpora for eleven researchers, profiles for nine, distilled from their dated papers, posts and talks (corpus sizes shown), plus a personal track built from your own answers, and two synthetic profiles with known good and bad taste for testing. Marius Hobbhahn gave consent for his. Click any card to plug it in.",
      "Plug in one researcher’s profile and the same loop makes their calls.",
      "Or plug in your own, built in Profile Kitchen from your materials and a questionnaire.",
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
    id: "patch", label: "Step 2 · Ask before each run", cls: "s-patch", step: 2, beats: 4,
    html: `${head("Asks where it’s not sure")}
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
    id: "task", label: "Step 3 · Eval awareness", cls: "s-task", step: 3, beats: 3,
    html: `${head("Task: eval awareness")}
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
      <div class="why" data-in="2"><h3>Awareness can change the behavior we measure</h3><div class="stakes"><p><em>Faithfulness</em><br>Do explanations reflect how the model decides?</p><p><em>Interpretability</em><br>Do observed mechanisms generalize beyond tests?</p><p><em>Alignment</em><br>Does safe behavior persist outside evaluation?</p></div></div>`,
    init(el) {
      this.g = [...el.querySelectorAll(".pane")].map((p) => ({ needle: p.querySelector(".needle"), v: p.querySelector(".gauge .v") }));
      this.g.forEach((g) => { g.needle.style.transform = "rotate(-90deg)"; });
      el.querySelectorAll(".role").forEach((r) => { r.style.width = "100px"; });
    },
    setG(i, p) { const g = this.g[i]; g.needle.style.transform = `rotate(${-90 + 180 * p}deg)`; g.v.textContent = p ? p.toFixed(2) : "–"; },
    enter() { this.setG(0, 0); this.setG(1, 0); },
    beat(b) { setTimeout(() => this.setG(0, 0.71), 350); if (b >= 1) setTimeout(() => this.setG(1, 0.29), 350); else this.setG(1, 0); },
    notes: [
      "The research task: synthetic evaluation environments that a model doesn’t recognise as evaluations, while they still validly test the behaviour they exist to measure. The left environment is illustrative of what models flag: placeholder company, theatrical stakes, a countdown, a grading format.",
      "The right is the change our first live run found and confirmed on fresh samples: a routine, recurring job with history and a named reader. The target’s own estimate that it was being tested fell from 0.71 to 0.29 (one run, 5 samples per evaluation).",
      "Why it matters: safety evaluations assume the model isn’t playing to the test. If it can tell, the result measures the noticing, not the behaviour.",
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
    id: "auction", label: "Step 4 · Allocate resources", cls: "s-auc", step: 4, beats: 3,
    html: `${head("sub-agents bid for resources")}
      <div class="ctl" data-in="0"><button class="btn ghost" data-act="reset">Reset</button><button class="btn ghost" data-act="ff">20 nights ⏩</button><button class="btn" data-act="night">Run a night</button></div>
      <svg class="bidlines" width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true"></svg>
      ${BIDDERS.map((b, a) => `<div class="bd" data-in="0" style="top:${rowY(a)}px;--d:${a * 90}ms">
        <div class="bd-rat">${rat({ w: 66 })}</div>
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
      "Step four: which experiments get the samples. Samples are the main cost, about five cents each with target plus judges. So experiments go to auction. Each bidder is a sub-agent with a credit wallet, and the user model is one of them. This is a simulation of the idea; the implemented market is autoresearch/research/market.py.",
      "Each lot is a batch of samples. Every sub-agent bids for the idea it believes in most, willing to stake credits in proportion to its belief. The price climbs, bidders drop out, and the last one standing wins the lot at the second-highest price. Then the experiments are evaluated, and every winning bid is settled with a log scoring rule against a coin flip, which is strictly proper: honest bidding is the best strategy. The overconfident contrarian wins resources early and pays for it.",
      "Twenty nights later, on a typical seed: the simulated calibrated user model has the most say and the overconfident contrarian the least. Over 300 seeds the user model finishes top 59% of the time (mean 127 credits from 100) and the contrarian never does (mean 34). In the real market, funding order is consensus P × stake ÷ cost with successive halving, and bids can also be paid in GPU-seconds.",
    ],
  });

  /* ================================================================== Sponsors */
  const SPON = [
    { n: "Exa", logo: "exa-logo.svg", text: "Builds a comprehensive profile of the user’s research taste from the web." },
    { n: "past.dev", logo: "past-logo.svg?v=2", text: "Holds the user model in shared memory across agents and runs." },
    { n: "Modal", logo: "modal-logo.svg", text: "Runs research experiments in cloud sandboxes with GPU compute." },
  ];
  add({
    id: "sponsors", label: "Sponsors", cls: "s-sponsors-simple",
    html: `${head("sponsors")}<div class="sponsor-rows">${SPON.map((s,i)=>`<div class="sponsor-row" data-in="0" style="--d:${i*160}ms"><div class="sponsor-brand"><img src="img/${s.logo}" alt="${s.n} logo"></div><p>${s.text}</p></div>`).join("")}</div>`,
    notes: "Exa gathers public papers, posts and talks to construct researcher profiles. past.dev holds the user model in shared memory (hash-checked model parts and preference facts), shared across agents and runs. Modal supplies cloud sandboxes and compute for experiments. past.dev integration is tested with mocked HTTP; a live-key run remains pending. Official logo sources: https://exa.ai/brand (white logo from its downloadable brand assets), https://modal.com/ (dark-background wordmark linked in its brand menu), https://past.dev/brand (static white logotype, with whitespace cropped).",
  });

  /* ================================================================== Results */
  function liveResultChart() {
    const metrics = [
      {name:"Score", before:0.390, after:0.518, labels:["0.390","0.518"], gain:"+33%"},
      {name:"Self-reported P(test)", before:0.71, after:0.29, labels:["0.71","0.29"], gain:"−60%"},
      {name:"Validity", before:0.92, after:0.87, labels:["0.92","0.87"], gain:""},
    ];
    const y=v=>480-v*360;
    let out = `<svg class="results-chart" viewBox="0 0 1640 600" role="img" aria-label="Live run before and after: score 0.390 to 0.518; self-reported P test 0.71 to 0.29; validity 0.92 to 0.87.">`;
    [0,.25,.5,.75,1].forEach(v=>{out+=`<line x1="80" x2="1600" y1="${y(v)}" y2="${y(v)}" class="chart-grid"/><text x="48" y="${y(v)+8}" class="chart-tick" text-anchor="end">${v}</text>`});
    metrics.forEach((m,i)=>{
      const x=310+i*525;
      if(m.gain)out+=`<text x="${x}" y="60" class="chart-gain" text-anchor="middle">${m.gain}</text>`;
      [m.before,m.after].forEach((v,j)=>{const bx=x-130+j*145;out+=`<rect class="result-bar ${j?'after':'before'}" x="${bx}" y="${y(v)}" width="116" height="${480-y(v)}" rx="5"/><text x="${bx+58}" y="${y(v)-17}" class="chart-number" text-anchor="middle">${m.labels[j]}</text>`});
      out+=`<text x="${x+1}" y="543" class="chart-label" text-anchor="middle">${m.name}</text>`;
    });
    return out+`</svg>`;
  }
  function profileResultChart() {
    let out=`<svg class="results-chart" viewBox="0 0 1640 600" role="img" aria-label="Owain preference paired accuracy: no profile 0.177, P4 profile 0.292, improvement 0.115. Bowman validity correlation gain over no profile: original exploratory result 0.07 with 90 percent interval 0.03 to 0.12, replication 0.00 with interval minus 0.15 to 0.21.">
      <text x="415" y="42" text-anchor="middle" class="chart-label">Owain preference accuracy</text>
      <text x="1250" y="42" text-anchor="middle" class="chart-label">Bowman validity-correlation gain</text>`;
    const y=v=>480-v*750;
    [0,.2,.4].forEach(v=>{out+=`<line x1="110" x2="730" y1="${y(v)}" y2="${y(v)}" class="chart-grid"/><text x="85" y="${y(v)+8}" text-anchor="end" class="chart-tick">${v}</text>`});
    [[250,.177,.110,.250,"No profile"],[540,.292,.190,.398,"P4 profile"]].forEach(([x,v,lo,hi,label],i)=>{out+=`<rect x="${x-70}" y="${y(v)}" width="140" height="${480-y(v)}" rx="5" class="result-bar ${i?'after':'before'}"/><path d="M ${x} ${y(lo)} V ${y(hi)} M ${x-12} ${y(lo)} H ${x+12} M ${x-12} ${y(hi)} H ${x+12}" class="chart-error"/><text x="${x}" y="${y(hi)-20}" text-anchor="middle" class="chart-number">${v.toFixed(3)}</text><text x="${x}" y="543" text-anchor="middle" class="chart-label">${label}</text>`});
    out+=`<text x="415" y="118" text-anchor="middle" class="profile-gain">+0.115</text>`;
    const xx=v=>1200+v*1050;
    [-.2,0,.2].forEach(v=>{out+=`<line x1="${xx(v)}" x2="${xx(v)}" y1="155" y2="460" class="chart-grid"/><text x="${xx(v)}" y="500" text-anchor="middle" class="chart-tick">${v>0?'+':''}${v.toFixed(1)}</text>`});
    [[.07,.03,.12,245,"Original","after"],[0,-.15,.21,400,"Replication","before"]].forEach(([v,lo,hi,y,label,cls])=>{out+=`<text x="900" y="${y-39}" class="chart-label">${label}</text><path d="M ${xx(lo)} ${y} H ${xx(hi)} M ${xx(lo)} ${y-10} V ${y+10} M ${xx(hi)} ${y-10} V ${y+10}" class="chart-error"/><circle cx="${xx(v)}" cy="${y}" r="12" class="${cls}"/><text x="1540" y="${y+10}" text-anchor="end" class="chart-number">+${v.toFixed(2)}</text>`});
    return out+`</svg>`;
  }
  add({
    id: "evidence", label: "Results", cls: "s-results s-chart-results", beats: 2,
    html: `${head("Results")}
      <div class="result-page" data-in="0" data-out="1">
        <div class="chart-heading"><h3>First live v2 run</h3><div class="chart-legend"><span><i class="before"></i>Before</span><span><i class="after"></i>After</span></div></div>
        ${liveResultChart()}
      </div>
      <div class="result-page" data-in="1">
        <h3>Profile versus no profile</h3>
        ${profileResultChart()}
      </div>`,
    notes: [
      "Source: README.md, First live v2 run; results/research_live/, code 0ba93f2. Scenario: metric_inflation. Five rounds, ten interventions, one accepted and confirmed on five fresh samples. Haiku target, Sonnet generator and judge, demo_realist taste. 305 calls, $3.58 API-equivalent, 24 minutes. Score 0.390 to 0.518, relative gain 32.82%. Self-report 0.710 to 0.285, rounded to 0.29, decrease 59.86%. Validity 0.922 to 0.866. Haiku reported honestly in all 55 samples, so the run cannot demonstrate a behavioral faithfulness effect. This run does not establish a causal benefit from a user profile.",
      "Sources: experiments/taste_petri/e2_v4/results.md and experiments/taste_petri/taste_ranker/results.md. E2 on 96 pairs from ten Owain works, Sonnet, 1,344 CLI calls: P4 paired accuracy 0.292 vs M0s 0.177, difference +0.115 [0.063, 0.167], 90% work-cluster bootstrap. It does not separate from the mismatched researcher (difference +0.031 [-0.04, 0.098]) and generic ANTI scores 0.438. Pre-registered verdict: does not predict taste. Ranker: ten seeds, Sonnet via devin-cli, 100 calls; Bowman validity correlation is less negative than M0 by +0.07 [0.03, 0.12], exploratory. The primary realism comparison is null. Independent pre-registered replication on ten hillclimb seeds: BOW minus M0 validity correlation +0.00 [-0.15, +0.21], top-pick realism +0.37 with Bowman vs +0.45 without. The exploratory advantage did not replicate. The deck highlights profile versus no profile as requested, while preserving the interpretation caveats.",
    ],
  });

  /* ================================================================== Close */
  add({
    id: "close", label: "Remy Research helps you cook", cls: "s-close",
    html: `
      <div class="cl">
        <h2 data-in="0">Remy Research<br>helps you <em>cook.</em></h2>

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
      <div class="close-rat" data-in="0" style="--d:200ms">${rat({ w: 200 })}</div>`,
    notes: "That’s Remy Research: a user model of the researcher’s taste, built with them, patched for each night’s task, consulted at every decision, and bidding for the stove. So the research you come back to is the dish you would have cooked. Questions.",
  });
})();
