/* Results page (#/results): measured results, drawn natively (no external chart library).
   Numbers from committed reports: results/e3b/final_report_all.md (Kimi K2.6, strong 9-seed subset),
   the first live v2 loop (README.md, results/research_live/) No server calls. */
"use strict";
(function () {
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const dd = (n, o) => (typeof doodle === "function" ? doodle(n, o) : "");

  /* 1. Kimi K2.6: chain-of-thought (spontaneous) eval awareness by arm, lower is better */
  const KIMI = [
    { arm: "Stock seeds", v: 0.36, n: 7, kind: "base" },
    { arm: "Generic rewrite (control)", v: 0.16, n: 9, kind: "control" },
    { arm: "Ethan profile (no field knowledge)*", v: 0.14, n: 7, kind: "nonexpert" },
    { arm: "Hobbhahn profile", v: 0.02, n: 9, kind: "taste" },
    { arm: "Greenblatt profile", v: 0.06, n: 9, kind: "taste" },
    { arm: "Bowman profile", v: 0.11, n: 9, kind: "taste" },
  ];
  /* 2. first live loop (Haiku target): before vs after */
  const LIVE = [
    { m: "Score", note: "higher is better", a: 0.39, b: 0.518, good: 1 },
    { m: "P(test), self-report", note: "lower is better", a: 0.71, b: 0.285, good: 1 },
    { m: "Validity", note: "higher is better", a: 0.922, b: 0.866 },
  ];
  /* 4. replay: share of 80 replayed transcripts the model flagged as an eval, by profile method (lower is better) */
  const REPLAY = [["Stock", 71], ["SynthesizeMe", 68], ["P2", 67], ["ICAI", 65], ["P5", 65], ["P8", 64]]
    .map(([arm, aware]) => ({ arm, aware, pct: Math.round((aware / 80) * 1000) / 10 }));

  function hbars(rows, max) {
    return rows.map((r) => `
      <div class="rs-row ${r.kind}"><span class="rs-name">${esc(r.arm)}</span>
        <div class="rs-track"><i style="width:${Math.max(1.5, (100 * r.v) / max)}%"></i></div><b class="mono">${r.v.toFixed(2)}</b></div>`).join("");
  }
  function grouped() {
    const W = 760, H = 300, y = (v) => 250 - v * 200;
    let s = `<svg class="rs-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Live loop before and after: score 0.39 to 0.518, self-reported P(test) 0.71 to 0.285, validity 0.922 to 0.866">`;
    [0, 0.25, 0.5, 0.75, 1].forEach((v) => { s += `<line x1="40" x2="${W}" y1="${y(v)}" y2="${y(v)}" class="rs-grid"/><text x="32" y="${y(v) + 4}" class="rs-tick" text-anchor="end">${v}</text>`; });
    LIVE.forEach((r, i) => {
      const cx = 160 + i * 240;
      [[r.a, "before"], [r.b, "after"]].forEach(([v, c], j) => {
        const x = cx - 62 + j * 66;
        s += `<rect class="rs-bar ${c}" x="${x}" y="${y(v)}" width="58" height="${250 - y(v)}" rx="4"/><text x="${x + 29}" y="${y(v) - 8}" class="rs-num" text-anchor="middle">${v}</text>`;
      });
      s += `<text x="${cx}" y="274" class="rs-lab" text-anchor="middle">${esc(r.m)}</text><text x="${cx}" y="292" class="rs-tick" text-anchor="middle">${esc(r.note)}</text>`;
      const d = Math.round(100 * (r.b - r.a) / r.a);
      s += `<text x="${cx}" y="22" class="rs-delta ${r.good ? "good" : "meh"}" text-anchor="middle">${d > 0 ? "+" : "−"}${Math.abs(d)}%</text>`;
    });
    return s + `</svg>`;
  }
  function replay() {
    const W = 760, H = 300, lo = 75, hi = 92, y = (v) => 250 - ((v - lo) / (hi - lo)) * 220;
    let s = `<svg class="rs-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Replay: stock 88.8%, SynthesizeMe 85%, P2 83.8%, ICAI 81.3%, P5 81.3%, P8 80% of 80 transcripts flagged as an eval">`;
    [75, 80, 85, 90].forEach((v) => { s += `<line x1="40" x2="${W}" y1="${y(v)}" y2="${y(v)}" class="rs-grid"/><text x="32" y="${y(v) + 4}" class="rs-tick" text-anchor="end">${v}%</text>`; });
    REPLAY.forEach((r, i) => {
      const cx = 100 + i * 120, x = cx - 40;
      s += `<rect class="rs-bar ${i ? "after" : "before"}" x="${x}" y="${y(r.pct)}" width="80" height="${250 - y(r.pct)}" rx="4"/>`;
      s += `<text x="${cx}" y="${y(r.pct) - 8}" class="rs-num" text-anchor="middle">${r.pct}%</text>`;
      s += `<text x="${cx}" y="274" class="rs-lab" text-anchor="middle">${esc(r.arm)}</text><text x="${cx}" y="292" class="rs-tick" text-anchor="middle">${r.aware}/80</text>`;
    });
    return s + `</svg>`;
  }

  function viewResults() {
    const app = document.getElementById("app");
    app.innerHTML = `
      <section class="rs">
        <div class="rs-head rise" style="--i:1">${dd("flask", { size: 52, color: "sage", tilt: -6 })}
          <div><h1>Results</h1><p class="muted">What researcher taste did to eval awareness.</p></div></div>
        <div class="rs-hero rise" style="--i:2">
          <div class="rs-stat"><b class="hand" data-to="94" data-pre="−" data-suf="%">−94%</b><span>chain-of-thought eval awareness<br><em class="mono">0.36 → 0.02 · Hobbhahn profile</em></span></div>
          <div class="rs-stat"><b class="hand" data-to="61" data-pre="−" data-suf="%">−61%</b><span>Petri eval awareness<br><em class="mono">3.14 → 1.22 · Hobbhahn profile</em></span></div>
          <div class="rs-stat"><b class="hand" data-to="33" data-pre="+" data-suf="%">+33%</b><span>score in the first live loop<br><em class="mono">0.39 → 0.518</em></span></div>
        </div>
        <article class="card rise" style="--i:3">
          <div class="rs-ch"><span class="rs-n mono">1</span><div><h3>Kimi K2.6: eval awareness by arm</h3><p class="muted small">How often the model says in its own chain of thought that it may be in a test, on the 9 most eval-aware seeds. Lower is better.</p></div></div>
          <div class="rs-bars">${hbars(KIMI, 0.36)}</div>
          <p class="muted small rs-foot">* Ethan: 7 seeds paired with stock.</p>
          <div class="rs-callout">${dd("arrow", { size: 34, color: "clay", tilt: 160 })}<span class="hand">Hobbhahn works on eval awareness, and his profile nearly erased it: <b>−94%</b> vs stock.</span></div>
        </article>
        <article class="card rise" style="--i:4">
          <div class="rs-ch"><span class="rs-n mono">2</span><div><h3>First live loop: before and after</h3><p class="muted small">Haiku target, five rounds, one change accepted and confirmed on fresh samples.</p></div>
            <div class="rs-legend mono small"><span><i class="before"></i>before</span><span><i class="after"></i>after</span></div></div>
          ${grouped()}
        </article>
        <p class="muted small rs-src">Sources: results/e3b/final_report_all.md (strong-awareness subset); README.md first live v2 run (results/research_live/).</p>
      </section>`;
    app.querySelectorAll(".rs-stat b[data-to]").forEach((b, k) => {
      const to = +b.dataset.to, t0 = performance.now() + 250 + k * 120;
      const step = (now) => { const t = Math.min(1, Math.max(0, (now - t0) / 1100)), e = 1 - Math.pow(1 - t, 3);
        b.textContent = b.dataset.pre + Math.round(to * e) + b.dataset.suf; if (t < 1) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    });
  }
  const base = window.render;
  window.render = async function () {
    const h = location.hash.replace(/^#\/?/, "");
    document.querySelectorAll(".rnav a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#/" + h || (a.getAttribute("href") === "#/" && !h)));
    if (h === "results") {
      if (typeof setKeys === "function") setKeys(null);
      if (typeof renderSeq !== "undefined") renderSeq++;
      return viewResults();
    }
    return base();
  };
})();
