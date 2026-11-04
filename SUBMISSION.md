# Submission checklist

This answers the proposal's "Fill in before submitting" list. Items marked **YOU** need the submitter's action or their own words.

- [x] **Model ID and endpoint actually used, and whether strict schema or the `json_object` fallback ran.**
  The code targets `muse-spark-1.3` at `https://api.meta.ai/v1` (OpenAI Python SDK, key in `MODEL_API_KEY`), with strict `json_schema` first and `json_object` as the fallback. **No live call was made during the build**, because no API key was available. The app and the demo video ran in **stub mode** (recorded JSON), and the result stamp says so. Neither schema path has been confirmed against the real API.
  **YOU:** if you run `scripts/run_model_eval.py` with your key before submitting, replace this with the observed model ID and schema mode, and paste the printed tables into EVAL.md section 7.2.
- [ ] **Demo video and repo URLs.**
  The video file is `docs/demo.mp4` in the repo (77 s, captioned, no voiceover). **YOU:** upload it (YouTube unlisted or Loom), check that the link opens in a private window, and paste both URLs into the submission form.
- [x] **Final six check IDs as read against eCFR, with retrieval date.**
  `PFAS_RESCUE_01` (d)(20), `PFAS_INSPECT_01` (d)(21), `PFAS_IMPACT_01` (d)(19), `PFAS_FREEFALL_01` (d)(16)(iii)–(iv), `PFAS_TRAIN_01` 1926.503(a)(1), `PFAS_CERT_01` 1926.503(b)(1). Indexed 2026-11-04. **Caveat:** the text was **not** read against live eCFR, because eCFR was blocked from the build sandbox. **YOU:** open the two eCFR URLs in `data/checks.json` and compare by eye. If they match, set `verified_against_live_ecfr_by_human` to `true` in `scripts/build_checks_index.py` and rerun it. If they don't, fix the text and rerun.
- [x] **Deterministic test outcomes, case by case.** EVAL.md section 7.1: 23 of 23 pass.
- [ ] **Model example outcomes and three-run stability log, case by case.** EVAL.md section 7.2 is marked **not run (stubbed)**. **YOU:** run `scripts/run_model_eval.py` with a key to fill it in, or submit it as is. As is, it is an honest pipeline demonstration with the model call stubbed, which the proposal's API fallback rule allows.
- [x] **Statement that no safety professional reviewed the output.** In the README, EVAL.md and the app's disclaimers.
- [x] **Statement that Plans A and B are development examples, not validation.** In the README.
- [ ] **One sentence connecting this to "Build for Your World", in your own words.** **YOU:** the proposal asks for your words, so this is left blank.
- [x] **If PDF was added: plain text remained the guaranteed path.** PDF was not added (first item in the cut order).
- [x] **If a partner-hosted Meta model or a stub was used: disclosed.** A stub was used. It is disclosed in the README, EVAL.md, the app's result stamp, the stub file itself, and the last caption of the demo video.

## Suggested submission text

> **ClauseGuard** prechecks a subcontractor's personal fall arrest plan against six requirements from 29 CFR 1926.502/503 before it goes to the general contractor. The model reads the plan and assigns each check one of four statuses: potential conflict, evidence found, needs information, or not located. It must quote the exact plan sentence it relied on. The application never lets the model write regulation. It renders the regulation from a pinned, hashed index, checks that every quoted sentence really occurs in the plan, checks that all six checks came back exactly once, and refuses to show a review as clean while anything is unresolved. The coordinator fixes the plan, reruns, and watches *monthly → prior to each use* flip from conflict to evidence. Built on Muse Spark 1.3 via the Meta Model API. In this submission the model call is stubbed with recorded JSON (see EVAL.md), so it is a pipeline demonstration. There is no accuracy claim and no expert review.
