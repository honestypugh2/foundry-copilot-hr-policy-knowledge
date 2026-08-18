// Capture the Overview architecture-map interaction as animation frames, in BOTH dark and
// light themes, using the app's REAL click behaviour (active node, updating detail card,
// animated dashed flow line). Frames are written to /tmp; assemble them into GIFs with
// scripts/assemble_gif.py (Pillow). See docs/images/app/README.md for the full workflow.
//
// Usage (workbench must be running — `scripts/app.sh start`):
//   cd src/frontend && node scripts/capture-architecture-gif.mjs
import { chromium } from "@playwright/test";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";

const BASE = process.env.WORKBENCH_URL || "http://127.0.0.1:5174";
const sequence = ["A", "A2", "B", "C", "H"];
const framesPerNode = 4;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1120 }, deviceScaleFactor: 1 });
await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

const themeToggle = () => page.getByRole("button", { name: /theme/i });
const currentTheme = () =>
  page.evaluate(() => document.documentElement.getAttribute("data-theme")
    || (document.documentElement.classList.contains("light") ? "light" : "dark"));

const clickNode = (label) => page.evaluate((lbl) => {
  const g = Array.from(document.querySelectorAll(".arch-map g.arch-node"))
    .find((x) => (x.querySelector("text")?.textContent || "").trim() === lbl);
  if (g) g.dispatchEvent(new MouseEvent("click", { bubbles: true }));
}, label);

async function captureTheme(dir) {
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  const mapTop = await page.locator(".arch-map").evaluate((m) => m.getBoundingClientRect().top + window.scrollY);
  await page.evaluate((y) => window.scrollTo(0, y - 16), mapTop);
  await page.waitForTimeout(400);
  const clip = await page.locator(".arch-map").evaluate((m) => {
    const r = m.getBoundingClientRect();
    return { x: Math.max(0, Math.floor(r.left)), y: Math.max(0, Math.floor(r.top)), width: Math.ceil(r.width), height: Math.ceil(r.height) };
  });
  const durations = [];
  let i = 0;
  for (const label of sequence) {
    await clickNode(label);
    await page.waitForTimeout(450); // let the detail card re-render
    for (let f = 0; f < framesPerNode; f++) {
      await page.screenshot({ path: `${dir}/f${String(i).padStart(3, "0")}.png`, clip });
      durations.push(f === framesPerNode - 1 ? 900 : 160); // march dashes fast, hold last frame
      i++;
      await page.waitForTimeout(150); // dash animation advances between frames
    }
  }
  writeFileSync(`${dir}/durations.json`, JSON.stringify(durations));
  return i;
}

if ((await currentTheme()) !== "dark") { await themeToggle().click(); await page.waitForTimeout(500); }
const nDark = await captureTheme("/tmp/archmap_dark");

await themeToggle().click();
await page.waitForTimeout(600);
const themeNow = await currentTheme();
const nLight = await captureTheme("/tmp/archmap_light");

await themeToggle().click(); // restore dark so the running app is left as it was
await browser.close();
console.log(`captured dark=${nDark} light=${nLight} (light theme reported '${themeNow}') for`, sequence.join(","));
