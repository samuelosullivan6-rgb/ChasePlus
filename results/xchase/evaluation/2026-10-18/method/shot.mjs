// Screenshots of the card page in headless Chrome.
// node shot.mjs jobs.json   where jobs.json is [{url, width, height, dark, full, out, wait_ms}]
import { spawn } from "node:child_process";
import { writeFileSync, readFileSync, mkdirSync } from "node:fs";
const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const port = 9334;
const prof = new URL("./chrome-prof-shots", import.meta.url).pathname;
mkdirSync(prof, { recursive: true });
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`, "--hide-scrollbars", "--no-first-run", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let list;
for (let k = 0; k < 50; k++) { try { list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); if (list.length) break; } catch (e) {} await sleep(200); }
const ws = new WebSocket(list.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0; const pending = new Map();
ws.addEventListener("message", (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send("Page.enable");
for (const j of jobs) {
  const w = j.width || 1440, h = j.height || 1000;
  await send("Page.navigate", { url: "about:blank" }); await sleep(200);
  await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: j.scale || 1, mobile: w < 768 });
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: j.dark ? "dark" : "light" }] });
  await send("Page.navigate", { url: j.url });
  await sleep(j.wait_ms || 3500);
  let params = { format: "png" };
  if (j.full) {
    const m = await send("Page.getLayoutMetrics");
    const cs = m.result.cssContentSize || m.result.contentSize;
    params = { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: Math.max(w, Math.ceil(cs.width)), height: Math.min(Math.ceil(cs.height), 16000), scale: 1 } };
  }
  const res = await send("Page.captureScreenshot", params);
  const sw = await send("Runtime.evaluate", { expression: "JSON.stringify({scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth, scrollHeight: document.documentElement.scrollHeight})", returnByValue: true });
  writeFileSync(j.out, Buffer.from(res.result.data, "base64"));
  console.log(j.out, sw.result.result.value);
}
ws.close(); chrome.kill(); process.exit(0);
