/* Fit Plan — animated exercise demos.
 * A side-view stick figure (facing right) driven by keyframes. Legs are posed by foot position (IK) or by
 * absolute angles; arms by absolute angles or a hand target (IK). Angles: 0 = pointing straight down,
 * positive = rotated towards the direction the figure faces (+x). Torso: 0 = upright, + = leaning forward.
 * Ground is y = 180. Near-side limbs are drawn solid, far-side limbs muted.
 */
(function () {
"use strict";
const L = { torso: 50, neck: 16, head: 9, thigh: 40, shin: 42, ua: 28, fa: 26 };
const R = Math.PI / 180;
const down = a => [Math.sin(a * R), Math.cos(a * R)];
const add = (p, v, s = 1) => [p[0] + v[0] * s, p[1] + v[1] * s];

function ik(root, end, l1, l2, bend) {
  let dx = end[0] - root[0], dy = end[1] - root[1], d = Math.hypot(dx, dy) || 1e-6;
  const max = l1 + l2 - 0.01, min = Math.abs(l1 - l2) + 0.01;
  if (d > max || d < min) { const k = (d > max ? max : min) / d; dx *= k; dy *= k; d = Math.hypot(dx, dy); }
  const e = [root[0] + dx, root[1] + dy];
  const a = (l1 * l1 - l2 * l2 + d * d) / (2 * d), h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
  const ux = dx / d, uy = dy / d;
  return [[root[0] + ux * a - uy * h * bend, root[1] + uy * a + ux * h * bend], e];
}

function limb(root, spec, l1, l2, defBend) {
  if (spec.a) { const j = add(root, down(spec.a[0]), l1); return [j, add(j, down(spec.a[1]), l2)]; }
  return ik(root, spec.f || spec.to, l1, l2, spec.b ?? defBend);
}

function solve(p) {
  const hip = p.h, td = [Math.sin(p.t * R), -Math.cos(p.t * R)];
  const sh = add(hip, td, L.torso), head = add(sh, td, L.neck);
  const legs = {}, arms = {};
  for (const s of ["n", "f"]) {
    legs[s] = limb(hip, p.legs[s], L.thigh, L.shin, -1);
    arms[s] = limb(sh, p.arms[s], L.ua, L.fa, 1);
  }
  let bell = null;
  if (p.kb) {
    const hs = p.kb.hand === "both" ? ["n", "f"] : [p.kb.hand];
    const hand = hs.map(s => arms[s][1]).reduce((a, b) => [a[0] + b[0] / hs.length, a[1] + b[1] / hs.length], [0, 0]);
    const el = arms[hs[0]][0], fd = [hand[0] - el[0], hand[1] - el[1]], fl = Math.hypot(...fd) || 1, f = [fd[0] / fl, fd[1] / fl];
    let c;
    switch (p.kb.mode) {
      case "along": c = add(hand, f, 11); break;
      case "above": c = [hand[0], hand[1] - 11]; break;
      case "rack": { let pp = [f[1], -f[0]]; if (pp[0] > 0) pp = [-pp[0], -pp[1]]; c = add(add(hand, pp, 9), f, -3); break; }
      case "floor": c = [p.kb.at[0], 172]; break;
      default: c = [hand[0], hand[1] + 11];
    }
    bell = { hand: p.kb.mode === "floor" ? [c[0], c[1] - 9] : hand, c };
  }
  return { hip, sh, head, legs, arms, bell };
}

/* ---------- keyframe interpolation ---------- */
function lerp(a, b, t) {
  if (typeof a === "number" && typeof b === "number") return a + (b - a) * t;
  if (Array.isArray(a) && Array.isArray(b) && a.length === b.length) return a.map((x, i) => lerp(x, b[i], t));
  if (a && b && typeof a === "object" && typeof b === "object") {
    const o = {}; for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) o[k] = k in a && k in b ? lerp(a[k], b[k], t) : (t < .5 ? a[k] : b[k]); return o;
  }
  return t < .5 ? a : b;
}
const ease = t => .5 - .5 * Math.cos(Math.PI * t);
const merge = (base, over) => {
  if (!over) return JSON.parse(JSON.stringify(base));
  const o = JSON.parse(JSON.stringify(base));
  const isLimb = v => v && (Array.isArray(v.a) || Array.isArray(v.f) || Array.isArray(v.to));   // limb specs replace, never blend
  for (const [k, v] of Object.entries(over)) o[k] = v && typeof v === "object" && !Array.isArray(v) && !isLimb(v) && o[k] && typeof o[k] === "object" ? merge(o[k], v) : JSON.parse(JSON.stringify(v));
  return o;
};

/* ---------- poses ---------- */
const FEET = { n: { f: [103, 180] }, f: { f: [97, 180] } };
const STAND = { h: [100, 98], t: 0, legs: FEET, arms: { n: { a: [4, 4] }, f: { a: [-4, -4] } } };
const S = o => merge(STAND, o);
const GOBLET = { arms: { n: { a: [15, 165] }, f: { a: [12, 165] } }, kb: { mode: "hang", hand: "both" } };
const LYING = { h: [120, 172], t: -90, legs: { n: { f: [150, 180] }, f: { f: [146, 180] } }, arms: { n: { a: [85, 85] }, f: { a: [85, 85] } } };
const Ly = o => merge(LYING, o);
const PLANK_LEGS = { n: { f: [32, 178] }, f: { f: [30, 178] } };

const swingBack = (arms, kb) => ({ h: [78, 122], t: 62, legs: { n: { f: [104, 180] }, f: { f: [96, 180] } }, arms, kb });
const swingTop = (arms, kb) => ({ h: [100, 98], t: -4, legs: { n: { f: [104, 180] }, f: { f: [96, 180] } }, arms, kb });
const K = (pose, move = 700, hold = 200, cut = false) => ({ pose, move, hold, cut });

const pushUp = [
  K({ h: [107.5, 146], t: 67, legs: PLANK_LEGS, arms: { n: { to: [150, 180] }, f: { to: [147, 180] } } }, 900, 250),
  K({ h: [113, 166], t: 82, legs: PLANK_LEGS, arms: { n: { to: [150, 180] }, f: { to: [147, 180] } } }, 900, 150),
];
const swing2 = [
  K(swingBack({ n: { a: [-28, -28] }, f: { a: [-26, -26] } }, { mode: "along", hand: "both" }), 450, 0),
  K(swingTop({ n: { a: [92, 92] }, f: { a: [90, 90] } }, { mode: "along", hand: "both" }), 450, 120),
];

const DEMOS = {
  "goblet squat": [K(S(GOBLET), 1100, 300), K(merge(S(GOBLET), { h: [84, 150], t: 30 }), 1100, 300)],
  "single-arm row": [
    K({ h: [86, 112], t: 72, legs: { n: { f: [108, 180] }, f: { f: [92, 180] } }, arms: { n: { a: [0, 0] }, f: { to: [116, 140], b: -1 } }, kb: { mode: "hang", hand: "n" } }, 800, 250),
    K({ h: [86, 112], t: 72, legs: { n: { f: [108, 180] }, f: { f: [92, 180] } }, arms: { n: { a: [-100, 0] }, f: { to: [116, 140], b: -1 } }, kb: { mode: "hang", hand: "n" } }, 900, 300),
  ],
  "kettlebell deadlift": [
    K(S({ arms: { n: { a: [0, 0] }, f: { a: [0, 0] } }, kb: { mode: "hang", hand: "both" } }), 1100, 300),
    K(S({ h: [76, 126], t: 62, arms: { n: { a: [0, 0] }, f: { a: [0, 0] } }, kb: { mode: "hang", hand: "both" } }), 1100, 200),
  ],
  "push-up": pushUp,
  "suitcase carry": [
    K(S({ legs: { n: { f: [110, 160] } }, arms: { n: { a: [2, 2] }, f: { a: [-12, -12] } }, kb: { mode: "hang", hand: "n" } }), 550, 100),
    K(S({ legs: { f: { f: [104, 160] } }, arms: { n: { a: [2, 2] }, f: { a: [12, 12] } }, kb: { mode: "hang", hand: "n" } }), 550, 100),
  ],
  "plank": [
    K({ h: [112, 160], t: 78, legs: PLANK_LEGS, arms: { n: { a: [0, 90] }, f: { a: [0, 90] } } }, 1600, 400),
    K({ h: [112, 158], t: 77, legs: PLANK_LEGS, arms: { n: { a: [0, 90] }, f: { a: [0, 90] } } }, 1600, 400),
  ],
  "two-hand swing": swing2,
  "single-arm swing": [
    K(swingBack({ n: { a: [-28, -28] }, f: { a: [10, 10] } }, { mode: "along", hand: "n" }), 450, 0),
    K(swingTop({ n: { a: [92, 92] }, f: { a: [-10, -10] } }, { mode: "along", hand: "n" }), 450, 120),
  ],
  "reverse lunge (goblet)": [
    K(S(GOBLET), 900, 300),
    K(merge(S(GOBLET), { h: [90, 138], t: 4, legs: { n: { f: [54, 180] }, f: { f: [112, 180] } } }), 900, 300),
  ],
  "floor press": [
    K(Ly({ arms: { n: { a: [80, 180] } }, kb: { mode: "along", hand: "n" } }), 900, 300),
    K(Ly({ arms: { n: { a: [180, 180] } }, kb: { mode: "along", hand: "n" } }), 900, 200),
  ],
  "single-arm overhead press": [
    K(S({ arms: { n: { a: [12, 172] }, f: { a: [-4, -4] } }, kb: { mode: "rack", hand: "n" } }), 900, 350),
    K(S({ arms: { n: { a: [178, 178] }, f: { a: [-4, -4] } }, kb: { mode: "rack", hand: "n" } }), 1000, 250),
  ],
  "dead bug": (() => {
    const base = { legs: { n: { a: [180, 90] }, f: { a: [178, 90] } }, arms: { n: { a: [180, 180] }, f: { a: [178, 178] } } };
    return [
      K(Ly(base), 1000, 250),
      K(Ly(merge(base, { legs: { n: { a: [96, 96] } }, arms: { f: { a: [-95, -95] } } })), 1000, 250),
      K(Ly(base), 1000, 250),
      K(Ly(merge(base, { legs: { f: { a: [96, 96] } }, arms: { n: { a: [-95, -95] } } })), 1000, 250),
    ];
  })(),
  "swing + push-up finisher": [
    ...swing2, ...swing2,
    K(merge(pushUp[0].pose, { kb: { mode: "floor", hand: "n", at: [192, 0] } }), 900, 250, true),
    K(merge(pushUp[1].pose, { kb: { mode: "floor", hand: "n", at: [192, 0] } }), 900, 150),
    K(merge(pushUp[0].pose, { kb: { mode: "floor", hand: "n", at: [192, 0] } }), 900, 250),
  ],
  "halo": (() => {
    const at = to => S({ arms: { n: { to, b: 1 }, f: { to, b: 1 } }, kb: { mode: "above", hand: "both" } });
    return [K(at([118, 54]), 500, 0), K(at([120, 26]), 500, 0), K(at([98, 10]), 500, 0), K(at([80, 26]), 500, 0)];
  })(),
  "kettlebell clean": [
    K(swingBack({ n: { a: [-28, -28] }, f: { a: [6, 6] } }, { mode: "along", hand: "n" }), 400, 0),
    K(swingTop({ n: { a: [6, 30] }, f: { a: [-6, -6] } }, { mode: "along", hand: "n" }), 250, 0),
    K(swingTop({ n: { a: [12, 172] }, f: { a: [-6, -6] } }, { mode: "rack", hand: "n" }), 500, 500),
    K(swingTop({ n: { a: [6, 30] }, f: { a: [-6, -6] } }, { mode: "along", hand: "n" }), 350, 0),
  ],
  "turkish get-up": (() => {
    const arm = { n: { a: [180, 180] } }, kb = { mode: "along", hand: "n" };
    const lie = { h: [120, 172], t: -90, legs: { n: { f: [150, 180] }, f: { f: [200, 178] } }, arms: { ...arm, f: { a: [-130, -130] } }, kb };
    const elbow = { h: [120, 172], t: -60, legs: { n: { f: [150, 180] }, f: { f: [200, 178] } }, arms: { ...arm, f: { to: [66, 178], b: -1 } }, kb };
    const hand = { h: [120, 172], t: -30, legs: { n: { f: [150, 180] }, f: { f: [200, 178] } }, arms: { ...arm, f: { to: [80, 180], b: -1 } }, kb };
    const bridge = { h: [122, 140], t: -45, legs: { n: { f: [150, 180] }, f: { f: [196, 178] } }, arms: { ...arm, f: { to: [92, 180], b: -1 } }, kb };
    const kneel = { h: [110, 130], t: 0, legs: { n: { f: [140, 180] }, f: { f: [74, 180] } }, arms: { ...arm, f: { a: [0, 0] } }, kb };
    const stand = S({ arms: { ...arm, f: { a: [0, 0] } }, kb });
    return [K(lie, 900, 400), K(elbow, 900, 300), K(hand, 900, 300), K(bridge, 1000, 300), K(kneel, 1100, 300), K(stand, 900, 600),
            K(kneel, 1000, 300), K(bridge, 1100, 300), K(hand, 900, 300), K(elbow, 900, 300)];
  })(),
  "romanian deadlift": [
    K(S({ legs: { n: { f: [99, 180] }, f: { f: [95, 180] } }, arms: { n: { a: [0, 0] }, f: { a: [0, 0] } }, kb: { mode: "hang", hand: "both" } }), 1200, 300),
    K(S({ h: [72, 106], t: 72, legs: { n: { f: [99, 180] }, f: { f: [95, 180] } }, arms: { n: { a: [0, 0] }, f: { a: [0, 0] } }, kb: { mode: "hang", hand: "both" } }), 1200, 300),
  ],
  "russian twist": (() => {
    const base = { h: [100, 174], t: -38, legs: { n: { f: [144, 180] }, f: { f: [140, 180] } }, kb: { mode: "hang", hand: "both" } };
    const at = to => merge(base, { arms: { n: { to, b: 1 }, f: { to, b: 1 } } });
    return [K(at([84, 160]), 650, 120), K(at([104, 136]), 650, 0), K(at([116, 162]), 650, 120), K(at([104, 136]), 650, 0)];
  })(),
  "thruster": [
    K(merge(S(GOBLET), { h: [84, 150], t: 30 }), 700, 150),
    K(S({ arms: { n: { a: [178, 178] }, f: { a: [176, 176] } }, kb: { mode: "above", hand: "both" } }), 700, 250),
  ],
  "high pull": [
    K(swingBack({ n: { a: [-28, -28] }, f: { a: [8, 8] } }, { mode: "along", hand: "n" }), 450, 0),
    K(swingTop({ n: { a: [-110, 90] }, f: { a: [-8, -8] } }, { mode: "along", hand: "n" }), 450, 150),
  ],
};
const ALIASES = { "goblet reverse lunge": "reverse lunge (goblet)", "reverse lunge": "reverse lunge (goblet)", "swing": "two-hand swing",
  "kettlebell swing": "two-hand swing", "deadlift": "kettlebell deadlift", "rdl": "romanian deadlift", "clean": "kettlebell clean",
  "overhead press": "single-arm overhead press", "press": "single-arm overhead press", "row": "single-arm row", "tgu": "turkish get-up",
  "get-up": "turkish get-up", "pushup": "push-up", "press-up": "push-up", "carry": "suitcase carry", "march": "suitcase carry" };

function keyFor(ex) {
  if (ex.demo === "none") return null;
  if (ex.demo && DEMOS[ex.demo]) return ex.demo;
  const n = (ex.name || "").toLowerCase().trim();
  if (DEMOS[n]) return n;
  if (ALIASES[n]) return ALIASES[n];
  return Object.keys(DEMOS).sort((a, b) => b.length - a.length).find(k => n.includes(k)) || null;
}

/* ---------- drawing ---------- */
const NS = "http://www.w3.org/2000/svg";
const mk = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };

function frame(svg, g) {
  const parts = svg._parts;
  const seg = (el, a, b) => { el.setAttribute("x1", a[0]); el.setAttribute("y1", a[1]); el.setAttribute("x2", b[0]); el.setAttribute("y2", b[1]); };
  const poly = (el, pts) => el.setAttribute("points", pts.map(p => p.join(",")).join(" "));
  poly(parts.legF, [g.hip, ...g.legs.f]); poly(parts.armF, [g.sh, ...g.arms.f]);
  seg(parts.torso, g.hip, g.sh);
  parts.head.setAttribute("cx", g.head[0]); parts.head.setAttribute("cy", g.head[1]);
  poly(parts.legN, [g.hip, ...g.legs.n]); poly(parts.armN, [g.sh, ...g.arms.n]);
  if (g.bell) {
    parts.bell.style.display = "";
    parts.bellBody.setAttribute("cx", g.bell.c[0]); parts.bellBody.setAttribute("cy", g.bell.c[1]);
    const mid = [(g.bell.hand[0] + g.bell.c[0]) / 2, (g.bell.hand[1] + g.bell.c[1]) / 2];
    parts.bellHandle.setAttribute("cx", mid[0]); parts.bellHandle.setAttribute("cy", mid[1]);
  } else parts.bell.style.display = "none";
}

function build() {
  const svg = mk("svg", { viewBox: "-5 -34 225 222", class: "demo-svg", role: "img" });
  svg.append(mk("line", { x1: -5, x2: 220, y1: 181.5, y2: 181.5, class: "demo-ground" }));
  const P = {};
  const line = cls => mk("polyline", { class: cls, fill: "none" });
  P.legF = line("demo-limb demo-far"); P.armF = line("demo-limb demo-far");
  P.torso = mk("line", { class: "demo-limb demo-torso" });
  P.head = mk("circle", { r: L.head, class: "demo-head" });
  P.legN = line("demo-limb"); P.armN = line("demo-limb");
  P.bell = mk("g", { class: "demo-bell" });
  P.bellHandle = mk("circle", { r: 5, class: "demo-bell-handle" });
  P.bellBody = mk("circle", { r: 8.5, class: "demo-bell-body" });
  P.bell.append(P.bellHandle, P.bellBody);
  svg.append(P.legF, P.armF, P.torso, P.head, P.legN, P.armN, P.bell);
  svg._parts = P;
  return svg;
}

function poseAt(keys, ms) {
  const total = keys.reduce((s, k) => s + k.hold + k.move, 0);
  let t = ms % total;
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i], nx = keys[(i + 1) % keys.length];
    if (t < k.hold) return k.pose;
    t -= k.hold;
    if (t < k.move) return nx.cut ? (t < k.move / 2 ? k.pose : nx.pose) : lerp(k.pose, nx.pose, ease(t / k.move));
    t -= k.move;
  }
  return keys[0].pose;
}

function create(ex) {
  const key = keyFor(ex);
  if (!key) return null;
  const keys = DEMOS[key], svg = build();
  frame(svg, solve(keys[0].pose));
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  let t0 = null;
  const tick = now => {
    if (!svg.isConnected) return;          // not on the page (re-rendered away): stop
    if (t0 === null) t0 = now;
    if (!reduce) frame(svg, solve(poseAt(keys, now - t0)));
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  return svg;
}

window.FitDemos = { create, keyFor, names: () => Object.keys(DEMOS), _solve: solve, _poseAt: poseAt, _DEMOS: DEMOS, _build: build, _frame: frame };
})();
