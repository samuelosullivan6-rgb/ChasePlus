(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const D = JSON.parse(document.getElementById("card-data").textContent);
  const M = window.CardMath;
  const T = (id) => { const e = document.getElementById(id); return e ? e.textContent : null; };
  const IT = (id) => { const e = document.getElementById(id); return e ? e.innerText : null; };
  const out = { season: D.season, footer: T("footer"), countNote: D.countNote, evidence: D.evidence, guide: D.guide, groups: D.countGroups, roster: {}, cards: [], errors: [] };

  // ---- roster view ----
  location.hash = "#roster";
  await sleep(300);
  out.roster.title = T("roster-title"); out.roster.lede = T("roster-lede"); out.roster.glossary = T("roster-glossary"); out.roster.state = T("state");
  out.roster.head = [...document.querySelectorAll("#roster-table thead th")].map((th) => th.textContent);
  out.roster.rows = [...document.querySelectorAll("#roster-table tbody tr")].map((tr) => [...tr.children].map((td) => td.textContent));

  // ---- pitches, decoded as the page does, for the leak-marker checks ----
  const bytes = new Uint8Array(await (await fetch(D.pitchFile)).arrayBuffer());
  const REC = D.recordBytes, N = bytes.length / REC, dv = new DataView(bytes.buffer);
  const Q = { x: new Float64Array(N), z: new Float64Array(N), chase: new Uint8Array(N), whiff: new Uint8Array(N), rhp: new Uint8Array(N), lhb: new Uint8Array(N), group: new Uint8Array(N), pitch: new Uint8Array(N), eMatch: new Float64Array(N) };
  for (let i = 0; i < N; i++) {
    const o = i * REC, f = bytes[o + 4];
    Q.x[i] = dv.getInt16(o, true) / 100; Q.z[i] = dv.getInt16(o + 2, true) / 100;
    Q.chase[i] = f & 1; Q.whiff[i] = (f >> 1) & 1; Q.rhp[i] = (f >> 2) & 1; Q.lhb[i] = (f >> 7) & 1;
    Q.group[i] = (f >> 3) & 3; Q.pitch[i] = (f >> 5) & 3; Q.eMatch[i] = bytes[o + 6] / 255;
  }
  const XS = Float64Array.from(D.xs), ZS = Float64Array.from(D.zs), NX = XS.length;
  const GKEYS = D.countGroups.map((g) => g.key);
  function surf(p, gi, hand, side) {
    const idx = [];
    for (let i = p.off; i < p.off + p.n; i++) {
      if (Q.group[i] !== gi) continue;
      if (side && (Q.lhb[i] ? "L" : "R") !== side) continue;
      if (hand === "R" && !Q.rhp[i]) continue;
      if (hand === "L" && Q.rhp[i]) continue;
      idx.push(i);
    }
    const x = new Float64Array(idx.length), z = new Float64Array(idx.length), y = new Float64Array(idx.length), e = new Float64Array(idx.length);
    idx.forEach((i, k) => { x[k] = Q.x[i]; z[k] = Q.z[i]; y[k] = Q.chase[i]; e[k] = Q.eMatch[i]; });
    const s = M.surface(x, z, y, e, XS, ZS); s.n = idx.length; return s;
  }
  const near = (arr, v) => { let b = 0; for (let k = 1; k < arr.length; k++) if (Math.abs(arr[k] - v) < Math.abs(arr[b] - v)) b = k; return b; };
  function rowsFor(p) {
    let rows = p.bats === "S"
      ? [["Batting left", "L", "all", "chase"], ["Batting right", "R", "all", "chase"]]
      : [["All pitchers", p.bats, "all", "chase"], ["vs RHP", p.bats, "R", "chase"], ["vs LHP", p.bats, "L", "chase"]];
    if (p.contact_led !== undefined ? p.contact_led : p.archetype === "execution-led") rows.push(["Misses on chases", p.bats, "all", "whiff"]);
    return rows;
  }

  // ---- every card, in each hand view ----
  const everyone = D.references.concat(D.players);
  for (const p of everyone) {
    try {
      location.hash = "#" + p.slug;
      let ok = false;
      for (let k = 0; k < 400; k++) {
        if (T("name") === p.name && !document.getElementById("card").hidden && document.querySelector("#aside section")) { ok = true; break; }
        await sleep(50);
      }
      if (!ok) { out.errors.push(`${p.slug}: did not render`); continue; }
      await sleep(20);
      const rec = { slug: p.slug, name: p.name, reference: !!p.reference };
      rec.notice = document.getElementById("notice").hidden ? "" : T("notice");
      rec.state = T("state"); rec.line1 = T("line1"); rec.line2 = T("line2");
      rec.tiles = IT("tiles");
      rec.colheads = [...document.querySelectorAll("#zgrid .colhead")].map((e) => e.textContent);
      rec.rowheads = [...document.querySelectorAll("#zgrid .rowhead")].map((e) => e.textContent);
      const sel = document.querySelector("#zgrid canvas.selected");
      rec.selected = sel ? sel.getAttribute("aria-label") : null;
      rec.selected_key = sel ? sel.dataset.key : null;
      rec.orient = T("orient"); rec.legend = T("legend");
      rec.numbers_note = T("numbers-note");
      rec.numbers = [...document.querySelectorAll("#numbers-table tr")].map((tr) => [...tr.children].map((c) => c.textContent).join(" | "));
      const tw = document.querySelector(".tablewrap");
      rec.table_overflow = tw ? tw.scrollWidth - tw.clientWidth : null;
      rec.aside = {};
      for (const h of ["all", "R", "L"]) {
        const r = document.getElementById("hand-" + h); r.checked = true; r.dispatchEvent(new Event("change", { bubbles: true }));
        await sleep(5);
        rec.aside[h] = IT("aside") + (document.getElementById("more") ? "\n" + IT("more") : "");
        if (h !== "all") rec["state_" + h] = T("state");
      }
      const r0 = document.getElementById("hand-all"); r0.checked = true; r0.dispatchEvent(new Event("change", { bubbles: true }));
      if (!p.reference) {
        // where each leak's number is drawn, and what the picture says right there
        const rows = rowsFor(p);
        const placed = {};
        rec.markers = (p.leaks.all || []).map((lk, k) => {
          let row = rows.findIndex((r) => r[1] === lk.side && r[2] === (lk.hand || "all") && r[3] === "chase");
          let fallback = false;
          if (row < 0) { row = rows.findIndex((r) => r[1] === lk.side && r[3] === "chase"); fallback = row >= 0; }
          if (row < 0) return { n: k + 1, drawn: false };
          const key = row + "|" + lk.count_group, taken = placed[key] || [];
          const s = surf(p, GKEYS.indexOf(lk.count_group), rows[row][2], rows[row][1]);
          let x = lk.x, z = lk.z;
          const NEW = p.contact_led !== undefined;      // the rebuilt page snaps and spaces 0.7 ft
          const SEP = NEW ? 0.7 : 0.5;
          if (NEW) {
            const gi = (arr, v) => Math.max(0, Math.min(arr.length - 1, Math.round((v - arr[0]) / D.gridStep)));
            const reg = (xx, zz) => { const xb = rows[row][1] === "L" ? -xx : xx; return ((zz > p.zone[1] ? "up" : zz < p.zone[0] ? "down" : "") + "-" + (xb < -0.83 ? "in" : xb > 0.83 ? "away" : "")).replace(/^-|-$/g, ""); };
            const mask = M.zoneMask(XS, ZS, p.zone[0], p.zone[1]);
            if (s.gap[gi(ZS, z) * NX + gi(XS, x)] < 0.05) {
              let best = null;
              for (let b = gi(ZS, lk.z - 1.0); b <= gi(ZS, lk.z + 1.0); b++) for (let a = gi(XS, lk.x - 1.0); a <= gi(XS, lk.x + 1.0); a++) {
                const j = b * NX + a, dd = Math.hypot(XS[a] - lk.x, ZS[b] - lk.z);
                if (dd > 1.0 || mask[j] || s.evidence[j] < 0.5 || s.gap[j] < 0.05 || reg(XS[a], ZS[b]) !== lk.region) continue;
                if (!best || dd < best.d) best = { d: dd, x: XS[a], z: ZS[b] };
              }
              if (best) { x = best.x; z = best.z; }
            }
          }
          const bx = x, bz = z;
          for (const [dx, dz] of [[0, 0], [SEP, 0], [-SEP, 0], [0, -SEP], [0, SEP], [SEP, -SEP], [-SEP, -SEP]]) {
            const cx = bx + dx, cz = bz + dz;
            if (taken.every(([, ox, oz]) => Math.hypot(cx - ox, cz - oz) >= SEP)) { x = cx; z = cz; break; }
          }
          (placed[key] = placed[key] || []).push([k + 1, x, z]);
          const at = (xx, zz) => { const j = near(ZS, zz) * NX + near(XS, xx); return { gap: Math.round(s.gap[j] * 100), evidence: +s.evidence[j].toFixed(2), you: Math.round(s.playerRate[j] * 100), avg: Math.round(s.leagueRate[j] * 100) }; };
          const inZone = Math.abs(x) < 0.83 && z > p.zone[0] && z < p.zone[1];
          return { n: k + 1, drawn: true, row: rows[row][0], row_fallback: fallback, group: lk.count_group, moved: Math.hypot(x - lk.x, z - lk.z) > 1e-9,
                   leak_xz: [lk.x, lk.z], marker_xz: [+x.toFixed(2), +z.toFixed(2)], in_zone_box: inZone,
                   off_grid: x < XS[0] || x > XS[XS.length - 1] || z < ZS[0] || z > ZS[ZS.length - 1],
                   at_leak: at(lk.x, lk.z), at_marker: at(x, z), panel_pitches: s.n };
        });
      }
      out.cards.push(rec);
    } catch (e) { out.errors.push(`${p.slug}: ${e && e.message}`); }
  }
  out.data = { players: D.players.map((p) => { const q = Object.assign({}, p); delete q.grids; return q; }), references: D.references.map((r) => ({ slug: r.slug, name: r.name, table: r.table })), leagueTrend: D.leagueTrend, defaultSlug: D.defaultSlug };
  return JSON.stringify(out);
})()
