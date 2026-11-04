const { chromium } = require('playwright');
const fs = require('fs');

// Usage: node scripts/record_demo.js <out_dir>  (app must be running on :8501)
const OUT_DIR = process.argv[2];
const ROOT = require('path').resolve(__dirname, '..');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    recordVideo: { dir: OUT_DIR, size: { width: 1280, height: 800 } },
  });
  const page = await context.newPage();
  const wait = (ms) => page.waitForTimeout(ms);

  const caption = async (text) => {
    await page.evaluate((t) => {
      let el = document.getElementById('cg-caption');
      if (!el) {
        el = document.createElement('div');
        el.id = 'cg-caption';
        Object.assign(el.style, {
          position: 'fixed', left: '50%', bottom: '24px', transform: 'translateX(-50%)',
          maxWidth: '1100px', padding: '14px 22px', background: 'rgba(17,24,39,0.92)',
          color: '#fff', font: '500 19px/1.4 system-ui, sans-serif', borderRadius: '10px',
          zIndex: 999999, pointerEvents: 'none', textAlign: 'center', boxShadow: '0 6px 24px rgba(0,0,0,0.3)',
        });
        document.body.appendChild(el);
      }
      el.textContent = t;
    }, text);
  };

  // Streamlit scrolls inside its own container, not the window.
  const scrollToText = async (text, offset = 120) => {
    const el = page.locator('[data-testid="stMain"]').getByText(text, { exact: false }).first();
    await el.evaluate((node, o) => {
      const main = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
      main.scrollBy({ top: node.getBoundingClientRect().top - o, behavior: 'smooth' });
    }, offset);
    await page.waitForTimeout(700);
  };

  await page.goto('http://localhost:8501', { waitUntil: 'networkidle' });
  await wait(1500);
  await caption("Fall protection has been OSHA's most cited standard fifteen years running. This is a subcontractor's fall arrest plan, checked against six requirements.");
  await wait(5000);

  await caption('Step 1: confirm the scenario. Anything other than conventional personal fall arrest stops here.');
  await page.getByText('Yes', { exact: true }).click();
  await wait(1500);
  await page.getByRole('button', { name: 'Confirm and continue' }).click();
  await wait(2000);

  await caption('Paste Plan A, as submitted. The extraction preview shows line and character counts.');
  const planA = fs.readFileSync(`${ROOT}/data/plan_a.txt`, 'utf-8').trim();
  const ta = page.locator('textarea');
  await ta.fill(planA);
  await page.locator('[data-testid="stMain"]').getByText('Extraction preview').click();
  await wait(3000);

  await caption('Analyze: one structured call returns one result per check. The app then validates every result locally.');
  await page.getByRole('button', { name: 'Analyze' }).click();
  await wait(3500);

  await scrollToText('PFAS_INSPECT_01');
  await caption('The conflict: the plan says "monthly". The regulation, rendered from a pinned eCFR copy and never from the model, says "prior to each use".');
  await wait(7000);

  await page.evaluate(() => {
    const main = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
    main.scrollTo(0, 0);
  });
  await wait(800);
  await caption('The fix: edit the inspection sentence. The old results clear on the first keystroke.');
  const oldS = 'inspected monthly by the site safety coordinator, and damaged equipment will be tagged out.';
  const newS = 'inspected prior to each use for wear, damage, and deterioration, and defective components will be removed from service.';
  const idx = planA.indexOf(oldS);
  await ta.evaluate((el, [s, e]) => { el.focus(); el.setSelectionRange(s, e); }, [idx, idx + oldS.length]);
  await page.keyboard.type(newS, { delay: 18 });
  await wait(2000);

  await caption('Rerun.');
  await page.getByRole('button', { name: 'Analyze' }).click();
  await wait(3000);

  await scrollToText('PFAS_INSPECT_01');
  await caption('PFAS_INSPECT_01 flips to evidence found, quoting the corrected sentence.');
  await wait(5000);

  await scrollToText('PFAS_IMPACT_01');
  await caption('Still open: impact loading is "not located in the supplied text" -- a statement about this text, never "missing" or "noncompliant".');
  await wait(6500);

  await scrollToText('PFAS_CERT_01');
  await caption('Certification needs information: the plan points to an HR record that was not supplied, so the tool asks for it instead of assuming it exists.');
  await wait(6500);

  await page.evaluate(() => {
    const main = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
    main.scrollTo(0, 0);
  });
  await wait(600);
  await scrollToText('Stamp:', 90);
  await caption('The banner says why this review is not clean. Why trust it: every quote is checked against the plan, every check is accounted for, and every result is stamped with plan hash, index version and model.');
  await wait(6500);

  await caption('Limits: six checks, one scenario, no expert review. In this recording the model call is STUBBED with recorded JSON (no Meta Model API key was available) -- see the stamp and EVAL.md.');
  await wait(7500);

  await context.close();
  await browser.close();
  console.log('done');
})();
