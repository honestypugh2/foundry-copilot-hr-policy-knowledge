import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("list, detail, compare, Pareto, and coverage workflow", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Choose the right architecture for your HR policy assistant." })).toBeVisible();
  await expect(page.getByText("LOCAL EVIDENCE", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Provenance" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "HR assistant" })).toHaveCount(0);
  await expect(page.getByText("No configuration clears every active SLO")).toBeVisible();
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
  await expect(toolMode.getByText("100.0%", { exact: true })).toBeVisible();
  await expect(semanticMode.getByText("85.7%", { exact: true })).toBeVisible();
  await expect(agenticMode.getByText("85.7%", { exact: true })).toBeVisible();

  const patternA = page.locator(".architecture-card").filter({ hasText: "Fixture evidence" }).filter({ hasText: "automated direct Search" });
  const patternC = page.locator(".architecture-card").filter({ hasText: "automated deterministic lookup" });
  await expect(patternA).toBeVisible();
  await expect(patternC.getByText("Run required")).toBeVisible();
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
  await expect(page.getByLabel("Quality and latency plot")).toBeVisible();
  await expect(page.locator(".plot-point")).not.toHaveCount(0);

  await page.getByRole("link", { name: "Operations" }).click();
  await expect(page.getByRole("heading", { name: "Investigate benchmark results" })).toBeVisible();
  const operationsApplicationInsights = page.locator(".evidence-source").filter({ has: page.getByRole("heading", { name: "Application Insights", exact: true }) });
  await expect(operationsApplicationInsights.getByText("Agent details: Preview")).toBeVisible();
  await expect(operationsApplicationInsights.getByText("Open Performance, select the operation", { exact: false })).toBeVisible();
  await expect(operationsApplicationInsights.getByText("token and tool-call charts to explain a slowdown", { exact: false })).toBeVisible();
  const operationsFoundry = page.locator(".evidence-source").filter({ has: page.getByRole("heading", { name: "Microsoft Foundry", exact: true }) });
  await expect(operationsFoundry.getByText("Agent Monitoring: Preview")).toBeVisible();

  await page.getByRole("link", { name: "Evidence coverage" }).click();
  await expect(page.getByRole("heading", { name: "Evidence coverage" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Where to inspect every evidence source" })).toBeVisible();
  await expect(page.locator(".evidence-source")).toHaveCount(6);
  const applicationInsightsGuide = page.locator(".evidence-source").filter({ has: page.getByRole("heading", { name: "Application Insights", exact: true }) });
  await expect(applicationInsightsGuide.getByText("How to investigate")).toBeVisible();
  await expect(applicationInsightsGuide.locator(".source-action")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Benchmark Blog Outline readiness" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "All repository and Microsoft capabilities" })).toHaveCount(0);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow, `${testInfo.project.name} layout has horizontal overflow`).toBe(false);
});

test("overview has no serious accessibility violations", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Choose the right architecture for your HR policy assistant." })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""));
  expect(serious).toEqual([]);
});