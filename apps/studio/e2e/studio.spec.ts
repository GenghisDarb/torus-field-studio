import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import path from "node:path";

const fixtures = path.resolve(import.meta.dirname, "../../../tests/generated-fixtures");

async function waitForField(page: Page) {
  await expect(page.locator(".busy-overlay")).toHaveCount(0, { timeout: 20_000 });
  await expect(page.locator("canvas.field-canvas")).toBeVisible();
}

test("field interaction, analytic claim, surface recovery, and screenshot", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  await page.goto("/");
  await waitForField(page);

  const inspector = page.locator(".right-panel .panel-heading code");
  const originalPoint = await inspector.textContent();
  await page.locator("canvas.field-canvas").click({ position: { x: 18, y: 18 } });
  await expect(inspector).not.toHaveText(originalPoint ?? "");

  await page.getByRole("button", { name: /ANALYTIC/ }).click();
  await waitForField(page);
  await expect(page.getByText("ILLUSTRATIVE_ANALYTIC", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /Surface/ }).click();
  const surfaceCanvas = page.locator(".surface-host canvas");
  await expect(surfaceCanvas).toBeVisible({ timeout: 20_000 });
  await surfaceCanvas.evaluate((canvas) => canvas.dispatchEvent(new Event("webglcontextlost", { cancelable: true })));
  await expect(page.locator(".surface-context-notice")).toContainText("WebGL context lost");
  await surfaceCanvas.evaluate((canvas) => canvas.dispatchEvent(new Event("webglcontextrestored")));
  await expect(page.locator(".surface-context-notice")).toHaveCount(0);

  await page.getByRole("button", { name: /Field/ }).click();
  await expect(page).toHaveScreenshot(`studio-field-${process.platform}.png`, { fullPage: true });
  expect(consoleErrors).toEqual([]);
});

test("strict TBX import accepts canonical bundles and rejects hostile members", async ({ page }) => {
  await page.goto("/");
  await waitForField(page);
  const input = page.locator('input[type="file"]');
  await input.setInputFiles(path.join(fixtures, "valid-reference.tbx.zip"));
  await expect(page.locator(".source-pill")).toHaveText("TBX AUDIT PASSED", { timeout: 20_000 });

  await input.setInputFiles(path.join(fixtures, "path-traversal.tbx.zip"));
  await expect(page.getByRole("alert")).toContainText("ARCHIVE_PATH_INVALID");
  await input.setInputFiles(path.join(fixtures, "forged-verifier.tbx.zip"));
  await expect(page.getByRole("alert")).toContainText("VERIFIER_RECEIPT_MISSING");
  await input.setInputFiles(path.join(fixtures, "nonfinite-metric.tbx.zip"));
  await expect(page.getByRole("alert")).toContainText("JSON_NONFINITE");
  await input.setInputFiles({ name: "raw-table.json", mimeType: "application/json", buffer: Buffer.from("{}") });
  await expect(page.getByRole("alert")).toContainText("ARCHIVE_INVALID");
});

test("browser export can be re-imported through the strict auditor", async ({ page }) => {
  await page.goto("/");
  await waitForField(page);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /Export .tbx/ }).click();
  const download = await downloadPromise;
  const output = path.join(fixtures, "browser-export.tbx.zip");
  await download.saveAs(output);
  const payload = await readFile(output);
  await page.locator('input[type="file"]').setInputFiles({ name: "browser-export.tbx.zip", mimeType: "application/zip", buffer: payload });
  await expect(page.locator(".source-pill")).toHaveText("TBX AUDIT PASSED", { timeout: 20_000 });
});

test("published TLD I result exposes audited evidence without claim escalation", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  await page.goto("/");
  await waitForField(page);
  await page.getByRole("button", { name: /Load TLD I result/ }).click();
  await expect(page.locator(".source-pill")).toHaveText("PUBLISHED SOURCE · AUDIT PASSED", { timeout: 30_000 });
  await expect(page.getByTestId("tld-source-panel")).toContainText("10.5281/zenodo.18080090");
  await expect(page.getByTestId("tld-source-panel")).toContainText("4 pass · 2 fail");
  await expect(page.getByText("COMPUTED_DYNAMICAL", { exact: true })).toBeVisible();
  await expect(page.getByText("TLD_DERIVED is blocked", { exact: false })).toBeVisible();
  await expect(page.getByTestId("tld-raw-point")).toBeVisible();
  await expect(page.getByTestId("tld-evidence-summary")).toContainText("winner-state transitions");
  await page.getByRole("button", { name: /Surface/ }).click();
  await expect(page.locator(".surface-host canvas")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: /Field/ }).click();
  await page.getByRole("button", { name: /Audit/ }).click();
  await expect(page.getByText("Source DOI and published input hashes verified")).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

test("held-out Beijing PM2.5 TBX exposes the frozen negative result", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.goto("/");
  await waitForField(page);
  await page.getByRole("button", { name: "Load v0.2.2 forensic audit" }).click();
  await expect(page.locator(".source-pill")).toHaveText("HELD-OUT SOURCE · AUDIT PASSED", {
    timeout: 30_000,
  });
  const source = page.getByTestId("heldout-source-panel");
  await expect(source).toBeVisible({ timeout: 30_000 });
  await expect(source).toContainText("10.24432/C5RK5G");
  await expect(source).toContainText("NOT_OBSERVED");
  await expect(source).toContainText("winner_N");
  await expect(source).toContainText("9 · separate closure mode");
  await expect(source).toContainText("FAILED");
  await expect(source).toContainText("25/25 mutations");
  await expect(source).toContainText("BLOCKED");
  await expect(source).toContainText("post-hoc", { ignoreCase: true });
  await expect(page.getByText("COMPUTED_DYNAMICAL", { exact: true })).toBeVisible();
  const evidence = page.getByTestId("heldout-evidence-summary");
  await expect(evidence).toContainText("Tₑ NOT_OBSERVED");
  await expect(evidence).toContainText("Sₑ 0.000");
  await expect(evidence).toContainText("14 specificity: FAIL");
  await expect(evidence).toContainText("external validation: NO");
  await page.getByRole("button", { name: "Surface" }).click();
  await expect(page.locator("canvas").first()).toBeVisible();
  await page.getByRole("button", { name: "Field" }).click();
  await expect(page.getByText("Interpolated pixels are never counted as observations.")).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

test("mobile layout and serious accessibility checks", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await waitForField(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await expect(page.getByRole("button", { name: /Import bundle/ })).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  const severe = accessibility.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious");
  expect(severe).toEqual([]);
});
