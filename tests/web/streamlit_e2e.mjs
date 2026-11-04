// Browser check of the Streamlit app's client-side behavior that AppTest
// cannot see (the clear-on-keystroke script). Needs the app running:
//   streamlit run app.py --server.port 8501 --server.headless true
//   node tests/web/streamlit_e2e.mjs [http://localhost:8501]
import { createRequire } from "node:module";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const URL = process.argv[2] || "http://localhost:8501";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1360, height: 900 } });
const results = [];
async function step(name, fn) {
  try { await fn(); results.push(`ok   ${name}`); }
  catch (e) { results.push(`FAIL ${name}: ${e.message.split("\n")[0]}`); }
}
const visible = (sel) => page.evaluate((s) => {
  const el = document.querySelector(s);
  return !!el && getComputedStyle(el).display !== "none" && el.getBoundingClientRect().height > 0;
}, sel);

await page.goto(URL, { waitUntil: "networkidle" });
await step("scenario -> plan -> analyze Plan A shows results", async () => {
  await page.getByRole("button", { name: "Yes, conventional PFAS" }).click();
  await page.getByRole("button", { name: "Load Plan A (as submitted)" }).click();
  await page.getByRole("button", { name: "Analyze plan" }).click();
  await page.getByText("Review is not clean").waitFor();
  assert.ok(await visible(".st-key-results"));
  assert.ok(!(await visible("#cg-stale")));
});
await step("first keystroke hides results and shows the stale note (before commit)", async () => {
  await page.locator("textarea").focus();
  await page.keyboard.press("Control+End");
  await page.keyboard.type(" x");
  await page.waitForTimeout(300);
  assert.ok(!(await visible(".st-key-results")));
  assert.ok(await visible("#cg-stale"));
});
await step("Analyze straight from the textarea reruns, and the stale note is gone", async () => {
  await page.getByRole("button", { name: "Load Plan B (corrected)" }).click();
  await page.waitForTimeout(800);
  await page.getByRole("button", { name: "Analyze plan" }).click();
  await page.locator(".cg-stamp").getByText("c2127e193697d998").waitFor();
  await page.waitForTimeout(800);
  assert.ok(await visible(".st-key-results"));
  assert.ok(!(await visible("#cg-stale")), "stale note still visible next to fresh results");
});
await step("edit then click Analyze without blurring: click is not swallowed", async () => {
  await page.locator("textarea").focus();
  await page.keyboard.press("Control+End");
  await page.keyboard.type(" y");
  await page.getByRole("button", { name: "Analyze plan" }).click();
  await page.getByText("does not fabricate an analysis").first().waitFor();
});

await browser.close();
console.log(results.join("\n"));
process.exit(results.some((r) => r.startsWith("FAIL")) ? 1 : 0);
