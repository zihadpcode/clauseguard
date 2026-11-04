# ClauseGuard

**A precheck for personal fall arrest system (PFAS) plans.** A subcontractor's safety coordinator pastes a fall protection plan. ClauseGuard runs six review questions drawn from 29 CFR 1926.502 and 1926.503, and returns one of four statuses for each question. Each result quotes the plan sentence it relied on and shows the governing regulation beside it. The coordinator fixes the plan, reruns, and watches the status change.

> Every result is labeled **source matched; interpretation requires review.** This is not legal advice, not a compliance determination, and not a substitute for a qualified safety professional. No accuracy figure is claimed, and no safety professional has reviewed the output.

Built for the Meta Global AI Developer Hackathon (Startup track, *Build for Your World*) on `muse-spark-1.3` through the Meta Model API.

![The conflict: plan says monthly, regulation says prior to each use](docs/conflict.png)

**Demo video:** [`docs/demo.mp4`](docs/demo.mp4) (77 s, on-screen captions, no voiceover)

---

## Status of this build

| | |
|---|---|
| App, validator, tests, demo | Working. 23 tests pass. |
| Live Meta Model API call | **Implemented but never executed.** No API key was available when this was built. The app runs in **stub mode** by default (see below). Set `MODEL_API_KEY` to use the real model. |
| Regulatory text | Typed from knowledge of the regulation. Not fetched live, because eCFR was blocked from the build sandbox. **Check each entry against eCFR before relying on it.** |

Full disclosure is in [EVAL.md](EVAL.md).

## Why

Fall protection has been OSHA's most cited standard for fifteen consecutive fiscal years. Templated plan sections fail review in three different ways, and each needs a different response:

- **Explicit conflict.** The plan is weaker than the rule: for example, inspection "monthly" instead of "prior to each use."
- **Not located.** The text does not address the topic. That describes the text, not proof the employer doesn't do it.
- **Needs information.** The plan points to a record that wasn't supplied, such as "records are kept by HR."

A tool that collapses all three into "missing requirement" produces confident, wrong conclusions. ClauseGuard keeps them separate and **never renders an incomplete review as a clean one.**

## How it works

```
Scenario confirmed (conventional PFAS only)  --no-->  "not supported", stop
        |
Plan text  --> extraction preview (lines, chars) --< 40 chars--> INCOMPLETE, stop
        |
ONE call to muse-spark-1.3   (strict json_schema; json_object fallback)
  returns per check: check_id, status, plan_span, interpretation, evidence_request
  never returns regulatory text
        |
Local validation (deterministic, no model)
  - exactly 6 results, the 6 expected IDs, no duplicates
  - status in the 4 allowed values
  - conflict/evidence: plan_span >= 20 chars AND found in the plan (after normalization)
  - needs_info/not_located: evidence_request present
  - interpretation present
        |
Cards: regulation from pinned checks.json | quoted plan sentence | status | interpretation
Banner: REVIEW INCOMPLETE (red) / not clean, with open items listed (amber) / clean (green)
Stamp: plan sha256, index version, model ID, schema mode, timestamp
```

**Division of labor.** The **model** reads the plan prose and picks a status for each check. The **application** renders the regulation from a pinned index (the model never types regulation), confirms that every quoted sentence really occurs in the plan, and confirms that all six checks came back exactly once.

**Accounting is not correctness.** The validator proves the response is complete and that every quote is real. It does not prove the interpretation is right: a real sentence can be quoted for the wrong conclusion and still pass. A test demonstrates this (`test_real_but_irrelevant_span_passes_validation`).

### The six checks

| ID | Question | Source |
|---|---|---|
| `PFAS_RESCUE_01` | Prompt rescue, or self-rescue assured? | § 1926.502(d)(20) |
| `PFAS_INSPECT_01` | Inspected prior to each use; defective components removed? | § 1926.502(d)(21) |
| `PFAS_IMPACT_01` | Impact-loaded components removed until a competent person clears them? | § 1926.502(d)(19) |
| `PFAS_FREEFALL_01` | 6 ft free fall and 3.5 ft deceleration limits stated? | § 1926.502(d)(16)(iii)–(iv) |
| `PFAS_TRAIN_01` | Training program for employees exposed to fall hazards? | § 1926.503(a)(1) |
| `PFAS_CERT_01` | Written training certification record addressed? | § 1926.503(b)(1) |

These are excluded on purpose: guardrails, covers, nets, roofing alternatives, and the § 1926.502(k) fall protection plan.

### The four statuses

| Status | Meaning | Required (enforced locally) |
|---|---|---|
| `potential_conflict` | Plan is weaker than, or contradicts, the requirement | Real `plan_span` of at least 20 characters |
| `evidence_found` | Plan appears to address the requirement | Real `plan_span` of at least 20 characters |
| `needs_information` | Plan refers to a record or fact that wasn't supplied | `evidence_request` |
| `not_located` | Nothing in the supplied text addresses it | `evidence_request`; rendered as "Not located in the supplied text (N lines, M characters)" and never as "missing" |

## Run it

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

Confirm the scenario, click **Load Plan A**, then **Analyze**. Edit the inspection sentence, or click **Load Plan B**, and run **Analyze** again.

### Live model vs stub mode

| `MODEL_API_KEY` | Behavior |
|---|---|
| set | Live call to `muse-spark-1.3` at `https://api.meta.ai/v1` via the OpenAI Python SDK. `MODEL_BASE_URL` and `MODEL_ID` can point at a partner-hosted Meta model; disclose it if you do. |
| unset | **Stub mode.** Returns hand-written recorded JSON for Plans A and B only. Refuses any other text instead of inventing an analysis. The result stamp reads `STUBBED -- recorded JSON, not a live call`. |

Export the variables listed in `.env.example` (the app reads the environment; it does not load `.env` files). The validator treats stub and live responses the same way.

### Tests

```bash
python -m pytest tests/ -v
```

The suite runs 23 tests: the validator rules, app behavior driven headlessly through Streamlit's `AppTest`, and the live client against a local fake OpenAI-compatible server. Case-by-case results are in [EVAL.md](EVAL.md).

### Live evaluation (needs a key)

```bash
MODEL_API_KEY=... python scripts/run_model_eval.py
```

This runs Plan A, Plan B and the prompt-injection plan three times each. It prints a per-check stability table for EVAL.md and logs every raw response to `logs/eval_runs.jsonl`.

## Repo layout

```
app.py                         Streamlit UI (scenario gate, input, cards, banner, clear-on-edit)
clauseguard/model_client.py    prompt, JSON schema, live call + fallbacks, stub mode
clauseguard/validator.py       the six deterministic validation rules
clauseguard/normalize.py       span-matching normalization (NFKC, quotes, whitespace, case)
data/checks.json               pinned regulatory index (text, CFR cite, URL, date, sha256)
data/plan_a.txt, plan_b.txt    demo plans (development examples, not validation data)
data/plan_injection.txt        boundary case for 7.3
data/stub_responses.json       recorded JSON for stub mode (hand-written; see EVAL.md)
scripts/build_checks_index.py  regenerates checks.json and its hashes
scripts/run_model_eval.py      live 7.2/7.3 evaluation
scripts/record_demo.js         Playwright script that recorded docs/demo.mp4
logs/runs.jsonl                raw JSON log from the recorded demo session
docs/PROPOSAL.md               the original design proposal
```

## Limits

- Six checks and one scenario. Nothing else in Subpart M, no other subparts, no other jurisdictions.
- No expert review and no accuracy claim. Plans A and B are development examples, not validation data.
- A plausible but wrong interpretation can pass validation. That is why every card says *interpretation requires review*.
- Prompt-injection resistance is untested against the live model. The structural limits (fixed IDs, pinned regulation, quotes checked against the plan) hold regardless of the model.
- Plain text only. There is no PDF extraction, persistence, authentication or export.
