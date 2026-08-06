import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("list, detail, compare, and Pareto workflow", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Choose the right retrieval path." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Pattern B" })).toBeVisible();
  await page.getByRole("button", { name: "Speed" }).click();
  await expect(page.getByRole("heading", { name: "Pattern A" })).toBeVisible();
  await expect(page.getByRole("link", { name: "synthetic-pattern-a", exact: true })).toBeVisible();

  await page.getByRole("link", { name: "synthetic-pattern-a", exact: true }).click();
  await expect(page).toHaveURL(/\/experiments\/synthetic-pattern-a$/);
  await expect(page.getByRole("heading", { name: "synthetic-pattern-a" })).toBeVisible();

  await page.getByRole("link", { name: "Compare" }).click();
  await expect(page.getByRole("heading", { name: "Compare runs" })).toBeVisible();
  await expect(page).toHaveURL(/\/compare/);

  await page.getByRole("link", { name: "Pareto / SLO" }).click();
  await expect(page.getByLabel("Quality and latency plot")).toBeVisible();
  await expect(page.locator(".plot-point")).not.toHaveCount(0);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow, `${testInfo.project.name} layout has horizontal overflow`).toBe(false);
});

test("overview has no serious accessibility violations", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Choose the right retrieval path." })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""));
  expect(serious).toEqual([]);
});