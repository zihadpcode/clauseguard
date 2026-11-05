const { chromium } = require('playwright');
const fs = require('fs');

// Usage: node record_narrated.js <repo_root> <out_dir> <durations.json> <narration.json>
const [ROOT, OUT_DIR, DUR_PATH, NAR_PATH] = process.argv.slice(2);
const DUR = JSON.parse(fs.readFileSync(DUR_PATH, 'utf-8'));
const NAR = Object.fromEntries(JSON.parse(fs.readFileSync(NAR_PATH, 'utf-8')));
const GAP = 550;

const CARD_CSS = `
  html,body{margin:0;height:100%;background:#0f1115;overflow:hidden;font-family:"Archivo","Helvetica Neue",Arial,sans-serif;color:#fff}
  .wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px}
  .glow{position:absolute;width:900px;height:900px;border-radius:50%;background:radial-gradient(circle,rgba(234,88,12,.28),rgba(234,88,12,0) 65%);animation:pulse 6s ease-in-out infinite}
  @keyframes pulse{0%,100%{transform:scale(.9);opacity:.7}50%{transform:scale(1.08);opacity:1}}
  .stripe{position:absolute;left:0;right:0;height:26px;background:repeating-linear-gradient(-45deg,#f97316 0 22px,#111 22px 44px);background-size:62px 26px;animation:slide 2.4s linear infinite}
  .top{top:0}.bot{bottom:0}
  @keyframes slide{from{background-position:0 0}to{background-position:62px 0}}
  .tag{font:600 15px/1 "IBM Plex Mono",monospace;letter-spacing:.32em;color:#fb923c;opacity:0;animation:up .9s .2s cubic-bezier(.2,.8,.2,1) forwards}
  h1{margin:0;font-size:104px;font-weight:800;letter-spacing:-.02em;opacity:0;animation:up 1.1s .45s cubic-bezier(.2,.8,.2,1) forwards}
  h1 span{color:#f97316}
  p{margin:0;font-size:27px;color:#cbd5e1;max-width:900px;text-align:center;line-height:1.4;opacity:0;animation:up 1.1s .9s cubic-bezier(.2,.8,.2,1) forwards}
  .chips{display:flex;gap:14px;opacity:0;animation:up 1s 1.4s cubic-bezier(.2,.8,.2,1) forwards}
  .chip{font:500 16px/1 "IBM Plex Mono",monospace;padding:10px 16px;border:1px solid #334155;border-radius:8px;color:#e2e8f0;background:#151a22}
  @keyframes up{from{opacity:0;transform:translateY(26px);filter:blur(6px)}to{opacity:1;transform:none;filter:none}}
  .fade{position:absolute;inset:0;background:#0f1115;animation:fin .8s ease forwards;pointer-events:none}
  @keyframes fin{from{opacity:1}to{opacity:0}}
`;

const introHTML = `<!doctype html><html><head><style>${CARD_CSS}</style></head><body>
<div class="stripe top"></div><div class="stripe bot"></div>
<div class="wrap"><div class="glow"></div>
<div class="tag">META GLOBAL AI DEVELOPER HACKATHON</div>
<h1>Clause<span>Guard</span></h1>
<p>Precheck a personal fall arrest plan against six OSHA requirements, before anyone climbs.</p>
<div class="chips"><div class="chip">29 CFR 1926.502</div><div class="chip">29 CFR 1926.503</div><div class="chip">Muse Spark</div></div>
</div><div class="fade"></div></body></html>`;

const outroHTML = `<!doctype html><html><head><style>${CARD_CSS}</style></head><body>
<div class="stripe top"></div><div class="stripe bot"></div>
<div class="wrap"><div class="glow"></div>
<div class="tag">FINDS QUESTIONS. DOES NOT CERTIFY COMPLIANCE.</div>
<h1>Clause<span>Guard</span></h1>
<p>github.com/zihadpcode/clauseguard</p>
<div class="chips"><div class="chip">Built by Zihad Patwary</div><div class="chip">Build for Your World</div></div>
</div><div class="fade"></div></body></html>`;

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 1,
    recordVideo: { dir: OUT_DIR, size: { width: 1280, height: 800 } },
  });
  const page = await context.newPage();
  const t0 = Date.now();
  const marks = [];
  const wait = (ms) => page.waitForTimeout(ms);

  const overlay = async () => {
    await page.evaluate(() => {
      if (document.getElementById('cg-cursor')) return;
      const st = document.createElement('style');
      st.textContent = `
        #cg-cursor{position:fixed;left:0;top:0;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;
          background:rgba(249,115,22,.95);box-shadow:0 0 0 6px rgba(249,115,22,.25),0 4px 14px rgba(0,0,0,.35);
          z-index:2147483647;pointer-events:none;transition:transform .85s cubic-bezier(.22,.9,.24,1);transform:translate(640px,420px)}
        .cg-ripple{position:fixed;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;border:3px solid #f97316;
          z-index:2147483646;pointer-events:none;animation:cgr .7s ease-out forwards}
        @keyframes cgr{from{opacity:1;transform:scale(1)}to{opacity:0;transform:scale(3.2)}}
        #cg-cap{position:fixed;left:50%;bottom:30px;transform:translate(-50%,14px);max-width:1080px;padding:14px 24px;
          background:rgba(15,17,21,.88);backdrop-filter:blur(8px);color:#fff;font:500 20px/1.45 system-ui,"Helvetica Neue",sans-serif;
          border-radius:12px;border:1px solid rgba(255,255,255,.08);z-index:2147483645;pointer-events:none;text-align:center;
          box-shadow:0 10px 30px rgba(0,0,0,.35);opacity:0;transition:opacity .45s ease,transform .45s cubic-bezier(.2,.8,.2,1)}
        #cg-cap.on{opacity:1;transform:translate(-50%,0)}
        .cg-spot{outline:3px solid #f97316 !important;outline-offset:6px;border-radius:10px;transition:outline-color .4s ease;
          box-shadow:0 0 0 9999px rgba(15,17,21,.0)}
      `;
      document.head.appendChild(st);
      const c = document.createElement('div'); c.id = 'cg-cursor'; document.body.appendChild(c);
      const cap = document.createElement('div'); cap.id = 'cg-cap'; document.body.appendChild(cap);
    });
  };

  const say = async (name, caption) => {
    marks.push({ name, t: (Date.now() - t0) / 1000 });
    const text = caption === undefined ? NAR[name] : caption;
    if (text) {
      await page.evaluate(async (t) => {
        const cap = document.getElementById('cg-cap');
        if (!cap) return;
        cap.classList.remove('on');
        await new Promise((r) => setTimeout(r, 250));
        cap.textContent = t;
        cap.classList.add('on');
      }, text);
    }
    return Date.now() + DUR[name] * 1000;
  };
  const until = async (deadline, extra = GAP) => {
    const ms = deadline - Date.now() + extra;
    if (ms > 0) await wait(ms);
  };
  const hideCap = () => page.evaluate(() => document.getElementById('cg-cap')?.classList.remove('on'));

  const moveTo = async (locator) => {
    await locator.scrollIntoViewIfNeeded();
    const b = await locator.boundingBox();
    const x = b.x + b.width / 2, y = b.y + b.height / 2;
    await page.evaluate(([x, y]) => {
      document.getElementById('cg-cursor').style.transform = `translate(${x}px,${y}px)`;
    }, [x, y]);
    await wait(900);
    return [x, y];
  };
  const clickFx = async (locator) => {
    const [x, y] = await moveTo(locator);
    await page.evaluate(([x, y]) => {
      const r = document.createElement('div'); r.className = 'cg-ripple';
      r.style.left = x + 'px'; r.style.top = y + 'px'; document.body.appendChild(r);
      setTimeout(() => r.remove(), 800);
    }, [x, y]);
    await locator.click();
  };

  const main = '[data-testid="stMain"]';
  const smoothScrollTo = async (text, offset = 110) => {
    const el = page.locator(main).getByText(text, { exact: false }).first();
    await el.evaluate((node, o) => {
      const m = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
      m.scrollBy({ top: node.getBoundingClientRect().top - o, behavior: 'smooth' });
    }, offset);
    await wait(1100);
    return el;
  };
  const scrollTop = async () => {
    await page.evaluate(() => {
      const m = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
      m.scrollTo({ top: 0, behavior: 'smooth' });
    });
    await wait(1000);
  };
  // Outline the result card that contains a given check id.
  const spot = async (text, on = true) => {
    await page.evaluate(([t, on]) => {
      document.querySelectorAll('.cg-spot').forEach((n) => n.classList.remove('cg-spot'));
      if (!on) return;
      const root = document.querySelector('[data-testid="stMain"]');
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let n; while ((n = walker.nextNode())) { if (n.nodeValue.includes(t)) break; }
      if (!n) return;
      let el = n.parentElement;
      // climb to the nearest ancestor that looks like a card (has a border radius and real height)
      for (let i = 0; i < 8 && el; i++) {
        const cs = getComputedStyle(el);
        if (el.getBoundingClientRect().height > 140 && parseFloat(cs.borderTopLeftRadius) >= 6) break;
        el = el.parentElement;
      }
      if (el) el.classList.add('cg-spot');
    }, [text, on]);
  };

  // ---- Intro card
  await page.setContent(introHTML);
  let d = await say('intro', null);
  await until(d, 400);

  // ---- App
  await page.goto('http://localhost:8501', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Yes, conventional PFAS' }).waitFor();
  await overlay();
  d = await say('user');
  await until(d);

  d = await say('gate');
  await wait(2500);
  await clickFx(page.getByRole('button', { name: 'Yes, conventional PFAS' }));
  await page.locator('textarea').waitFor();
  await overlay();
  await until(d);

  d = await say('paste');
  const planA = fs.readFileSync(`${ROOT}/data/plan_a.txt`, 'utf-8').trim();
  const ta = page.locator('textarea');
  await moveTo(ta);
  await ta.fill(planA);
  await page.locator(main).getByText('Extraction preview').click();
  await wait(600);
  await smoothScrollTo('Extraction preview', 160);
  await until(d);

  d = await say('analyze');
  await wait(1200);
  await clickFx(page.getByRole('button', { name: 'Analyze plan' }));
  await page.locator(main).getByText('PFAS_INSPECT_01').first().waitFor();
  await overlay();
  await wait(1500);
  await smoothScrollTo('Review is not clean', 100);
  await until(d);

  d = await say('conflict');
  await smoothScrollTo('PFAS_INSPECT_01', 90);
  await spot('PFAS_INSPECT_01');
  await until(d);
  await spot('', false);

  d = await say('fix');
  await scrollTop();
  const oldS = 'inspected monthly by the site safety coordinator, and damaged equipment will be tagged out.';
  const newS = 'inspected prior to each use for wear, damage, and deterioration, and defective components will be removed from service.';
  const idx = planA.indexOf(oldS);
  await moveTo(ta);
  await ta.evaluate((el, [s, e]) => { el.focus(); el.setSelectionRange(s, e); }, [idx, idx + oldS.length]);
  await page.keyboard.type(newS, { delay: 22 });
  await until(d);

  d = await say('rerun');
  await clickFx(page.getByRole('button', { name: 'Analyze plan' }));
  await page.locator(main).getByText('PFAS_INSPECT_01').first().waitFor();
  await overlay();
  await until(d, 900);

  d = await say('flip');
  await smoothScrollTo('PFAS_INSPECT_01', 90);
  await spot('PFAS_INSPECT_01');
  await until(d);
  await spot('', false);

  d = await say('impact');
  await smoothScrollTo('PFAS_IMPACT_01', 90);
  await spot('PFAS_IMPACT_01');
  await until(d);
  await spot('', false);

  d = await say('cert');
  await smoothScrollTo('PFAS_CERT_01', 90);
  await spot('PFAS_CERT_01');
  await until(d);
  await spot('', false);

  d = await say('banner');
  await scrollTop();
  await smoothScrollTo('Review is not clean', 90);
  await until(d);

  d = await say('json');
  const exp = page.locator(main).getByText('Raw model response (JSON)').first();
  await exp.evaluate((node) => {
    const m = document.querySelector('[data-testid="stMain"]');
    m.scrollBy({ top: node.getBoundingClientRect().top - 260, behavior: 'smooth' });
  });
  await wait(1100);
  await clickFx(exp);
  await wait(800);
  await until(d);

  d = await say('limits');
  await scrollTop();
  await until(d);

  // ---- Outro card
  await hideCap();
  await wait(400);
  await page.setContent(outroHTML);
  d = await say('outro', null);
  await until(d, 1800);

  const end = (Date.now() - t0) / 1000;
  await context.close();
  await browser.close();
  fs.writeFileSync(`${OUT_DIR}/marks.json`, JSON.stringify({ marks, end }, null, 1));
  console.log(JSON.stringify({ marks, end }));
})();
