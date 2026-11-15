/* Hand-drawn icon set. Each doodle is ink strokes over a soft colour blob, drawn through the
   #rough SVG filter (index.html) so lines wobble like pen on paper. doodle(name, opts) returns
   markup; every doodle sits at its own small tilt so neighbours never line up exactly. */
"use strict";

const DOODLE_INK = {
  pencil: `<path d="M14 50 L18 38 L44 12 L52 20 L26 46 Z"/><path d="M18 38 L26 46"/><path d="M40 16 L48 24"/><path d="M14 50 L21 48"/>`,
  magnifier: `<path d="M15 27 C15 18 22 13 29 14 C37 15 42 21 41 29 C40 37 33 41 26 40 C19 39 15 34 15 27 Z"/><path d="M37 37 L51 51"/><path d="M21 23 C23 19 27 18 30 19"/>`,
  paper: `<path d="M18 10 L40 10 L48 18 L48 54 L18 54 Z"/><path d="M40 10 L40 18 L48 18"/><path d="M24 28 L42 28"/><path d="M24 35 L40 35"/><path d="M24 42 L35 42"/>`,
  stack: `<path d="M14 22 L42 16 L50 46 L22 52 Z"/><path d="M10 18 L36 12"/><path d="M8 14 L30 9"/><path d="M22 30 L40 26"/><path d="M24 37 L42 33"/>`,
  lightbulb: `<path d="M32 10 C21 10 15 19 17 28 C18 34 23 37 24 43 L40 43 C41 37 46 34 47 28 C49 19 43 10 32 10 Z"/><path d="M25 48 L39 48"/><path d="M27 53 L37 53"/><path d="M8 20 L13 22"/><path d="M56 20 L51 22"/><path d="M32 2 L32 5"/><path d="M28 30 C30 34 34 34 36 30"/>`,
  flask: `<path d="M25 10 L39 10"/><path d="M28 10 L28 26 L16 47 C14 52 17 55 21 55 L43 55 C47 55 50 52 48 47 L36 26 L36 10"/><path d="M19 41 C26 38 32 44 45 40"/><path d="M29 48 C29 47 31 47 31 48 C31 49 29 49 29 48 Z"/><path d="M37 46 C37 45 39 45 39 46"/>`,
  book: `<path d="M32 16 C25 12 16 12 10 14 L10 50 C16 48 25 48 32 52 C39 48 48 48 54 50 L54 14 C48 12 39 12 32 16 Z"/><path d="M32 16 L32 52"/><path d="M16 22 L26 22"/><path d="M16 29 L26 30"/><path d="M38 22 L48 22"/>`,
  telescope: `<path d="M10 33 L42 17 L47 26 L15 42 Z"/><path d="M42 17 L50 13 L55 22 L47 26"/><path d="M30 33 L22 55"/><path d="M30 33 L39 55"/><path d="M30 33 L30 54"/>`,
  scale: `<path d="M32 9 L32 52"/><path d="M21 53 L43 53"/><path d="M13 18 L51 18"/><path d="M13 18 L6 34"/><path d="M13 18 L21 34"/><path d="M51 18 L43 34"/><path d="M51 18 L58 34"/><path d="M5 34 C7 40 19 40 22 34 Z"/><path d="M42 34 C44 40 56 40 59 34 Z"/><path d="M29 9 C30 6 34 6 35 9"/>`,
  chat: `<path d="M12 16 C12 12 15 10 19 10 L45 10 C49 10 52 12 52 16 L52 33 C52 37 49 40 45 40 L29 40 L18 50 L20 40 L19 40 C15 40 12 37 12 33 Z"/><path d="M22 25 L23 25"/><path d="M32 25 L33 25"/><path d="M42 25 L43 25"/>`,
  sparkle: `<path d="M32 8 C34 24 40 30 56 32 C40 34 34 40 32 56 C30 40 24 34 8 32 C24 30 30 24 32 8 Z"/><path d="M50 8 L50 15"/><path d="M46.5 11.5 L53.5 11.5"/>`,
  check: `<path d="M13 34 L26 46 L52 15"/>`,
  arrow: `<path d="M8 40 C18 20 28 50 40 30 C44 24 48 22 55 22"/><path d="M47 15 L55 22 L48 30"/>`,
  upload: `<path d="M10 40 L10 52 L54 52 L54 40"/><path d="M32 43 L32 12"/><path d="M22 22 L32 12 L42 22"/>`,
  link: `<path d="M27 37 L37 27"/><path d="M30 20 L36 14 C40 10 47 10 50 14 C54 18 54 24 50 28 L44 34"/><path d="M34 44 L28 50 C24 54 17 54 14 50 C10 46 10 40 14 36 L20 30"/>`,
  cap: `<path d="M5 24 L32 12 L59 24 L32 36 Z"/><path d="M17 30 L17 43 C24 50 40 50 47 43 L47 30"/><path d="M59 24 L59 40"/><path d="M57 40 L61 40 L59 46 Z"/>`,
  globe: `<path d="M12 32 C12 20 21 11 32 11 C44 11 53 21 52 33 C51 45 42 53 31 53 C20 52 12 44 12 32 Z"/><path d="M32 11 C24 20 23 44 31 53"/><path d="M32 11 C41 20 41 44 31 53"/><path d="M14 25 L50 24"/><path d="M14 40 L50 40"/>`,
  person: `<path d="M24 20 C24 14 28 11 32 11 C37 11 40 15 40 20 C40 26 36 29 32 29 C27 29 24 25 24 20 Z"/><path d="M13 55 C14 42 22 36 32 36 C43 36 50 43 51 55"/>`,
  seedling: `<path d="M32 56 L32 30"/><path d="M32 35 C22 35 15 27 15 18 C25 18 32 25 32 35"/><path d="M32 30 C32 20 40 13 51 13 C51 23 43 30 32 30"/><path d="M20 56 L44 56"/>`,
  coffee: `<path d="M13 24 L46 24 L42 52 L17 52 Z"/><path d="M46 29 C55 29 55 42 44 42"/><path d="M23 18 C21 14 25 12 23 7"/><path d="M32 18 C30 14 34 12 32 7"/>`,
  hourglass: `<path d="M17 10 L47 10"/><path d="M17 54 L47 54"/><path d="M20 10 C20 24 44 30 44 54"/><path d="M44 10 C44 24 20 30 20 54"/><path d="M26 49 L38 49"/>`,
  rocket: `<path d="M32 6 C42 14 45 28 41 42 L23 42 C19 28 22 14 32 6 Z"/><path d="M28 24 C28 21 30 20 32 20 C34 20 36 21 36 24 C36 27 34 28 32 28 C30 28 28 27 28 24 Z"/><path d="M23 36 L15 46 L23 44"/><path d="M41 36 L49 46 L41 44"/><path d="M28 48 C29 53 31 56 32 58 C33 56 35 53 36 48"/>`,
  key: `<path d="M12 30 C12 23 17 19 23 19 C29 19 34 24 33 31 C32 37 27 40 22 40 C16 40 12 36 12 30 Z"/><path d="M33 30 L54 30"/><path d="M46 30 L46 37"/><path d="M52 30 L52 36"/>`,
  feather: `<path d="M50 10 C30 12 18 26 16 48 C30 46 46 34 50 10 Z"/><path d="M12 54 L42 20"/><path d="M24 38 L34 38"/><path d="M30 30 L40 30"/>`,
  star: `<path d="M32 9 L38 25 L55 25 L41 35 L46 52 L32 42 L18 52 L23 35 L9 25 L26 25 Z"/>`,
  heart: `<path d="M32 52 C14 40 8 30 12 21 C16 13 27 12 32 22 C37 12 48 13 52 21 C56 30 50 40 32 52 Z"/>`,
  folder: `<path d="M8 18 L24 18 L29 24 L56 24 L56 52 L8 52 Z"/><path d="M8 30 L56 30"/>`,
};

const DOODLE_BLOB = [
  "M30 12 C44 9 56 20 54 34 C52 48 38 56 25 52 C12 48 7 35 11 24 C14 17 21 13 30 12 Z",
  "M26 10 C40 6 55 16 55 31 C55 46 43 55 29 54 C15 53 7 42 9 29 C10 19 17 12 26 10 Z",
  "M34 9 C47 12 57 25 53 39 C49 52 34 57 22 51 C10 45 6 31 12 21 C17 13 25 7 34 9 Z",
];
const DOODLE_COLORS = ["clay", "sage", "ochre", "sky", "rose"];

function hashStr(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0; return Math.abs(h); }

/* opts: size (px), color (clay|sage|ochre|sky|rose), tilt (deg), cls, label (accessible name) */
function doodle(name, opts = {}) {
  const ink = DOODLE_INK[name] || DOODLE_INK.sparkle;
  const h = hashStr(name + (opts.seed || ""));
  const color = opts.color || DOODLE_COLORS[h % DOODLE_COLORS.length];
  const tilt = opts.tilt ?? ((h % 13) - 6);
  const blob = DOODLE_BLOB[h % DOODLE_BLOB.length];
  const size = opts.size || 44;
  const a11y = opts.label ? `role="img" aria-label="${opts.label}"` : `aria-hidden="true"`;
  return `<span class="doodle doodle-${color} ${opts.cls || ""}" style="--tilt:${tilt}deg;--size:${size}px" ${a11y}>` +
    `<svg viewBox="0 0 64 64" width="${size}" height="${size}">` +
    `<path class="doodle-blob" d="${blob}" transform="translate(${(h % 7) - 3} ${(h % 5) - 1})"/>` +
    `<g class="doodle-ink" filter="url(#rough)">${ink}</g></svg></span>`;
}
