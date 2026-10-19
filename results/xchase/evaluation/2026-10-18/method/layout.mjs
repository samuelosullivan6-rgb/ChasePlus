// Layout measures on the card page at several widths: By count overflow, first-screen content, roster columns.
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
const base = process.argv[2] || "http://localhost:8765/2026/index.html";
const port = 9338, prof = new URL("./chrome-prof-layout3", import.meta.url).pathname; mkdirSync(prof, { recursive: true });
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`, "--hide-scrollbars", "--no-first-run", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let list; for (let k = 0; k < 150; k++) { try { list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); if (list.length) break; } catch (e) {} await sleep(200); }
const ws = new WebSocket(list.find((t) => t.type === "page").webSocketDebuggerUrl); await new Promise((r) => ws.addEventListener("open", r));
let id = 0; const pend = new Map(); ws.addEventListener("message", (ev) => { const m = JSON.parse(ev.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.result.value;
await send("Page.enable");
const out = {};
for (const w of (process.argv[3] || "390,768,1101,1280,1440,1920").split(",").map(Number)) {
  await send("Emulation.setDeviceMetricsOverride", { width: w, height: w < 768 ? 844 : 1000, deviceScaleFactor: 1, mobile: w < 768 });
  await send("Page.navigate", { url: "about:blank" }); await sleep(200);
  await send("Page.navigate", { url: base + "#roster" }); await sleep(2500);
  const roster = await ev(`(() => { const box = document.querySelector("#roster-view .scroll").getBoundingClientRect();
    const ths = [...document.querySelectorAll("#roster-table thead th")].map((th) => ({ t: th.textContent.replace(/[▼▲]/, ""), right: Math.round(th.getBoundingClientRect().right - box.right) }));
    return { scrollY: Math.round(window.scrollY), start: ths.find((x) => x.t === "Start with"), beat: ths.find((x) => x.t === "Beat"), pageScrollW: document.documentElement.scrollWidth }; })()`);
  const cards = await ev(`(async () => {
    const D = JSON.parse(document.getElementById("card-data").textContent); const res = { over: 0, n: 0, maxOver: 0, planY: [], picY: [], firstScreenPlan: 0, wide: 0 };
    for (const p of D.players) {
      location.hash = "#" + p.slug;
      for (let k = 0; k < 200 && !(document.getElementById("name").textContent === p.name && document.querySelector("#aside section")); k++) await new Promise((r) => setTimeout(r, 25));
      const tw = document.querySelector("#more .tablewrap"); const o = tw.scrollWidth - tw.clientWidth; res.n++; if (o > 2) { res.over++; res.maxOver = Math.max(res.maxOver, o); }
      const plan = document.querySelector("#aside h2").getBoundingClientRect().top + window.scrollY;
      const pic = document.querySelector("#zgrid canvas").getBoundingClientRect().top + window.scrollY;
      const planEnd = document.querySelector("#aside").getBoundingClientRect().bottom + window.scrollY;
      res.planY.push(Math.round(plan)); res.picY.push(Math.round(pic - planEnd));
      if (plan < window.innerHeight) res.firstScreenPlan++;
      if (document.documentElement.scrollWidth > window.innerWidth + 1) res.wide++;
    }
    const med = (a) => a.slice().sort((x, y) => x - y)[Math.floor(a.length / 2)];
    return { cards: res.n, tableOverflow: res.over, maxOverflowPx: res.maxOver, planHeadingMedianY: med(res.planY), planOnFirstScreen: res.firstScreenPlan, picturesBelowPlanEndMedianPx: med(res.picY), sidewaysScroll: res.wide };
  })()`);
  out[w] = { roster, cards };
  console.log(w, JSON.stringify(out[w]));
}
ws.close(); chrome.kill(); process.exit(0);
