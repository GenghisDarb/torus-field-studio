import { chromium } from "@playwright/test";
import path from "node:path";
import process from "node:process";

const [url = "http://127.0.0.1:4173", output = "results/tld-i/exports/tld-i-browser.png"] = process.argv.slice(2);
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  await page.goto(url, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /Load TLD I result/ }).click();
  await page.locator(".source-pill").filter({ hasText: "PUBLISHED SOURCE · AUDIT PASSED" }).waitFor({ timeout: 30_000 });
  await page.screenshot({ path: path.resolve(output), fullPage: true });
  console.log(path.resolve(output));
} finally {
  await browser.close();
}
