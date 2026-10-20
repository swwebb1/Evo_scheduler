/* Fit Plan — animated exercise demos (v2).
 *
 * Side-view figure, facing right (+x), drawn to adult proportions (≈1 unit per cm; ground at y = 180).
 * Poses are keyframes. Angles are absolute, in degrees: 0 = pointing straight down, + = rotated toward the
 * direction the figure faces. Torso angle t: 0 = upright, + = leaning forward, −90 = lying on the back.
 *
 * The torso is drawn as a solid block so the line of the back is visible. Hinge exercises show a dashed
 * "dowel" along the back: head, upper back and tailbone should all touch it (neutral spine).
 * Each keyframe carries a coaching caption that is shown while that phase plays.
 *
 * Technique references (see each exercise's source link in the app): ACE Exercise Library, NSCA
 * Exercise Technique Manual / Kinetic Select, StrongFirst, NASM, McGill "Big 3".
 */
(function () {
"use strict";
const L = { torso: 52, neck: 22, head: 10, thigh: 43, shin: 43, ua: 31, fa: 31, half: 10, toe: 19, heel: 6, sole: 5 };
const GY = 180, ANK = 174;                        // ground line, ankle height when the foot is flat
const R = Math.PI / 180;
const dir = a => [Math.sin(a * R), Math.cos(a * R)];
const add = (p, v, s = 1) => [p[0] + v[0] * s, p[1] + v[1] * s];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1]];
const hyp = v => Math.hypot(v[0], v[1]);
const unit = v => { const l = hyp(v) || 1; return [v[0] / l, v[1] / l]; };
const angOf = v => Math.atan2(v[0], v[1]) / R;                // inverse of dir()
const tOf = v => Math.atan2(v[0], -v[1]) / R;                 // torso angle of a hip→shoulder vector

function ik(root, end, l1, l2, bend) {
  let dx = end[0] - root[0], dy = end[1] - root[1], d = Math.hypot(dx, dy) || 1e-6;
  const max = l1 + l2 - 0.01, min = Math.abs(l1 - l2) + 0.01;
  if (d > max || d < min) { const k = (d > max ? max : min) / d; dx *= k; dy *= k; d = Math.hypot(dx, dy); }
  const a = (l1 * l1 - l2 * l2 + d * d) / (2 * d), h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
  const ux = dx / d, uy = dy / d;
  return [[root[0] + ux * a - uy * h * bend, root[1] + uy * a + ux * h * bend], [root[0] + dx, root[1] + dy]];
}

/* ---------- solving a pose into joint positions ---------- */
function solve(p) {
  const legs = {}, arms = {};
  let hip = p.h;
  for (const s of ["n", "f"]) {                     // a leg with an ankle anchor + angles fixes the hip
    const sp = p.legs[s];
    if (!hip && sp.ank && sp.a) {
      const knee = sub(sp.ank, dir(sp.a[1]).map(v => v * L.shin));
      hip = sub(knee, dir(sp.a[0]).map(v => v * L.thigh));
      legs[s] = [knee, sp.ank];
    }
  }
  for (const s of ["n", "f"]) {
    if (legs[s]) continue;
    const sp = p.legs[s];
    if (sp.ank) legs[s] = ik(hip, sp.ank, L.thigh, L.shin, sp.b ?? -1);
    else { const k = add(hip, dir(sp.a[0]), L.thigh); legs[s] = [k, add(k, dir(sp.a[1]), L.shin)]; }
  }
  const td = [Math.sin(p.t * R), -Math.cos(p.t * R)], fn = [-td[1], td[0]];   // up the spine / out of the chest
  const sh = add(hip, td, L.torso);
  const target = (spec) => {
    if (typeof spec.to === "string") {
      const [kind, side] = spec.to.split(":");
      if (kind === "knee") return add(legs[side][0], [-4, -7]);
      if (kind === "hip") return add(hip, fn, -(L.half + 3));
    }
    return spec.to;
  };
  for (const s of ["n", "f"]) {
    const sp = p.arms[s], k = sp.k || [1, 1];
    if (sp.a) { const e = add(sh, dir(sp.a[0]), L.ua * k[0]); arms[s] = [e, add(e, dir(sp.a[1]), L.fa * k[1])]; }
    else arms[s] = ik(sh, target(sp), L.ua * k[0], L.fa * k[1], sp.b ?? 1);
  }
  // bell
  let bell = null;
  if (p.kb && p.kb.mode === "floor") bell = { hand: [p.kb.at, GY - 25], c: [p.kb.at, GY - 10] };
  else if (p.kb) {
    const hs = p.kb.hand === "both" ? ["n", "f"] : [p.kb.hand];
    const hand = hs.map(s => arms[s][1]).reduce((a, b) => [a[0] + b[0] / hs.length, a[1] + b[1] / hs.length], [0, 0]);
    const f = unit(sub(arms[hs[0]][1], arms[hs[0]][0]));
    let c;
    switch (p.kb.mode) {
      case "swing": c = add(hand, f, 16); break;                           // bell continues the line of the arm
      case "goblet": c = add(hand, [0, 13]); break;                        // held by the horns, against the chest
      case "halo": c = add(hand, [0, -13]); break;                         // upside down, by the horns
      case "rack": c = add(add(hand, f, -8), fn, 2); break;                // resting on the forearm at the chest
      case "press": { let pp = [-f[1], f[0]]; if (pp[0] > 0) pp = [-pp[0], -pp[1]]; c = add(add(hand, f, -5), pp, 8); break; }
      case "floor": c = [p.kb.at, GY - 10]; break;
      default: c = add(hand, [0, 16]);                                      // hanging from the handle
    }
    bell = { hand: p.kb.mode === "floor" ? [c[0], c[1] - 15] : hand, c };
  }
  // head: neutral = in line with the spine; `look` turns the face toward a point (neck limited)
  let nk = p.nk || 0;
  if (p.look) {
    const at = p.look === "bell" && bell ? bell.c : p.look;
    const base = add(sh, td, L.neck), w = unit(sub(at, base));
    nk = Math.max(-55, Math.min(50, Math.atan2(-(w[0] * td[0] + w[1] * td[1]), w[0] * fn[0] + w[1] * fn[1]) / R));
  }
  const c = Math.cos(nk * R), s = Math.sin(nk * R);
  const nv = [td[0] * c + fn[0] * s, td[1] * c + fn[1] * s];                 // neck direction
  const face = [fn[0] * c - td[0] * s, fn[1] * c - td[1] * s];
  const head = add(sh, nv, L.neck);
  const feet = { n: [p.legs.n.ft, p.legs.n.fo], f: [p.legs.f.ft, p.legs.f.fo] };
  return { hip, sh, td, fn, head, face, nk, legs, arms, bell, feet, view: p.view || "side" };
}

function footPts(knee, ank, ft, view, fo) {
  let u;
  if (ft !== undefined) u = [Math.cos(ft * R), Math.sin(ft * R)];
  else if (ank[1] >= 170) u = [1, 0];                                       // flat on the ground
  else { const d = unit(sub(ank, knee)); u = [d[1], -d[0]]; }               // ankle at 90° (toes tucked / pointing up)
  const v = [-u[1], u[0]], k = view === "front" ? 0.25 : 1;
  const o = fo ?? L.sole;
  return [add(add(ank, u, -L.heel * k), v, o), add(add(ank, u, L.toe * k), v, o)];
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
const clone = o => JSON.parse(JSON.stringify(o));
const isLimb = v => v && (Array.isArray(v.a) || Array.isArray(v.ank) || v.to !== undefined);
function merge(base, over) {
  const o = clone(base);
  if (!over) return o;
  for (const [k, v] of Object.entries(over)) {
    o[k] = v && typeof v === "object" && !Array.isArray(v) && !isLimb(v) && o[k] && typeof o[k] === "object" ? merge(o[k], v) : clone(v);
  }
  return o;
}
const K = (pose, cap, move = 700, hold = 250, cut = false) => ({ pose, cap, move, hold, cut });

/* ---------- pose builders ---------- */
const FEET = { n: { ank: [100, ANK], a: [0, 0] }, f: { ank: [98, ANK] } };
const STAND = { t: 0, legs: FEET, arms: { n: { a: [4, 4] }, f: { a: [-4, -4] } } };
const S = o => merge(STAND, o);
// Hinge with feet planted: thigh/shin angles of the near leg, torso angle t.
const hinge = (thigh, shin, t, o) => merge({ t, legs: { n: { ank: [100, ANK], a: [thigh, shin] }, f: { ank: [98, ANK] } }, arms: STAND.arms }, o);
// Hinge where the shoulder must land on a given point (e.g. directly above the bell): solves the hip.
function hingeTo(shoulder, shin, o) {
  const knee = sub([100, ANK], dir(shin).map(v => v * L.shin));
  const [hip] = ik(knee, shoulder, L.thigh, L.torso, -1);
  return hinge(angOf(sub(knee, hip)), shin, tOf(sub(shoulder, hip)), o);
}
// Rigid straight body from the ankle to the shoulder (plank / push-up / side plank).
function lineBody(ank, shoulder, o) {
  const u = unit(sub(shoulder, ank)), hip = add(ank, u, L.thigh + L.shin - 0.02);
  return merge({ h: hip, t: tOf(sub(shoulder, hip)), legs: { n: { ank }, f: { ank: add(ank, [-2, 0]) } } }, o);
}
const SUP = (o) => merge({ h: [128, 170], t: -90, legs: { n: { ank: [172, ANK] }, f: { ank: [168, ANK] } },
  arms: { n: { a: [86, 86] }, f: { a: [88, 88] } } }, o);                    // lying on the back, knees bent

const GOB = { arms: { n: { a: [20, 170] }, f: { a: [17, 170] } }, kb: { mode: "goblet", hand: "both" } };
const RACK = { a: [12, 165] };

/* ---------- swing family ---------- */
const HIKE = (arms, hand) => hinge(50, -8, 65, { arms, kb: { mode: "swing", hand } });
const UP = (arms, hand) => S({ arms, kb: { mode: "swing", hand } });
function swingKeys(one) {
  const fr = one ? { a: [-6, -6] } : null, h = one ? "n" : "both";
  const A = a => one ? { n: { a: [a, a] }, f: fr } : { n: { a: [a, a] }, f: { a: [a - 2, a - 2] } };
  return [
    K(HIKE(A(-58), h), "Hike: bell high between the thighs, above the knees. Flat back, neck long", 330, 0),
    K(UP(A(22), h), "Snap the hips forward — the power comes from the hips, not the arms", 280, 0),
    K(UP(A(80), h), "Top: stand tall in a 'standing plank'. Glutes tight, no leaning back", 330, 140),
    K(UP(A(16), h), "Let the bell fall; hinge only when your forearms meet your hips", 300, 0),
  ];
}

/* ---------- push-up / plank geometry ---------- */
const PU_TOP = lineBody([19, 158], [150, 115], { arms: { n: { to: [150, GY - 3], k: [1, 1] }, f: { to: [147, GY - 3], k: [1, 1] } } });
const PU_LOW = lineBody([19, 158], [157, 159], { arms: { n: { to: [150, GY - 3], k: [0.6, 1.1] }, f: { to: [147, GY - 3], k: [0.6, 1.1] } } });

/* ---------- Turkish get-up ---------- */
const TGU = (() => {
  const arm = { a: [180, 180] }, kb = { mode: "press", hand: "n" }, look = "bell";
  const lie = SUP({ legs: { n: { ank: [172, ANK] }, f: { ank: [212, ANK] } }, arms: { n: arm, f: { a: [92, 92] } }, kb, look });
  const elbow = merge(lie, { t: -60, arms: { n: arm, f: { a: [13, 92] } } });
  const hand = merge(lie, { t: -25, arms: { n: arm, f: { to: [82, GY - 3] } } });
  const bridge = { h: [138, 138], t: -64, legs: { n: { ank: [172, ANK] }, f: { ank: [212, ANK] } }, arms: { n: arm, f: { to: [82, GY - 3] } }, kb, look };
  const sweep = { h: [118, 132], t: -42, legs: { n: { ank: [166, ANK] }, f: { ank: [80, 169], b: -1 } }, arms: { n: arm, f: { a: [-25, -25] } }, kb, look };
  const kneel = { h: [118, 131], t: 0, legs: { n: { ank: [166, ANK] }, f: { ank: [78, 169] } }, arms: { n: arm, f: { a: [-8, -8] } }, kb, look };
  const stand = { h: [160, 88], t: 0, legs: { n: { ank: [160, ANK] }, f: { ank: [158, ANK] } }, arms: { n: arm, f: { a: [-6, -6] } }, kb };
  return [
    K(lie, "Lie on your back, bell pressed up, same-side knee bent. Eyes on the bell", 900, 500),
    K(elbow, "Punch the bell up and roll onto the opposite elbow", 900, 350),
    K(hand, "Press up onto the hand. Arm stays locked, eyes on the bell", 900, 350),
    K(bridge, "Lift the hips: straight line from the straight leg to the shoulder", 1000, 350),
    K(sweep, "Sweep the straight leg back under you to a half-kneel", 1000, 250),
    K(kneel, "Lift the torso upright — kneeling, bell locked overhead", 1000, 350),
    K(stand, "Stand up out of the lunge. Then reverse every step to lie back down", 1000, 700),
    K(kneel, "Step back to a half-kneel — slow and controlled", 1000, 250),
    K(sweep, "Hand down, leg back through", 1000, 250),
    K(bridge, "Hips high", 900, 250),
    K(hand, "Sit back onto the hand", 900, 250),
    K(elbow, "Down to the elbow, then lie back", 900, 250),
  ];
})();

/* ---------- the library ---------- */
const DEMOS = {
  "goblet squat": { keys: [
    K(S(merge(GOB, { t: 3 })), "Feet shoulder-width, toes slightly out. Bell at the chest, elbows down", 1100, 300),
    K(hinge(95, -30, 35, merge(GOB, { nk: -15 })), "Hips back and down, chest up, heels flat, knees in line with toes. Elbows inside the knees. Drive up through the whole foot", 1100, 450),
  ] },
  "single-arm row": { guide: true, keys: [
    K({ h: [94, 100], t: 60, legs: { n: { ank: [76, ANK] }, f: { ank: [122, ANK] } },
        arms: { n: { a: [0, 0] }, f: { to: "knee:f", b: 1 } }, kb: { mode: "hang", hand: "n" } },
      "Split stance, free hand braced on the front thigh. Flat back, neck long", 850, 300),
    K({ h: [94, 100], t: 60, legs: { n: { ank: [76, ANK] }, f: { ank: [122, ANK] } },
        arms: { n: { a: [-68, -4] }, f: { to: "knee:f", b: 1 } }, kb: { mode: "hang", hand: "n" } },
      "Pull the elbow back to the hip. Don't twist your torso", 900, 350),
  ] },
  "kettlebell deadlift": { guide: true, keys: [
    K(hingeTo([106, 92], -10, { arms: { n: { a: [0, 0] }, f: { a: [0, 0] } }, kb: { mode: "hang", hand: "both" } }),
      "Bell between the feet, under the middle of the foot. Hips back, shins near vertical, flat back — brace", 1000, 450),
    K(S({ arms: { n: { a: [5, 5] }, f: { a: [3, 3] } }, kb: { mode: "hang", hand: "both" } }),
      "Push the floor away and drive the hips forward. Stand tall, glutes tight — don't lean back", 1000, 450),
  ] },
  "push-up": { keys: [
    K(PU_TOP, "Hands under the shoulders. Straight line from heels to head", 900, 300),
    K(PU_LOW, "Lower as one unit, elbows about 45° from your sides, chest close to the floor", 900, 200),
  ] },
  "side plank": { view: "front", keys: [
    K({ h: [112, 167], t: 66, legs: { n: { ank: [25, 175] }, f: { ank: [25, 170] } }, arms: { n: { a: [0, 90], k: [1, 0.25] }, f: { a: [180, 180] } }, view: "front" },
      "On your side, elbow directly under the shoulder, feet stacked (or knees bent to make it easier)", 1000, 400),
    K(lineBody([25, 175], [160, 146], { legs: { f: { ank: [25, 170] } }, arms: { n: { a: [0, 90], k: [1, 0.25] }, f: { a: [180, 180] } }, view: "front" }),
      "Lift the hips into a straight line from feet to head. Head in line, keep breathing", 1000, 2200),
  ] },
  "plank": { keys: [
    K(lineBody([13, 158], [150, 146], { arms: { n: { a: [0, 90] }, f: { a: [0, 88] } } }),
      "Elbows directly under the shoulders, forearms on the floor", 1800, 400),
    K(lineBody([13, 158], [150, 145], { arms: { n: { a: [0, 90] }, f: { a: [0, 88] } } }),
      "Brace: one straight line heels to head. No sagging or piking hips — breathe", 1800, 400),
  ] },
  "two-hand swing": { guide: true, keys: swingKeys(false) },
  "single-arm swing": { guide: true, keys: swingKeys(true) },
  "reverse lunge (goblet)": { keys: [
    K(merge(GOB, { h: [99, 88], t: 2, legs: { n: { ank: [99, ANK] }, f: { ank: [98, ANK] } } }), "Stand tall, bell at the chest, feet hip-width", 950, 300),
    K(merge(GOB, { h: [62, 131], t: 4, legs: { n: { ank: [14, 162] }, f: { ank: [98, ANK] } } }),
      "Step back and lower the back knee straight down. Front shin near vertical, chest up", 950, 350),
  ] },
  "floor press": { keys: [
    K(SUP({ arms: { n: { a: [84, 180] }, f: { a: [88, 88] } }, kb: { mode: "press", hand: "n" } }),
      "Lying, knees bent. Upper arm on the floor, about 45° from your side, wrist straight", 900, 350),
    K(SUP({ arms: { n: { a: [180, 180] }, f: { a: [88, 88] } }, kb: { mode: "press", hand: "n" } }),
      "Press straight up over the shoulder, then lower slowly until the elbow touches", 900, 250),
  ] },
  "single-arm overhead press": { keys: [
    K(S({ arms: { n: RACK, f: { a: [-4, -4] } }, kb: { mode: "rack", hand: "n" } }),
      "Rack: bell on the forearm, elbow tucked to the ribs, wrist straight. Brace and squeeze glutes", 900, 400),
    K(S({ arms: { n: { a: [178, 178] }, f: { a: [-4, -4] } }, kb: { mode: "press", hand: "n" } }),
      "Press straight up until the arm locks, bicep by the ear. Don't lean back or sideways", 1000, 300),
  ] },
  "dead bug": { keys: (() => {
    const base = SUP({ h: [120, 170], legs: { n: { a: [180, 90] }, f: { a: [178, 90] } }, arms: { n: { a: [180, 180] }, f: { a: [178, 178] } } });
    return [
      K(base, "Arms up, hips and knees at 90°, low back gently pressed into the floor", 1100, 350),
      K(merge(base, { legs: { n: { a: [100, 100] } }, arms: { f: { a: [260, 260] } } }), "Slowly reach one leg and the opposite arm away — low back stays down", 1100, 350),
      K(base, "Return to the start", 1100, 300),
      K(merge(base, { legs: { f: { a: [100, 100] } }, arms: { n: { a: [260, 260] } } }), "Other side. Only go as low as you can without your back arching", 1100, 350),
    ];
  })() },
  "bird dog": { keys: (() => {
    const ft = { n: { a: [0, -90], ft: 180, fo: -3 }, f: { a: [2, -90], ft: 180, fo: -3 } };
    const quad = { h: [90, 131], t: 72, legs: ft, arms: { n: { a: [0, 0] }, f: { a: [2, 2] } } };
    return [
      K(quad, "Hands under shoulders, knees under hips, neutral spine, head in line", 1100, 300),
      K(merge(quad, { legs: { ...ft, f: { a: [-90, -90] } }, arms: { n: { a: [90, 90] }, f: { a: [2, 2] } } }),
        "Reach one arm forward and the opposite leg back. Hips level, no arching — hold 2 s", 1100, 1200),
      K(quad, "Return under control", 1100, 300),
      K(merge(quad, { legs: { ...ft, n: { a: [-90, -90] } }, arms: { n: { a: [0, 0] }, f: { a: [90, 90] } } }),
        "Other side. Keep the spine still — don't twist", 1100, 1200),
    ];
  })() },
  "swing + push-up finisher": { guide: true, keys: [
    ...swingKeys(false), ...swingKeys(false),
    K(merge(PU_TOP, { kb: { mode: "floor", at: 210 } }), "Park the bell safely, then straight into push-ups", 900, 300, true),
    K(merge(PU_LOW, { kb: { mode: "floor", at: 210 } }), "Straight line heels to head", 900, 200),
    K(merge(PU_TOP, { kb: { mode: "floor", at: 210 } }), "Back to the bell for the next round", 900, 300),
  ] },
  "halo": { keys: (() => {
    const at = (to, cap) => K(S({ arms: { n: { to, b: 1 }, f: { to: add(to, [-2, 0]), b: 1 } }, kb: { mode: "halo", hand: "both" } }), cap, 550, 0);
    return [
      at([118, 42], "Hold the horns, bell upside down in front of the chest"),
      at([101, 12], "Circle it close around the head — keep the head still"),
      at([86, 22], "Behind the head. Ribs down, glutes tight, no arching"),
      at([101, 12], "Back round to the front. Change direction each rep"),
    ];
  })() },
  "kettlebell clean": { guide: true, keys: [
    K(HIKE({ n: { a: [-58, -58] }, f: { a: [-6, -6] } }, "n"), "Hike the bell back, flat back", 330, 0),
    K(S({ arms: { n: { a: [-5, 120] }, f: { a: [-6, -6] } }, kb: { mode: "rack", hand: "n" } }), "Drive the hips, elbow close to the body — guide the bell around the hand, don't let it flip and bang", 250, 0),
    K(S({ arms: { n: RACK, f: { a: [-6, -6] } }, kb: { mode: "rack", hand: "n" } }), "Catch it softly in the rack: elbow on the ribs, wrist straight", 450, 500),
    K(S({ arms: { n: { a: [14, 14] }, f: { a: [-6, -6] } }, kb: { mode: "swing", hand: "n" } }), "Let it drop back into the swing", 350, 0),
  ] },
  "turkish get-up": { keys: TGU },
  "romanian deadlift": { guide: true, keys: [
    K(hinge(9, -9, 0, { arms: { n: { a: [4, 4] }, f: { a: [2, 2] } }, kb: { mode: "hang", hand: "both" } }),
      "Stand tall, knees soft, bell in front of the thighs", 1200, 300),
    K(hinge(30, 10, 70, { arms: { n: { a: [-12, -12] }, f: { a: [-12, -12] } }, kb: { mode: "hang", hand: "both" } }),
      "Push the hips back, bell close to the legs, to just below the knees — or until your back starts to round", 1200, 350),
  ] },
  "thruster": { keys: [
    K(hinge(95, -30, 32, { arms: { n: RACK, f: { a: [30, 30] } }, kb: { mode: "rack", hand: "n" }, nk: -15 }),
      "Squat with the bell in the rack, chest up, heels down", 700, 200),
    K(S({ arms: { n: { a: [178, 178] }, f: { a: [10, 10] } }, kb: { mode: "press", hand: "n" } }),
      "Drive up and press overhead in one motion. Finish tall, bicep by the ear", 750, 300),
  ] },
  "high pull": { guide: true, keys: [
    K(HIKE({ n: { a: [-58, -58] }, f: { a: [-6, -6] } }, "n"), "Hike the bell back, flat back", 380, 0),
    K(S({ arms: { n: { a: [-95, 80] }, f: { a: [-6, -6] } }, kb: { mode: "swing", hand: "n" } }), "Hips drive, then pull the elbow high and back, bell close to the chest", 380, 150),
    K(S({ arms: { n: { a: [16, 16] }, f: { a: [-6, -6] } }, kb: { mode: "swing", hand: "n" } }), "Push it back out into the swing", 330, 0),
  ] },
  "suitcase carry": { keys: (() => {
    const pose = (n, f, fa) => ({ h: [99, 88], t: 0, legs: { n: { a: n }, f: { a: f } }, arms: { n: { a: [2, 2] }, f: { a: [fa, fa] } }, kb: { mode: "hang", hand: "n" } });
    return [
      K(pose([0, 0], [0, 0], 0), "Bell in one hand by your side. Stand tall — don't lean toward it", 600, 150),
      K(pose([55, -5], [0, 0], -10), "March slowly: knee up, shoulders level, core braced", 600, 150),
      K(pose([0, 0], [0, 0], 0), "Stay perfectly upright", 600, 150),
      K(pose([0, 0], [55, -5], 10), "Other knee. Switch hands halfway", 600, 150),
    ];
  })() },
};
DEMOS["swing + push-up finisher"].keys[0].cut = true;

const ALIASES = {
  "goblet reverse lunge": "reverse lunge (goblet)", "reverse lunge": "reverse lunge (goblet)", "lunge": "reverse lunge (goblet)",
  "swing": "two-hand swing", "kettlebell swing": "two-hand swing", "deadlift": "kettlebell deadlift", "rdl": "romanian deadlift",
  "clean": "kettlebell clean", "overhead press": "single-arm overhead press", "press": "single-arm overhead press",
  "row": "single-arm row", "tgu": "turkish get-up", "get-up": "turkish get-up", "pushup": "push-up", "press-up": "push-up",
  "carry": "suitcase carry", "march": "suitcase carry", "side bridge": "side plank", "bird-dog": "bird dog",
};

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
const pts = a => a.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");

function build() {
  const svg = mk("svg", { viewBox: "-15 -52 250 238", class: "demo-svg", role: "img" });
  svg.append(mk("line", { x1: -15, x2: 235, y1: GY + 1.5, y2: GY + 1.5, class: "demo-ground" }));
  const P = {};
  const line = cls => mk("polyline", { class: cls, fill: "none" });
  P.dowel = mk("line", { class: "demo-dowel" });
  P.legF = line("demo-limb demo-far demo-leg"); P.footF = line("demo-limb demo-far demo-foot");
  P.armF = line("demo-limb demo-far demo-arm");
  P.torso = mk("line", { class: "demo-torso" });
  P.neck = mk("line", { class: "demo-neck" });
  P.head = mk("circle", { r: L.head, class: "demo-head" });
  P.nose = mk("line", { class: "demo-nose" });
  P.legN = line("demo-limb demo-leg"); P.footN = line("demo-limb demo-foot");
  P.bell = mk("g", { class: "demo-bell" });
  P.bellHandle = mk("circle", { r: 6, class: "demo-bell-handle" });
  P.bellBody = mk("circle", { r: 10, class: "demo-bell-body" });
  P.bell.append(P.bellHandle, P.bellBody);
  P.armN = line("demo-limb demo-arm");
  svg.append(P.dowel, P.legF, P.footF, P.armF, P.torso, P.neck, P.head, P.nose, P.legN, P.footN, P.bell, P.armN);
  svg._parts = P;
  return svg;
}

function frame(svg, g, guide) {
  const P = svg._parts;
  const seg = (el, a, b) => { el.setAttribute("x1", a[0]); el.setAttribute("y1", a[1]); el.setAttribute("x2", b[0]); el.setAttribute("y2", b[1]); };
  const poly = (el, a) => el.setAttribute("points", pts(a));
  poly(P.legF, [g.hip, ...g.legs.f]); poly(P.footF, footPts(g.legs.f[0], g.legs.f[1], g.feet.f[0], g.view, g.feet.f[1]));
  poly(P.legN, [g.hip, ...g.legs.n]); poly(P.footN, footPts(g.legs.n[0], g.legs.n[1], g.feet.n[0], g.view, g.feet.n[1]));
  poly(P.armF, [g.sh, ...g.arms.f]); poly(P.armN, [g.sh, ...g.arms.n]);
  seg(P.torso, g.hip, g.sh); seg(P.neck, g.sh, g.head);
  P.head.setAttribute("cx", g.head[0]); P.head.setAttribute("cy", g.head[1]);
  if (g.view === "front") P.nose.style.display = "none";
  else { P.nose.style.display = ""; const b = add(g.head, sub(g.sh, g.head), 0.18); seg(P.nose, add(b, g.face, L.head - 3), add(b, g.face, L.head + 2.5)); }
  if (g.bell) {
    P.bell.style.display = "";
    P.bellBody.setAttribute("cx", g.bell.c[0]); P.bellBody.setAttribute("cy", g.bell.c[1]);
    const m = [(g.bell.hand[0] * 0.65 + g.bell.c[0] * 0.35), (g.bell.hand[1] * 0.65 + g.bell.c[1] * 0.35)];
    P.bellHandle.setAttribute("cx", m[0]); P.bellHandle.setAttribute("cy", m[1]);
  } else P.bell.style.display = "none";
  // neutral-spine dowel: shown while hinged (torso 25–85° forward, upright on the feet)
  const show = guide && g.td[1] < -0.08 && g.td[1] > -0.91 && g.td[0] > 0;
  if (show) {
    const back = g.fn.map(v => -v * (L.half + 1.5));
    seg(P.dowel, add(add(g.hip, g.td, -16), back), add(add(g.sh, g.td, L.neck + L.head + 10), back));
    P.dowel.style.display = "";
  } else P.dowel.style.display = "none";
}

function phaseAt(keys, ms) {
  const total = keys.reduce((s, k) => s + k.hold + k.move, 0);
  let t = ms % total;
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i], nx = keys[(i + 1) % keys.length];
    if (t < k.hold) return { pose: k.pose, cap: k.cap };
    t -= k.hold;
    if (t < k.move) {
      const f = t / k.move;
      const pose = nx.cut ? (f < .5 ? k.pose : nx.pose) : lerp(k.pose, nx.pose, ease(f));
      return { pose, cap: f < .55 ? k.cap : nx.cap };
    }
    t -= k.move;
  }
  return { pose: keys[0].pose, cap: keys[0].cap };
}

function fitView(svg, keys) {
  const total = keys.reduce((s, k) => s + k.hold + k.move, 0);
  let x0 = 1e9, x1 = -1e9, y0 = 1e9;
  const take = (p, r = 0) => { x0 = Math.min(x0, p[0] - r); x1 = Math.max(x1, p[0] + r); y0 = Math.min(y0, p[1] - r); };
  for (let t = 0; t < total; t += Math.max(20, total / 80)) {
    const g = solve(phaseAt(keys, t).pose);
    [g.hip, g.sh, ...g.legs.n, ...g.legs.f, ...g.arms.n, ...g.arms.f].forEach(p => take(p, 6));
    take(g.head, L.head + 4); take(g.hip, L.half + 2); take(g.sh, L.half + 2);
    if (g.bell) take(g.bell.c, 12);
    footPts(g.legs.n[0], g.legs.n[1], g.feet.n[0], g.view, g.feet.n[1]).forEach(p => take(p, 4));
  }
  const pad = 8, y1 = GY + 6;
  let w = x1 - x0 + 2 * pad, h = y1 - (y0 - pad);
  const minW = 170, minH = 120;
  if (w < minW) { x0 -= (minW - w) / 2; w = minW; }
  if (h < minH) { y0 -= (minH - h); h = minH; }
  const vx = x0 - pad, vy = y1 - h;
  svg.setAttribute("viewBox", `${vx.toFixed(1)} ${vy.toFixed(1)} ${w.toFixed(1)} ${h.toFixed(1)}`);
  const gl = svg.querySelector(".demo-ground"); gl.setAttribute("x1", vx); gl.setAttribute("x2", vx + w);
}

function create(ex) {
  const key = keyFor(ex);
  if (!key) return null;
  const demo = DEMOS[key], keys = demo.keys, svg = build();
  fitView(svg, keys);
  if (demo.view === "front") {
    const vb = svg.getAttribute("viewBox").split(" ").map(Number);
    const tx = mk("text", { x: vb[0] + 4, y: vb[1] + 12, class: "demo-note" }); tx.textContent = "Viewed from the front";
    svg.append(tx);
  }
  const wrap = document.createElement("div"); wrap.className = "demo-wrap";
  const cap = document.createElement("div"); cap.className = "demo-cap";
  wrap.append(svg, cap);
  if (demo.guide) {
    const lg = document.createElement("div"); lg.className = "demo-legend";
    lg.innerHTML = '<span class="demo-legend-line"></span> Flat back: head, upper back and tailbone stay on this line';
    wrap.append(lg);
  }
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const show = ph => { frame(svg, solve(ph.pose), demo.guide); if (cap.textContent !== ph.cap) cap.textContent = ph.cap || ""; };
  show({ pose: keys[0].pose, cap: keys[0].cap });
  let t0 = null;
  const tick = now => {
    if (!wrap.isConnected && t0 !== null) return;     // card closed / re-rendered: stop
    if (t0 === null) t0 = now;
    if (!reduce) show(phaseAt(keys, now - t0));
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  return wrap;
}

window.FitDemos = { create, keyFor, names: () => Object.keys(DEMOS),
  _: { solve, phaseAt, DEMOS, build, frame, footPts, L, GY } };
})();
