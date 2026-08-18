import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("list, detail, compare, Pareto, and coverage workflow", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Grounded agent — architecture benchmark" })).toBeVisible();
  await expect(page.getByText("LOCAL EVIDENCE", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Provenance" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "HR assistant" })).toHaveCount(0);
  await expect(page.locator(".decision-ribbon")).toContainText("Hosted · Tool retrieval");
  await expect(page.getByText("Not measured", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Azure tools explain each system. This benchmark helps you choose across them." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Decision gaps this fills" })).toBeVisible();
  await expect(page.getByText("Apples-to-apples evidence")).toBeVisible();
  await expect(page.getByRole("heading", { name: "What remains Azure-native" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "When to use the benchmark and when to stay native" })).toBeVisible();
  await expect(page.getByText("Production · Azure services lead")).toBeVisible();

  const toolMode = page.locator(".mode-comparison article").filter({ hasText: "Tool retrieval" });
  const semanticMode = page.locator(".mode-comparison article").filter({ hasText: "Semantic context" });
  const agenticMode = page.locator(".mode-comparison article").filter({ hasText: "Agentic context" });
  await expect(toolMode.locator("strong")).toHaveText("100.0%");
  await expect(semanticMode.locator("strong")).toHaveText("71.4%");
  await expect(agenticMode.locator("strong")).toHaveText("100.0%");

  const patternA = page.locator(".architecture-card").filter({ hasText: "Measured evidence" }).filter({ hasText: "automated direct Search" });
  const patternC = page.locator(".architecture-card").filter({ hasText: "automated deterministic lookup" });
  await expect(patternA).toBeVisible();
  await expect(patternC.getByText("Measured evidence")).toBeVisible();
  await semanticMode.getByRole("link", { name: "Open evidence" }).click();
  await expect(page.getByRole("heading", { name: "Run configuration" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "How to read latency percentiles" })).toBeVisible();
  await expect(page.getByText("This is the median, not the average.", { exact: false })).toBeVisible();
  await expect(page.getByText("the slowest 5% took longer", { exact: false })).toBeVisible();
  await expect(page.getByText("Git commit", { exact: true })).toHaveCount(0);
  await expect(page).toHaveURL(/\/experiments\/agent-framework-context-semantic-publication/);
  await expect(page.getByRole("heading", { name: /agent-framework-context-semantic-publication/ })).toBeVisible();

  await page.getByRole("link", { name: "Compare" }).click();
  await expect(page.getByRole("heading", { name: "Compare runs" })).toBeVisible();
  await expect(page).toHaveURL(/\/compare/);

  await page.getByRole("link", { name: "Pareto / SLO" }).click();
  await expect(page.getByRole("heading", { name: "Pareto and SLO" })).toBeVisible();
  await expect(page.locator(".plot-frame")).toBeVisible();

  await page.getByRole("link", { name: "Evidence coverage" }).click();
  await expect(page.getByRole("heading", { name: "Evidence coverage" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Where to inspect every evidence source" })).toBeVisible();
  await expect(page.locator(".evidence-source")).toHaveCount(5);
  const applicationInsightsGuide = page.locator(".evidence-source").filter({ has: page.getByRole("heading", { name: "Application Insights", exact: true }) });
  await expect(applicationInsightsGuide.getByText("Agent details: Preview")).toBeVisible();
  await expect(applicationInsightsGuide.getByText("How to investigate")).toBeVisible();
  await expect(applicationInsightsGuide.locator(".source-action")).toBeVisible();
  const foundryGuide = page.locator(".evidence-source").filter({ has: page.getByRole("heading", { name: "Microsoft Foundry", exact: true }) });
  await expect(foundryGuide.getByText("Agent Monitoring: Preview")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Benchmark Blog Outline readiness" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "All repository and Microsoft capabilities" })).toHaveCount(0);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow, `${testInfo.project.name} layout has horizontal overflow`).toBe(false);
});

test("overview has no serious accessibility violations", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Grounded agent — architecture benchmark" })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""));
  expect(serious).toEqual([]);
});