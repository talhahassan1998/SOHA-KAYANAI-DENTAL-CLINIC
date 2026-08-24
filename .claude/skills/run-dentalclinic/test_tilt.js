// Self-check for the pointer-tilt state machine in app/static/js/main.js.
// Extracts the pointerTilt IIFE, runs it against a fake DOM, and asserts the
// two bugs that made rotateX/rotateY unstable on hover stay fixed.
//   run: node .claude/skills/run-dentalclinic/test_tilt.js
const assert = require("assert");
const fs = require("fs");
const path = require("path");

const MAIN = path.join(__dirname, "..", "..", "..", "app", "static", "js", "main.js");
const src = fs.readFileSync(MAIN, "utf8");
const body = src.slice(src.indexOf("(function pointerTilt()"), src.indexOf("// Scroll parallax"));

const L = {};
let q = [];
global.requestAnimationFrame = (fn) => { q.push(fn); return q.length; };
const flush = (n = 200) => { for (let i = 0; i < n && q.length; i++) { const b = q; q = []; b.forEach(f => f()); } };

const card = (id) => ({
  id, style: {},
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 200, height: 100 }),
  closest(s) { return s === ".tilt" ? this : null; },
});
const A = card("A"), B = card("B");

global.window = { matchMedia: () => ({ matches: true }), addEventListener: () => {} };
global.document = { querySelector: () => A, addEventListener: (t, f) => { L[t] = f; } };
new Function("prefersReducedMotion", body)(false);

const deg = (el, axis) => {
  const m = (el.style.transform || "").match(new RegExp(axis + "\\(([-\\d.]+)deg\\)"));
  return m ? parseFloat(m[1]) : null;
};
// The chase is exponential, so it converges to within EPS of the target and
// stops there (the rAF loop's own cutoff is 0.01deg) — never exactly onto it.
const EPS = 0.02;
const near = (got, want, msg) =>
  assert.ok(got !== null && Math.abs(got - want) <= EPS, msg + " (want ~" + want + ", got " + got + ")");

// 1. Basic tracking settles at the corner target.
L.pointermove({ clientX: 100, clientY: 50 });
L.pointerover({ target: A });
L.pointermove({ clientX: 200, clientY: 100 });   // bottom-right corner
flush();
near(deg(A, "rotateY"), 6, "rotateY settles at +MAX_DEG");
near(deg(A, "rotateX"), -6, "rotateX settles at -MAX_DEG");

// 2. Regression: a card-to-card move fires pointerover for B BEFORE any
//    pointermove over B. Without seeding `pending` from `last` in enter(),
//    B renders a frame flat with transition:none, then jumps.
L.pointerover({ target: B });
flush();
assert.ok(B.style.transform, "card B must carry a transform right after enter(), not sit flat");
assert.notStrictEqual(deg(B, "rotateY"), null, "card B must have a rotateY immediately");
assert.strictEqual(A.style.transform, "", "card A must be handed back to the CSS return-home easing");

// 3. Regression: the chase must run to completion rather than stalling when a
//    guard trips (frame must not be zeroed before the early returns).
L.pointermove({ clientX: 0, clientY: 0 });       // opposite corner
flush();
near(deg(B, "rotateY"), -6, "rotateY finishes its travel after a flick across the card");
near(deg(B, "rotateX"), 6, "rotateX finishes its travel after a flick across the card");

// 4. Angles stay clamped inside +/- MAX_DEG even well outside the element.
for (const [x, y] of [[-500, -500], [900, 900], [0, 300], [400, -200]]) {
  L.pointermove({ clientX: x, clientY: y });
  flush();
  assert.ok(Math.abs(deg(B, "rotateX")) <= 6 + EPS, "rotateX exceeded MAX_DEG: " + deg(B, "rotateX"));
  assert.ok(Math.abs(deg(B, "rotateY")) <= 6 + EPS, "rotateY exceeded MAX_DEG: " + deg(B, "rotateY"));
}

// 5. leave() releases the card entirely.
L.pointerover({ target: { closest: () => null } });
flush();
assert.strictEqual(B.style.transform, "", "leave() must clear the inline transform");
assert.strictEqual(B.style.transition, "", "leave() must restore the CSS transition");

console.log("PASS: tilt stable — tracking, card-to-card, no stall, clamped, clean leave");
