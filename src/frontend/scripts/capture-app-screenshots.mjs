// Capture the workbench tab views and Overview section crops. Run from src/frontend with the
// workbench running (scripts/app.sh start). GIFs are captured separately by capture-architecture-gif.mjs.
// Usage: cd src/frontend && node scripts/capture-app-screenshots.mjs
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const OUT = "/home/brittanypugh/foundry-copilot-hr-policy-knowledge/docs/images/app";
const BASE = process.env.WORKBENCH_URL || "http://127.0.0.1:5174";
mkdirSync(`${OUT}/overview`, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
const settle = async (ms = 1300) => { await page.waitForLoadState("networkidle").catch(() => {}); await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(ms); };

// --- Tab views ---
await page.goto(`${BASE}/`, { waitUntil: "networkidle" }); await settle();
await page.screenshot({ path: `${OUT}/01-overview.png`, fullPage: true });
await page.goto(`${BASE}/experiments`, { waitUntil: "networkidle" }); await settle(1600);
await page.screenshot({ path: `${OUT}/02-experiments-latency.png`, fullPage: true });
try {
  await page.locator("table tbody tr, a[href*='/experiments/']").first().click({ timeout: 4000 });
  await settle(1400);
  await page.screenshot({ path: `${OUT}/03-experiment-detail.png`, fullPage: true });
} catch (e) { console.log("detail-click-failed", e.message); }
for (const [route, file] of [["/compare", "04-compare"], ["/pareto", "05-pareto-slo"], ["/coverage", "06-evidence-coverage"], ["/glossary", "07-glossary"]]) {
  await page.goto(`${BASE}${route}`, { waitUntil: "networkidle" }); await settle(1400);
  await page.screenshot({ path: `${OUT}/${file}.png`, fullPage: true });
}

// --- Overview section crops (group each eyebrow .section-title with the block that follows) ---
await page.goto(`${BASE}/`, { waitUntil: "networkidle" }); await settle(1500);
const regions = await page.locator("main > section.overview-page").evaluate((root) => {
  const slug = (s) => (s || "section").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);
  const eyebrow = (el) => { const e = el.querySelector("p, span"); const t = (e?.innerText || "").trim().split("\n")[0]; const h = el.querySelector("h1,h2,h3,h4"); return (t || h?.innerText || el.className || "section").trim(); };
  const out = []; let pTop = null, pLeft = null, pRight = null, pName = null;
  for (const child of root.children) {
    const r = child.getBoundingClientRect(); const top = r.top + window.scrollY, bottom = r.bottom + window.scrollY;
    if ((child.className || "").toString().includes("section-title")) { pTop = top; pLeft = r.left; pRight = r.right; pName = eyebrow(child); continue; }
    out.push({ name: pName ?? eyebrow(child), top: pTop ?? top, bottom, left: Math.min(pLeft ?? r.left, r.left), right: Math.max(pRight ?? r.right, r.right) });
    pTop = pLeft = pRight = pName = null;
  }
  const seen = {};
  const numbered = out.map((s, i) => {
    let base = slug(s.name);
    if (base.startsWith("fork-this-workbench")) base = "reuse-footer";
    else if (base === "architecture-paths") { base = (seen["architecture-paths"] || 0) === 0 ? "path-stats" : "architecture-paths"; seen["architecture-paths"] = (seen["architecture-paths"] || 0) + 1; }
    return { file: String(i + 1).padStart(2, "0") + "-" + base + ".png", x: Math.max(0, Math.floor(s.left - 24)), y: Math.max(0, Math.floor(s.top - 16)), width: Math.ceil(Math.min(1600, s.right + 24) - Math.max(0, s.left - 24)), height: Math.ceil(s.bottom - s.top + 32) }; });
  return { pageHeight: Math.ceil(root.getBoundingClientRect().height + 200), sections: numbered };
});
await page.setViewportSize({ width: 1600, height: Math.min(regions.pageHeight, 8000) });
await page.waitForTimeout(400);
for (const s of regions.sections) {
  await page.screenshot({ path: `${OUT}/overview/${s.file}`, clip: { x: s.x, y: s.y, width: s.width, height: s.height } });
}
await browser.close();
console.log("captured", regions.sections.length, "overview sections + 7 tab views");
