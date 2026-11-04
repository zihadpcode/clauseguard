// End-to-end check of the built hosted page (web/dist/clauseguard.html) in
// headless Chromium. Usage: node tests/web/e2e.mjs [screenshot_dir]
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { readFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const PAGE = "file://" + path.join(ROOT, "web/dist/clauseguard.html");
const SHOTS = process.argv[2];
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const planA = readFileSync(path.join(ROOT, "data/plan_a.txt"), "utf8").trim();

const browser = await chromium.launch();
const results = [];
async function step(name, fn) {
  try { await fn(); results.push(`ok   ${name}`); }
  catch (e) { results.push(`FAIL ${name}: ${e.message.split("\n")[0]}`); }
}

const page = await browser.newPage({ viewport: { width: 1360, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error" && !/fonts\.(googleapis|gstatic)/.test(m.text())) errors.push(m.text()); });
await page.goto(PAGE);
const shot = (n) => SHOTS && page.screenshot({ path: `${SHOTS}/${n}.png` });

await step("scenario gate shows question and a real example card", async () => {
  await page.getByText("Does this plan use conventional personal fall arrest?").waitFor();
  assert.equal(await page.locator(".card").count(), 1);
  await shot("w1_gate");
});
await step("'No' stops with not supported, and Back returns", async () => {
  await page.getByRole("button", { name: "No, a different system" }).click();
  await page.getByText("This scenario is not supported").waitFor();
  assert.equal(await page.locator("#plan").count(), 0);
  await page.getByRole("button", { name: "Back to scenario question" }).click();
});
await step("'Yes' reaches plan step; empty input is INCOMPLETE and Analyze disabled", async () => {
  await page.getByRole("button", { name: "Yes, conventional PFAS" }).click();
  await page.locator("#preview").getByText("INCOMPLETE").waitFor();
  assert.ok(await page.locator("#analyze").isDisabled());
});
await step(".txt upload fills text, preview shows lines/chars/source/hash", async () => {
  await page.locator("#file").setInputFiles(path.join(ROOT, "data/plan_a.txt"));
  await page.locator("#preview").getByText("upload: plan_a.txt").waitFor();
  const prev = await page.locator("#preview").innerText();
  assert.match(prev, /9\s*lines/);
  assert.match(prev, /634\s*characters/);
  assert.match(prev, /sha256 1bd6d6593a752444/);
  assert.equal(await page.locator("#plan").inputValue(), planA);
  await shot("w2_plan");
});
await step(".pdf upload is refused with a clear message", async () => {
  await page.locator("#file").setInputFiles({ name: "plan.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4") });
  await page.getByText("PDF text extraction runs in the Streamlit app").waitFor();
});
await step("Analyze Plan A: not-clean banner, conflict on INSPECT, 6 cards, 4 highlights", async () => {
  await page.locator("#analyze").click();
  await page.getByText("Review is not clean").waitFor();
  assert.equal(await page.locator("#results .card").count(), 6);
  const inspect = page.locator('#results .card[data-check="PFAS_INSPECT_01"]');
  assert.match(await inspect.locator(".tag").innerText(), /potential conflict/i);
  assert.match(await inspect.innerText(), /inspected monthly/);
  assert.match(await inspect.innerText(), /prior to each use/);
  assert.equal(await page.locator(".planview mark").count(), 4);
  assert.match(await page.locator(".stamp").innerText(), /STUBBED/);
  const impact = await page.locator('#results .card[data-check="PFAS_IMPACT_01"]').innerText();
  assert.match(impact, /Not located in the supplied text \(9 lines, 634 characters\)\./);
  assert.doesNotMatch(impact.toLowerCase(), /missing|noncompliant/);
  for (const card of await page.locator("#results .card").all()) {
    assert.match(await card.innerText(), /Not legal advice/);
  }
  await page.locator('#results .card[data-check="PFAS_INSPECT_01"]').scrollIntoViewIfNeeded();
  await shot("w3_results");
});
await step("one keystroke clears results and shows the stale note", async () => {
  await page.locator("#plan").focus();
  await page.keyboard.press("End");
  await page.keyboard.type(" ");
  assert.equal(await page.locator("#results .card").count(), 0);
  await page.getByText("previous results were cleared").waitFor();
});
await step("fixing the inspection sentence flips INSPECT to evidence found", async () => {
  const fixed = planA.replace(
    "inspected monthly by the site safety coordinator, and damaged equipment will be tagged out.",
    "inspected prior to each use for wear, damage, and deterioration, and defective components will be removed from service.",
  );
  await page.locator("#plan").fill(fixed);
  await page.locator("#analyze").click();
  const inspect = page.locator('#results .card[data-check="PFAS_INSPECT_01"]');
  await inspect.waitFor();
  assert.match(await inspect.locator(".tag").innerText(), /evidence found/i);
  assert.match(await page.locator(".banner").innerText(), /1 not located, 1 needs information/);
});
await step("unrecognized text is refused in stub mode, never analyzed", async () => {
  await page.locator("#plan").fill("All workers will wear harnesses. Inspection happens whenever it is convenient for the crew.");
  await page.locator("#analyze").click();
  await page.getByText("does not invent an analysis").waitFor();
  assert.equal(await page.locator("#results .card").count(), 0);
});
await step("no page errors", async () => assert.deepEqual(errors, []));

for (const scheme of ["dark"]) {
  await step(`${scheme} theme renders with dark ground`, async () => {
    const p = await browser.newPage({ viewport: { width: 1360, height: 900 }, colorScheme: scheme });
    await p.goto(PAGE);
    await p.getByRole("button", { name: "Yes, conventional PFAS" }).click();
    await p.getByRole("button", { name: "Load Plan A (as submitted)" }).click();
    await p.locator("#analyze").click();
    await p.getByText("Review is not clean").waitFor();
    const bg = await p.evaluate(() => getComputedStyle(document.body).backgroundColor);
    assert.equal(bg, "rgb(13, 18, 23)");
    if (SHOTS) await p.screenshot({ path: `${SHOTS}/w4_dark.png` });
    await p.close();
  });
}
await step("phone width: no horizontal scroll", async () => {
  const p = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await p.goto(PAGE);
  await p.getByRole("button", { name: "Yes, conventional PFAS" }).click();
  await p.getByRole("button", { name: "Load Plan A (as submitted)" }).click();
  await p.locator("#analyze").click();
  await p.getByText("Review is not clean").waitFor();
  const over = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assert.equal(over, 0);
  if (SHOTS) {
    await p.locator('#results .card[data-check="PFAS_INSPECT_01"]').scrollIntoViewIfNeeded();
    await p.screenshot({ path: `${SHOTS}/w5_phone.png` });
  }
  await p.close();
});

await browser.close();
console.log(results.join("\n"));
process.exit(results.some((r) => r.startsWith("FAIL")) ? 1 : 0);
