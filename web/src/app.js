// ClauseGuard hosted page: scenario gate -> plan text -> review. Stub mode:
// validates and renders the recorded responses for the two development plans.
(function () {
  "use strict";
  const { validate, pyStrip, pyLen } = window.CGValidator;
  const { highlightHtml, esc } = window.CGHighlight;
  const DATA = JSON.parse(document.getElementById("cg-data").textContent);
  const CHECKS = DATA.checks;
  const IDS = CHECKS.map((c) => c.check_id);
  const MIN_PLAN_CHARS = 40;
  const MAX_UPLOAD = 5 * 1024 * 1024;
  const MODEL_LABEL = "muse-spark-1.3 (STUBBED -- recorded JSON, not a live call)";
  const DISCLAIMER = "Not legal advice, not a compliance determination, not a substitute for a qualified safety professional.";
  const CARD_DISCLAIMER = "Not legal advice or a compliance determination.";
  const STATUS = {
    potential_conflict: "Potential conflict",
    evidence_found: "Evidence found",
    needs_information: "Needs information",
    not_located: "Not located",
  };
  const OPEN = { potential_conflict: "potential conflict", not_located: "not located", needs_information: "needs information" };

  const S = { step: "scenario", text: "", source: "pasted", hash: null, run: null, stale: false, error: null, uploadError: null };
  const $ = (sel) => document.querySelector(sel);
  const view = $("#view");

  const lineCount = (s) => (s ? s.split(/\r\n|[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]/).length : 0);

  async function sha256(text) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  // ---------- chrome ----------
  function renderSteps() {
    const cur = S.step === "plan" ? (S.run ? 3 : 2) : 1;
    $("#steps").innerHTML = ["Confirm scenario", "Plan text", "Review"]
      .map((label, i) => {
        const n = i + 1;
        const cls = n === cur ? "on" : n < cur ? "done" : "";
        return `<li class="${cls}" ${n === cur ? 'aria-current="step"' : ""}><b>${n < cur ? "&#10003;" : n}</b>${label}</li>`;
      })
      .join("");
  }

  // ---------- step 1 ----------
  function exampleCard() {
    const check = CHECKS.find((c) => c.check_id === "PFAS_INSPECT_01");
    const card = DATA.stubs[DATA.plans.a_hash].response.results.find((r) => r.check_id === "PFAS_INSPECT_01");
    return `<div class="panel"><p class="eyebrow">What a review looks like &middot; Plan A, development example</p>
      ${cardHtml(check, { ...card, errors: [] }, 0, 0)}</div>`;
  }

  function renderScenario() {
    const excluded = ["Guardrails", "Safety nets", "Covers", "Roofing alternatives", "\u00a7 1926.502(k) fall protection plan"];
    const unsupported = S.step === "unsupported";
    view.innerHTML = `<div class="gate">
      <section class="panel" aria-labelledby="gate-h">
        <p class="eyebrow">Step 1 &middot; Applicability</p>
        <h2 id="gate-h" style="font-size:1.35rem">Does this plan use conventional personal fall arrest?</h2>
        <p class="lede">ClauseGuard supports one scenario: work protected by a <b>conventional personal fall arrest system</b>
          (body harness, connector, anchorage) on a construction site. All six checks apply by construction. Anything else
          stops here instead of producing a review that doesn't fit.</p>
        <p class="eyebrow" style="margin-top:16px">Not supported</p>
        <div class="chips">${excluded.map((x) => `<span class="chip">${esc(x)}</span>`).join("")}</div>
        ${unsupported ? `<div class="banner banner--incomplete" style="margin-top:18px" role="alert"><div class="ico">!</div><div>
            <h2>This scenario is not supported</h2><p>ClauseGuard has no applicability logic for guardrails, nets, covers,
            roofing alternatives, or a \u00a7 1926.502(k) plan, so it stops rather than guessing.</p></div></div>
            <div class="actions"><button class="btn" id="back">Back to scenario question</button></div>`
          : `<div class="actions"><button class="btn btn--primary" id="yes">Yes, conventional PFAS</button>
            <button class="btn" id="no">No, a different system</button></div>`}
      </section>
      ${exampleCard()}
    </div>`;
    if (unsupported) $("#back").onclick = () => go("scenario");
    else {
      $("#yes").onclick = () => go("plan");
      $("#no").onclick = () => go("unsupported");
    }
  }

  // ---------- step 2 ----------
  function renderPlan() {
    view.innerHTML = `<div class="work">
      <section>
        <label class="field" for="plan">Fall protection plan text</label>
        <textarea id="plan" spellcheck="false" placeholder="Paste the PFAS section of the site-specific safety plan here."></textarea>
        <div class="drop"><label for="file">Or upload a .txt file</label><input id="file" type="file" accept=".txt,.pdf,text/plain,application/pdf"></div>
        <div id="upload-err"></div>
        <div class="demo"><p>Development examples (not validation data):</p>
          <div class="row"><button class="btn" id="demo-a">Load Plan A (as submitted)</button>
          <button class="btn" id="demo-b">Load Plan B (corrected)</button></div></div>
      </section>
      <aside class="side">
        <div class="panel" id="preview"></div>
        <button class="btn btn--primary btn--block" id="analyze">Analyze plan</button>
        <button class="btn btn--block" id="change">Change scenario</button>
        <p class="note">This hosted page runs in <b>stub mode</b>: it validates and renders recorded responses for the two
          development plans only, and refuses any other text. Live analysis with muse-spark-1.3 runs in the Streamlit app
          when a Meta Model API key is configured.</p>
      </aside>
    </div><div id="results"></div>`;

    const ta = $("#plan");
    ta.value = S.text;
    ta.addEventListener("input", () => {
      S.source = "pasted / edited";
      setText(ta.value, null, false);
    });
    $("#file").addEventListener("change", onUpload);
    $("#demo-a").onclick = () => loadDemo("a", "demo: Plan A");
    $("#demo-b").onclick = () => loadDemo("b", "demo: Plan B");
    $("#analyze").onclick = analyze;
    $("#change").onclick = () => go("scenario");
    renderPreview();
    renderResults();
  }

  function setText(text, source, syncTextarea = true) {
    S.text = text;
    if (source) S.source = source;
    if (S.run) {
      S.run = null;
      S.stale = true;
      renderSteps();
    }
    S.error = null;
    if (syncTextarea && $("#plan")) $("#plan").value = text;
    renderPreview();
    renderResults();
  }

  function loadDemo(which, source) {
    S.uploadError = null;
    setText(DATA.plans[which], source);
    $("#upload-err").innerHTML = "";
  }

  function onUpload(e) {
    const file = e.target.files[0];
    const errBox = $("#upload-err");
    errBox.innerHTML = "";
    if (!file) return;
    const fail = (msg) => (errBox.innerHTML = `<div class="err" role="alert">${esc(msg)}</div>`);
    const name = file.name.toLowerCase();
    if (file.size > MAX_UPLOAD) return fail(`${file.name} is larger than 5 MB.`);
    if (name.endsWith(".pdf")) {
      return fail("PDF text extraction runs in the Streamlit app. On this page, paste the text or upload a .txt file.");
    }
    if (!name.endsWith(".txt")) return fail("Only .txt files can be uploaded here.");
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result).replace(/^\ufeff/, "").trim(), `upload: ${file.name}`);
    reader.onerror = () => fail(`${file.name} could not be read.`);
    reader.readAsText(file);
  }

  async function renderPreview() {
    const stripped = pyStrip(S.text);
    const chars = pyLen(stripped);
    const ready = chars >= MIN_PLAN_CHARS;
    const hash = stripped ? await sha256(stripped) : null;
    if (pyStrip(S.text) !== stripped) return; // a newer keystroke owns the preview
    S.hash = hash;
    const box = $("#preview");
    if (!box) return;
    box.innerHTML = `<p class="eyebrow">Extraction preview</p>
      <div class="stats"><div class="stat"><b>${lineCount(stripped)}</b><span>lines</span></div>
      <div class="stat"><b>${chars.toLocaleString("en-US")}</b><span>characters</span></div></div>
      <div class="kv"><div><b>source</b> ${esc(S.source)}</div>${hash ? `<div><b>sha256</b> ${hash.slice(0, 16)}&hellip;</div>` : ""}</div>
      ${ready ? '<div class="state state--ok">Ready to analyze</div>'
        : `<div class="state state--bad">INCOMPLETE &middot; paste at least ${MIN_PLAN_CHARS} characters</div>`}`;
    $("#analyze").disabled = !ready;
  }

  // ---------- analysis ----------
  async function analyze() {
    const plan = pyStrip(S.text);
    if (pyLen(plan) < MIN_PLAN_CHARS) return;
    S.stale = false;
    S.error = null;
    const hash = await sha256(plan);
    const stub = DATA.stubs[hash];
    if (!stub) {
      S.run = null;
      S.error = "This hosted page runs in stub mode, which only has recorded responses for the two development plans " +
        "(Plan A and Plan B). It does not invent an analysis for text it has not seen. Load a development plan, or run " +
        "the Streamlit app with MODEL_API_KEY set to analyze any plan text with the real model.";
    } else {
      const v = validate(stub.response, plan, IDS);
      S.run = { plan, hash, raw: stub.response, v, at: new Date(), lines: lineCount(plan), chars: pyLen(plan) };
    }
    renderSteps();
    renderResults();
    const target = $("#results");
    if (target && S.run) target.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  // ---------- results ----------
  function regBox(check) {
    return `<div class="box box--reg"><p class="eyebrow">Regulation &middot; <span class="cite">${esc(check.cfr_paragraph)}</span></p>
      <p class="q">${esc(check.verbatim_text)}</p>
      <div class="src">pinned index &middot; <a href="${esc(check.ecfr_url)}" target="_blank" rel="noopener">eCFR</a> &middot;
      <span class="nw">retrieved ${esc(check.retrieval_date)}</span> &middot; sha256 ${esc(check.sha256.slice(0, 12))}&hellip;</div></div>`;
  }

  function cardHtml(check, card, lines, chars) {
    if (!card) {
      return `<article class="card card--invalid" data-check="${esc(check.check_id)}">
        <div class="card-head"><span class="cid">${esc(check.check_id)}</span><span class="tag tag--invalid">No result</span></div>
        <h3>${esc(check.question)}</h3><div class="pair">${regBox(check)}
        <div class="box box--not_located">The model returned no result for this check, so it is unreviewed.</div></div>
        <div class="card-foot card-foot--bad"><span>REVIEW INCOMPLETE &middot; rerun the analysis</span><span>${CARD_DISCLAIMER}</span></div></article>`;
    }
    const valid = card.errors.length === 0;
    const known = card.status in STATUS;
    const tagCls = valid && known ? card.status : "invalid";
    const label = known ? STATUS[card.status] : "Invalid status";
    let plan;
    if ((card.status === "potential_conflict" || card.status === "evidence_found") && card.plan_span) {
      plan = `<div class="box box--${card.status}"><p class="eyebrow">Plan says</p><p class="q">${esc(card.plan_span)}</p></div>`;
    } else if (card.status === "not_located") {
      plan = `<div class="box box--not_located"><p class="eyebrow">Plan</p>
        <p><b>Not located in the supplied text (${lines} lines, ${chars.toLocaleString("en-US")} characters).</b></p>
        <p style="margin-top:8px"><b>What to add:</b> ${esc(card.evidence_request)}</p></div>`;
    } else if (card.status === "needs_information") {
      plan = `<div class="box box--needs_information"><p class="eyebrow">Needs information</p><p>${esc(card.evidence_request)}</p></div>`;
    } else {
      plan = `<div class="box box--not_located"><p class="eyebrow">Plan</p><p>Returned status: <code>${esc(card.status)}</code></p></div>`;
    }
    const fails = card.errors.map((e) => `<div class="fail">Validation failure: ${esc(e)}</div>`).join("");
    const foot = valid
      ? `<div class="card-foot"><span>Source matched; interpretation requires review.</span><span>${CARD_DISCLAIMER}</span></div>`
      : `<div class="card-foot card-foot--bad"><span>Validation failed &middot; do not rely on this card</span><span>${CARD_DISCLAIMER}</span></div>`;
    return `<article class="card ${valid ? "" : "card--invalid"}" data-check="${esc(check.check_id)}">
      <div class="card-head"><span class="cid">${esc(check.check_id)}</span><span class="tag tag--${tagCls}">${esc(label)}</span></div>
      <h3>${esc(check.question)}</h3><div class="pair">${regBox(check)}${plan}</div>
      <p class="interp"><b>Model interpretation.</b> ${esc(card.interpretation)}</p>${fails}${foot}</article>`;
  }

  function bannerHtml(kind, title, body, items = []) {
    const ico = { incomplete: "!", open: "&bull;", clean: "&#10003;" }[kind];
    const list = items.length ? `<ul>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : "";
    return `<div class="banner banner--${kind}" role="status"><div class="ico">${ico}</div><div><h2>${esc(title)}</h2><p>${esc(body)}</p>${list}</div></div>`;
  }

  function summaryBanner(v) {
    if (!v.all_valid) {
      const items = v.global_errors.map((e) => `Accounting: ${e}`);
      for (const c of v.cards) if (!IDS.includes(c.check_id)) for (const e of c.errors) items.push(`${c.check_id}: ${e}`);
      const bad = v.cards.filter((c) => IDS.includes(c.check_id) && c.errors.length).length;
      if (bad) items.push(`${bad} card(s) failed validation; see the flagged cards below.`);
      return bannerHtml("incomplete", "REVIEW INCOMPLETE", "The response did not pass local validation. Rerun before relying on any result.", items);
    }
    const accounting = `${v.valid_count} of ${IDS.length} checks returned with valid evidence fields.`;
    const open = Object.entries(OPEN)
      .map(([status, label]) => [v.cards.filter((c) => c.status === status).length, label])
      .filter(([n]) => n)
      .map(([n, label]) => `${n} ${label}`);
    if (open.length) return bannerHtml("open", "Review is not clean", `${accounting} Open items: ${open.join(", ")}. They are on the cards below.`);
    return bannerHtml("clean", accounting, "Every check shows plan evidence. Interpretation still requires review by a qualified person.");
  }

  function renderResults() {
    const box = $("#results");
    if (!box) return;
    if (S.error) {
      box.innerHTML = `<div class="results">${bannerHtml("incomplete", "REVIEW INCOMPLETE", S.error)}</div>`;
      return;
    }
    if (!S.run) {
      box.innerHTML = S.stale
        ? '<div class="stale" role="status">Plan text changed, so the previous results were cleared. Run the analysis again.</div>'
        : "";
      return;
    }
    const { v, raw, plan, hash, at, lines, chars } = S.run;
    const byId = {};
    for (const c of v.cards) {
      if (!IDS.includes(c.check_id)) continue;
      if (!(c.check_id in byId) || c.errors.length) byId[c.check_id] = c;
    }
    const counts = {};
    for (const c of Object.values(byId)) counts[c.status] = (counts[c.status] || 0) + 1;
    const tallyColors = { potential_conflict: "danger", evidence_found: "safe", needs_information: "caution", not_located: "neutral" };
    const spans = Object.values(byId)
      .filter((c) => !c.errors.length && c.plan_span && (c.status === "potential_conflict" || c.status === "evidence_found"))
      .map((c) => [c.check_id, c.status, c.plan_span]);
    const ts = at.toISOString().replace("T", " ").slice(0, 19) + " UTC";

    box.innerHTML = `<div class="results">
      ${summaryBanner(v)}
      <div class="tally">${Object.entries(STATUS)
        .map(([s, label]) => `<div><b style="color:var(--${tallyColors[s] === "caution" ? "ink" : tallyColors[s]})">${counts[s] || 0}</b>
          <span class="tag tag--${s}">${label}</span></div>`).join("")}</div>
      <div class="stamp"><span><b>plan</b> sha256:${hash.slice(0, 16)}&hellip;</span><span><b>index</b> checks.json v1</span>
        <span><b>model</b> ${esc(MODEL_LABEL)}</span><span><b>schema</b> stub</span><span><b>at</b> ${ts}</span></div>
      <div class="split">
        <div class="cards">${CHECKS.map((c) => cardHtml(c, byId[c.check_id], lines, chars)).join("")}</div>
        <aside class="planview"><p class="eyebrow">Plan text &middot; quoted evidence</p>
          <pre>${highlightHtml(plan, spans)}</pre>
          <div class="legend"><span><i style="background:var(--hl-danger);box-shadow:inset 0 -2px 0 var(--danger)"></i>Potential conflict</span>
          <span><i style="background:var(--hl-safe);box-shadow:inset 0 -2px 0 var(--safe)"></i>Evidence found</span></div>
          <details class="raw"><summary>Raw model response (JSON)</summary><pre>${esc(JSON.stringify(raw, null, 2))}</pre></details>
        </aside>
      </div></div>`;
  }

  function go(step) {
    S.step = step;
    renderSteps();
    if (step === "plan") renderPlan();
    else renderScenario();
    window.scrollTo(0, 0);
  }

  $("#disclaimer").textContent = DISCLAIMER;
  go("scenario");
})();
