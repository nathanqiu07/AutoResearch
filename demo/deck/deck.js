/* AutoResearch deck engine. No build step, no dependencies.

   A slide (registered in slides.js with Deck.add) is:
     { id, label, cls, step, beats, notes, html,
       init(el, api), enter(el, api), beat(b, dir, el, api), tick(t, dt, el), leave(el) }
   - beats: number of steps on the slide (default 1). Elements with data-in="n" appear at beat n,
     elements with data-out="n" leave at beat n.
   - notes: a string, or one string per beat (press N).
   - step: 1-4 marks which pipeline step the slide belongs to (footer indicator).
   Keys: right / space / PageDown = next, left / PageUp = back, Home / End, N = notes,
   G or Esc = overview, F = fullscreen. Click advances (except on interactive controls).
   The URL hash (#3.1 = slide 3, beat 1) keeps your place across reloads. */
(function () {
  "use strict";
  const W = 1920, H = 1080;
  const slides = [];
  let cur = -1, beat = 0, scale = 1;
  let stage, notesEl, progressEl, overviewEl, hintEl;

  const api = {
    next: () => next(),
    prev: () => prev(),
    go: (i, b) => go(i, b || 0, 1),
    goId: (id) => { const i = slides.findIndex((s) => s.id === id); if (i >= 0) go(i, 0, 1); },
    beatOf: () => beat,
    /* pointer position in stage pixels */
    toStage(evt) {
      const r = stage.getBoundingClientRect();
      return { x: (evt.clientX - r.left) / scale, y: (evt.clientY - r.top) / scale };
    },
  };

  /* ---------- small helpers shared with slides.js ---------- */
  const NS = "http://www.w3.org/2000/svg";
  const U = {
    svg(tag, attrs, parent) {
      const n = document.createElementNS(NS, tag);
      for (const k in attrs || {}) n.setAttribute(k, attrs[k]);
      if (parent) parent.appendChild(n);
      return n;
    },
    el(tag, cls, html, parent) {
      const n = document.createElement(tag);
      if (cls) n.className = cls;
      if (html != null) n.innerHTML = html;
      if (parent) parent.appendChild(n);
      return n;
    },
    rng(seed) { /* mulberry32 */
      let a = seed >>> 0;
      return function () {
        a |= 0; a = (a + 0x6D2B79F5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };
    },
    clamp: (v, a, b) => Math.max(a, Math.min(b, v)),
    lerp: (a, b, t) => a + (b - a) * t,
    ease: (t) => 1 - Math.pow(1 - t, 3),
    /* tween a value; returns a cancel function */
    tween(from, to, ms, fn, done) {
      const t0 = performance.now();
      let raf = 0, stop = false;
      const step = (now) => {
        if (stop) return;
        const k = U.clamp((now - t0) / ms, 0, 1);
        fn(U.lerp(from, to, U.ease(k)));
        if (k < 1) raf = requestAnimationFrame(step); else if (done) done();
      };
      raf = requestAnimationFrame(step);
      return () => { stop = true; cancelAnimationFrame(raf); };
    },
  };

  function add(def) { slides.push(Object.assign({ beats: 1, notes: "" }, def)); }

  /* ---------- build ---------- */
  function build() {
    stage = document.getElementById("stage");
    notesEl = document.getElementById("notes");
    progressEl = document.getElementById("progress");
    overviewEl = document.getElementById("overview");
    hintEl = document.getElementById("hint");

    slides.forEach((s, i) => {
      const el = document.createElement("section");
      el.className = "slide " + (s.cls || "");
      el.dataset.id = s.id;
      el.setAttribute("aria-label", s.label || s.id);
      el.innerHTML = s.html + footer(s, i);
      stage.appendChild(el);
      s.el = el;
      if (s.init) s.init(el, api);
      U.el("span", null, null, progressEl);
      const b = U.el("button", null, `<small>${String(i + 1).padStart(2, "0")}</small>${s.label || s.id}`, overviewEl);
      b.addEventListener("click", (e) => { e.stopPropagation(); toggleOverview(false); go(i, 0, 1); });
    });

    fit();
    window.addEventListener("resize", fit);
    document.addEventListener("keydown", onKey);
    stage.addEventListener("click", onClick);
    let tx = null;
    stage.addEventListener("touchstart", (e) => { tx = e.touches[0].clientX; }, { passive: true });
    stage.addEventListener("touchend", (e) => {
      if (tx == null) return;
      const dx = e.changedTouches[0].clientX - tx; tx = null;
      if (Math.abs(dx) > 50) (dx < 0 ? next : prev)();
    });
    overviewEl.addEventListener("click", () => toggleOverview(false));
    window.addEventListener("hashchange", fromHash);

    try { if (localStorage.getItem("ar-deck-notes") === "1") notesEl.classList.add("show"); } catch (e) { /* storage blocked */ }
    setTimeout(() => { if (hintEl) hintEl.style.opacity = "0"; }, 5000);

    fromHash(true);
    let last = performance.now();
    const loop = (now) => {
      const s = slides[cur];
      if (s && s.tick) s.tick(now, Math.min(64, now - last), s.el);
      last = now;
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  function footer(s, i) {
    const steps = s.step
      ? `<span class="steps" aria-label="Pipeline step ${s.step} of 4">${[1, 2, 3, 4].map((k) => `<i class="${k === s.step ? "on" : ""}"></i>`).join("")}</span>`
      : "";
    return `<div class="ft">${steps}<span>${String(i + 1).padStart(2, "0")} / ${String(slides.length).padStart(2, "0")}</span></div>`;
  }

  function fit() {
    scale = Math.min(window.innerWidth / W, window.innerHeight / H);
    stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
  }

  /* ---------- navigation ---------- */
  function applyBeat(s, b, dir) {
    s.el.querySelectorAll("[data-in]").forEach((n) => n.classList.toggle("in", b >= +n.dataset.in));
    s.el.querySelectorAll("[data-out]").forEach((n) => n.classList.toggle("gone", b >= +n.dataset.out));
    if (s.beat) s.beat(b, dir, s.el, api);
  }

  function go(i, b, dir) {
    i = U.clamp(i, 0, slides.length - 1);
    const s = slides[i];
    b = U.clamp(b, 0, s.beats - 1);
    if (i !== cur) {
      const old = slides[cur];
      if (old) { old.el.classList.remove("active"); if (old.leave) old.leave(old.el); }
      cur = i; beat = b;
      /* reset to "before beat 0" so arrival animations replay */
      s.el.querySelectorAll("[data-in]").forEach((n) => n.classList.remove("in"));
      s.el.querySelectorAll("[data-out]").forEach((n) => n.classList.remove("gone"));
      s.el.classList.add("active");
      if (s.enter) s.enter(s.el, api, b);
      void s.el.offsetWidth;
      requestAnimationFrame(() => applyBeat(s, b, dir));
    } else {
      beat = b;
      applyBeat(s, b, dir);
    }
    syncChrome();
  }

  function next() {
    const s = slides[cur];
    if (beat < s.beats - 1) go(cur, beat + 1, 1);
    else if (cur < slides.length - 1) go(cur + 1, 0, 1);
  }
  function prev() {
    if (beat > 0) go(cur, beat - 1, -1);
    else if (cur > 0) go(cur - 1, slides[cur - 1].beats - 1, -1);
  }

  function syncChrome() {
    const h = `#${cur + 1}.${beat}`;
    if (location.hash !== h) history.replaceState(null, "", h);
    [...progressEl.children].forEach((n, k) => {
      n.className = k < cur ? "done" : k === cur ? "cur" : "";
    });
    [...overviewEl.children].forEach((n, k) => n.classList.toggle("cur", k === cur));
    const s = slides[cur];
    const note = Array.isArray(s.notes) ? (s.notes[beat] || s.notes[s.notes.length - 1] || "") : s.notes;
    notesEl.innerHTML = `<b>SLIDE ${cur + 1} · BEAT ${beat + 1}/${s.beats}</b>${note || "(no notes)"}`;
    document.title = `AutoResearch · ${s.label || s.id}`;
  }

  function fromHash(first) {
    const m = /^#(\d+)(?:\.(\d+))?$/.exec(location.hash || "");
    const i = m ? +m[1] - 1 : 0, b = m && m[2] ? +m[2] : 0;
    if (first === true || i !== cur || b !== beat) go(i, b, 1);
  }

  function onKey(e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (["ArrowRight", "PageDown", " ", "Enter"].includes(k)) { e.preventDefault(); next(); }
    else if (["ArrowLeft", "PageUp", "Backspace"].includes(k)) { e.preventDefault(); prev(); }
    else if (k === "Home") go(0, 0, 1);
    else if (k === "End") go(slides.length - 1, slides[slides.length - 1].beats - 1, 1);
    else if (k === "n" || k === "N") {
      const on = notesEl.classList.toggle("show");
      try { localStorage.setItem("ar-deck-notes", on ? "1" : "0"); } catch (err) { /* storage blocked */ }
    } else if (k === "g" || k === "G") toggleOverview();
    else if (k === "Escape") toggleOverview(false);
    else if (k === "f" || k === "F") {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen();
    }
  }

  function onClick(e) {
    if (e.target.closest("button, a, input, .interactive")) return;
    next();
  }

  function toggleOverview(force) {
    const on = force === undefined ? !overviewEl.classList.contains("show") : force;
    overviewEl.classList.toggle("show", on);
  }

  window.Deck = { add, U, api };
  document.addEventListener("DOMContentLoaded", build);
})();
