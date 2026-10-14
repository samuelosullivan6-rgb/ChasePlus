/*
 * JavaScript twin of scripts/card_surfaces.py, used by player_cards.html.
 * The constants and the arithmetic must match the Python file exactly;
 * step 17 runs both on one hitter and stops if they disagree.
 */
(function (root) {
  "use strict";

  const C = {
    HALF_PLATE_PLUS_BALL: 0.83,
    BANDWIDTH: 0.28,
    KERNEL_REACH: 3.0,
    PRIOR_PITCHES: 3.0,
    EVIDENCE_PITCHES: 1.5,
    GAP_LIMIT: 0.30,
    CONTOUR_GAP: 0.15,
    CONTOUR_MIN_EVIDENCE: 0.5,
    OUTLINE_MIN_AREA: 0.35,
    OUTLINE_MIN_LENGTH: 1.6,
  };

  function kernelRow(p, grid) {
    const reach = C.KERNEL_REACH * C.BANDWIDTH;
    const out = new Float64Array(grid.length);
    let lo = -1, hi = -1;
    for (let a = 0; a < grid.length; a++) {
      const d = grid[a] - p;
      if (Math.abs(d) > reach) continue;
      out[a] = Math.exp(-0.5 * (d / C.BANDWIDTH) * (d / C.BANDWIDTH));
      if (lo < 0) lo = a;
      hi = a;
    }
    return { k: out, lo, hi };
  }

  // gap, evidence, weight, player rate, league rate on the grid.
  // Arrays are row-major with rows = z (bottom to top), columns = x.
  function surface(x, z, y, e, xs, zs) {
    const nx = xs.length, nz = zs.length, size = nx * nz;
    const weight = new Float64Array(size);
    const extra = new Float64Array(size);
    const observed = new Float64Array(size);
    const expected = new Float64Array(size);
    for (let i = 0; i < x.length; i++) {
      const kx = kernelRow(x[i], xs);
      const kz = kernelRow(z[i], zs);
      if (kx.lo < 0 || kz.lo < 0) continue;
      const r = y[i] - e[i];
      for (let b = kz.lo; b <= kz.hi; b++) {
        const wb = kz.k[b];
        const row = b * nx;
        for (let a = kx.lo; a <= kx.hi; a++) {
          const w = wb * kx.k[a];
          weight[row + a] += w;
          extra[row + a] += w * r;
          observed[row + a] += w * y[i];
          expected[row + a] += w * e[i];
        }
      }
    }
    const gap = new Float64Array(size);
    const evidence = new Float64Array(size);
    const playerRate = new Float64Array(size);
    const leagueRate = new Float64Array(size);
    for (let j = 0; j < size; j++) {
      gap[j] = extra[j] / (weight[j] + C.PRIOR_PITCHES);
      evidence[j] = weight[j] / (weight[j] + C.EVIDENCE_PITCHES);
      playerRate[j] = weight[j] > 1e-6 ? observed[j] / weight[j] : NaN;
      leagueRate[j] = weight[j] > 1e-6 ? expected[j] / weight[j] : NaN;
    }
    return { gap, evidence, weight, playerRate, leagueRate };
  }

  // True inside the hitter's own zone (bottom and top in feet).
  function zoneMask(xs, zs, bottom, top) {
    const m = new Uint8Array(xs.length * zs.length);
    for (let b = 0; b < zs.length; b++)
      for (let a = 0; a < xs.length; a++)
        m[b * xs.length + a] =
          Math.abs(xs[a]) < C.HALF_PLATE_PLUS_BALL && zs[b] > bottom && zs[b] < top ? 1 : 0;
    return m;
  }

  // The +15 outline: marching squares on the gap, skipping any cell that
  // touches the zone or thin evidence, then joining segments into lines
  // and dropping specks (same thresholds as the Python version).
  function outlines(gap, evidence, mask, xs, zs) {
    const nx = xs.length, nz = zs.length, L = C.CONTOUR_GAP;
    const ok = (j) => !mask[j] && evidence[j] >= C.CONTOUR_MIN_EVIDENCE;
    const segs = [];
    const lerp = (p, q, vp, vq) => p + ((L - vp) / (vq - vp)) * (q - p);
    for (let b = 0; b < nz - 1; b++) {
      for (let a = 0; a < nx - 1; a++) {
        const j00 = b * nx + a, j10 = j00 + 1, j01 = j00 + nx, j11 = j01 + 1;
        if (!(ok(j00) && ok(j10) && ok(j01) && ok(j11))) continue;
        const v = [gap[j00], gap[j10], gap[j11], gap[j01]];
        const idx = (v[0] >= L ? 1 : 0) | (v[1] >= L ? 2 : 0) | (v[2] >= L ? 4 : 0) | (v[3] >= L ? 8 : 0);
        if (idx === 0 || idx === 15) continue;
        const x0 = xs[a], x1 = xs[a + 1], z0 = zs[b], z1 = zs[b + 1];
        const E = {
          s: [lerp(x0, x1, v[0], v[1]), z0],
          e: [x1, lerp(z0, z1, v[1], v[2])],
          n: [lerp(x0, x1, v[3], v[2]), z1],
          w: [x0, lerp(z0, z1, v[0], v[3])],
        };
        const table = {
          1: [["w", "s"]], 2: [["s", "e"]], 3: [["w", "e"]], 4: [["e", "n"]],
          5: [["w", "n"], ["s", "e"]], 6: [["s", "n"]], 7: [["w", "n"]], 8: [["n", "w"]],
          9: [["n", "s"]], 10: [["n", "e"], ["w", "s"]], 11: [["n", "e"]], 12: [["e", "w"]],
          13: [["e", "s"]], 14: [["s", "w"]],
        };
        for (const [p, q] of table[idx]) segs.push([E[p], E[q]]);
      }
    }
    // join segments that share endpoints
    const key = (pt) => pt[0].toFixed(4) + "," + pt[1].toFixed(4);
    const ends = new Map();
    segs.forEach((s, i) => {
      for (const pt of s) {
        const k = key(pt);
        if (!ends.has(k)) ends.set(k, []);
        ends.get(k).push(i);
      }
    });
    const used = new Uint8Array(segs.length);
    const lines = [];
    for (let i = 0; i < segs.length; i++) {
      if (used[i]) continue;
      used[i] = 1;
      const line = [segs[i][0], segs[i][1]];
      for (const dir of [1, -1]) {
        for (;;) {
          const tip = dir === 1 ? line[line.length - 1] : line[0];
          const next = (ends.get(key(tip)) || []).find((j) => !used[j]);
          if (next === undefined) break;
          used[next] = 1;
          const s = segs[next];
          const other = key(s[0]) === key(tip) ? s[1] : s[0];
          if (dir === 1) line.push(other); else line.unshift(other);
        }
      }
      let length = 0;
      for (let k = 1; k < line.length; k++)
        length += Math.hypot(line[k][0] - line[k - 1][0], line[k][1] - line[k - 1][1]);
      const closed = key(line[0]) === key(line[line.length - 1]);
      if (closed) {
        let area = 0;
        for (let k = 0; k < line.length - 1; k++)
          area += line[k][0] * line[k + 1][1] - line[k + 1][0] * line[k][1];
        if (Math.abs(area) / 2 >= C.OUTLINE_MIN_AREA) lines.push(line);
      } else if (length >= C.OUTLINE_MIN_LENGTH) {
        lines.push(line);
      }
    }
    return lines;
  }

  // ---- color, in OKLab, the same as the Python renderer ----
  const lin = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  const gam = (c) => {
    c = Math.min(1, Math.max(0, c));
    return c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
  };
  function hexRgb(h) {
    h = h.trim().replace("#", "");
    return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
  }
  function toLab(rgb) {
    const [r, g, b] = rgb.map(lin);
    const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
  }
  function fromLab([L, A, B]) {
    const l = Math.pow(L + 0.3963377774 * A + 0.2158037573 * B, 3);
    const m = Math.pow(L - 0.1055613458 * A - 0.0638541728 * B, 3);
    const s = Math.pow(L - 0.0894841775 * A - 1.291485548 * B, 3);
    return [gam(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
            gam(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
            gam(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s)];
  }
  function divergingScale(mid, neg, pos) {
    const M = toLab(hexRgb(mid)), N = toLab(hexRgb(neg)), P = toLab(hexRgb(pos));
    return (v) => {
      const t = Math.max(-1, Math.min(1, v / C.GAP_LIMIT));
      const end = t >= 0 ? P : N, f = Math.abs(t);
      return fromLab([0, 1, 2].map((k) => M[k] + f * (end[k] - M[k])));
    };
  }
  function sequentialScale(stops, top) {
    const labs = stops.map((s) => toLab(hexRgb(s)));
    return (v) => {
      const t = Math.max(0, Math.min(1, v / top)) * (labs.length - 1);
      const lo = Math.min(labs.length - 2, Math.floor(t)), f = t - lo;
      return fromLab([0, 1, 2].map((k) => labs[lo][k] * (1 - f) + labs[lo + 1][k] * f));
    };
  }

  const api = { C, surface, zoneMask, outlines, divergingScale, sequentialScale, hexRgb };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CardMath = api;
})(typeof window !== "undefined" ? window : globalThis);
