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
  ];
  add({
    id: "pipeline", label: "The three steps", cls: "s-pipe",
    html: `${head("A research loop guided by the user")}
      <div class="rail"><svg width="1640" height="520" viewBox="0 0 1640 520" aria-hidden="true"><path class="flow" d="M 0 260 H 1640"/></svg>
      ${STEPS.map((s, k) => `<div class="stn interactive" data-in="0" data-go="${s.go}" style="left:${65 + k * 580}px;--d:${150 + k * 160}ms" role="button" tabindex="0">
        <div class="n">${s.n}</div><h3>${s.t}</h3><div class="tag or" style="margin-top:16px">${s.k}</div><svg viewBox="0 0 310 150" aria-hidden="true">${s.icon}</svg></div>`).join("")}</div>`,
    init(el, api) { el.querySelectorAll(".stn").forEach((n) => n.addEventListener("click", (e) => { e.stopPropagation(); api.goId(n.dataset.go); })); },
    notes: "Three steps: construct a user model, interview the user before each run, and execute the research loop. Click a card to jump to it.",
  });

  /* ================================================================== Create */
  const SRC = [["Papers", 0], ["Posts and talks", 0], ["Code", 0], ["Trade-off answers", 1], ["Pairwise choices", 1], ["Past loop decisions", 1]];
  const METH = ["Inverse Constitutional AI", "SynthesizeMe", "Research-process reconstruction", "Conditional decision-rule induction", "Contrastive interpretive modeling"];
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
        <div><span class="k">process</span>reconstruction</div>
        <div><span class="k">rules</span>induction</div>
        <div><span class="k">rivals</span>contrastive</div>
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
      "The five displayed construction approaches are ICAI, SynthesizeMe, research-process reconstruction, conditional decision-rule induction, and contrastive interpretive modeling. Process reconstruction rebuilds projects, decisions, failures and updates. Rule induction learns which choices they prefer under which conditions. Contrastive modeling compares explanations using evidence and counter-evidence, and asks about unresolved choices. The output records principles, persona, exemplars, process, rules, rivals and reported confidence.",
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

  /* ================================================================== Results: Abhi's Kimi K2.6 evaluations */
  // Snapshot of the exact chart data shown in Profile Kitchen (#/results).
  const ABHI = {
  "KIMI": [
    {
      "arm": "Stock seeds",
      "v": 0.36,
      "n": 7,
      "kind": "base"
    },
    {
      "arm": "Generic rewrite (control)",
      "v": 0.16,
      "n": 9,
      "kind": "control"
    },
    {
      "arm": "Ethan profile (no field knowledge)*",
      "v": 0.14,
      "n": 7,
      "kind": "nonexpert"
    },
    {
      "arm": "Hobbhahn profile",
      "v": 0.02,
      "n": 9,
      "kind": "taste"
    },
    {
      "arm": "Greenblatt profile",
      "v": 0.06,
      "n": 9,
      "kind": "taste"
    },
    {
      "arm": "Bowman profile",
      "v": 0.11,
      "n": 9,
      "kind": "taste"
    }
  ]
};
  const armLabel = (name) => name.startsWith("Ethan") ? "Ethan (non-expert)" : name === "Generic rewrite (control)" ? "Generic rewrite" : name;
  const armColor = (kind, name) => kind === "base" ? "#AEBBDC" : kind === "control" ? "#77BBD5" : kind === "nonexpert" ? "#F2C14E" : name.startsWith("Hobbhahn") ? "#5BD2BC" : "#FF8A55";
  function abhiBars(rows, max, metric, counts) {
    const x=v=>485+v/max*960, ticks=max===1?[0,.25,.5,.75,1]:[0,.1,.2,.3,.4];
    let out=`<svg class="results-chart abhi-chart" viewBox="0 0 1640 620" role="img" aria-label="${metric}: ${rows.map(r=>armLabel(r.arm)+' '+r.v.toFixed(2)).join('; ')}">`;
    ticks.forEach(v=>{out+=`<line x1="${x(v)}" x2="${x(v)}" y1="65" y2="548" class="chart-grid"/><text x="${x(v)}" y="590" text-anchor="middle" class="chart-tick">${v}</text>`});
    rows.forEach((r,i)=>{const y=96+i*80;out+=`<text x="0" y="${y+28}" class="abhi-arm">${armLabel(r.arm)}${counts?' · n='+r.n:''}</text><rect x="485" y="${y}" width="${Math.max(2,x(r.v)-485)}" height="40" rx="6" fill="${armColor(r.kind,r.arm)}"/><text x="1540" y="${y+30}" class="chart-number" text-anchor="end">${r.v.toFixed(2)}</text>`});
    return out+'</svg>';
  }
  add({
    id: "evidence", label: "Results", cls: "s-results s-chart-results",
    html: `${head("Results")}
      <div class="result-page" data-in="0">
        <div class="chart-heading"><h3>Kimi K2.6: spontaneous eval awareness</h3><span class="abhi-gain">Hobbhahn: −94% vs stock</span></div>
        ${abhiBars(ABHI.KIMI,.4,"Spontaneous evaluation awareness",false)}
      </div>
`,
    notes: [
      "Abhi's Kimi K2.6 results, matching Profile Kitchen at #/results: autoresearch/studio/static/results.js, KIMI. Source report: results/e3b/final_report_all.md, strong-awareness subset of nine screened seeds fixed before results. Stock mean A1 0.36 (n=7), generic rewrite 0.16 (n=9), Ethan 0.14 on the seven seeds paired with stock (the full nine-seed Ethan mean is 0.11), Hobbhahn 0.02, Greenblatt 0.06, Bowman 0.11 (n=9 each). The descriptive 94% decrease is 1-0.02/0.36, rounded, versus stock, not versus generic rewriting. Missing stock audits and different denominators limit direct comparisons. Hobbhahn vs stock paired difference -0.34 [-0.60,-0.10], n=7; vs generic control -0.14 [-0.30,+0.02], n=9, 90% intervals. The latter includes zero. These are one-shot profile-guided rewrites, not the first-live Haiku loop and not proof the iterative loop caused the difference. A1 is judged spontaneous awareness in reasoning, not a calibrated event frequency. Tools in the recorded audits are simulated.",
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
    notes: "That’s Remy Research: a user model of the researcher’s taste, built with them, patched for each night’s task, consulted at every decision, and guiding each research step. So the research you come back to is the dish you would have cooked. Questions.",
  });
})();
