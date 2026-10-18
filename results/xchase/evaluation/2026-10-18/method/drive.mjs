import { spawn } from "node:child_process";
import { writeFileSync, readFileSync, mkdirSync } from "node:fs";
const [,, url, expressionFile, outFile] = process.argv;
const port = 9333;
const prof = new URL("./chrome-prof", import.meta.url).pathname;
mkdirSync(prof, { recursive: true });
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`, "--window-size=1440,1000", "--no-first-run", "--disable-gpu", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let list;
for (let k = 0; k < 50; k++) { try { list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); if (list.length) break; } catch (e) {} await sleep(200); }
const page = list.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0; const pending = new Map();
ws.addEventListener("message", (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send("Page.enable"); await send("Runtime.enable");
await send("Page.navigate", { url });
await sleep(4000);
const expr = readFileSync(expressionFile, "utf8");
const res = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true, timeout: 1800000 });
if (res.result && res.result.exceptionDetails) { console.error(JSON.stringify(res.result.exceptionDetails).slice(0, 2000)); }
else if (res.error) console.error(JSON.stringify(res.error));
else { writeFileSync(outFile, res.result.result.value); console.log("wrote", outFile, res.result.result.value.length); }
ws.close(); chrome.kill();
process.exit(0);
