"""ClauseGuard Streamlit app: scenario gate -> plan text -> review.
Decision logic lives in clauseguard/: model_client (what the model is
asked), validator (what the app checks on its own), ui (escaped HTML)."""
import datetime as dt
import json
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from clauseguard import highlight, ingest, model_client, ui, validator

DISCLAIMER = (
    "Not legal advice, not a compliance determination, not a substitute "
    "for a qualified safety professional."
)
MIN_PLAN_CHARS = 40
INDEX_VERSION = "checks.json v1"
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOG_PATH = Path(os.environ.get("CLAUSEGUARD_LOG_PATH", ROOT / "logs" / "runs.jsonl"))
OPEN_STATUS_LABELS = {
    "potential_conflict": "potential conflict",
    "not_located": "not located",
    "needs_information": "needs information",
}

# st.text_area only commits on blur/Ctrl+Enter, so server-side clearing alone
# would leave stale results visible while the user types. This hides them on
# the first keystroke; the server clears them for real on commit.
_CLEAR_ON_KEYSTROKE_JS = """
<script>
const doc = window.parent.document;
const w = window.parent;
const hide = () => {
  doc.querySelectorAll('.st-key-results').forEach(e => e.style.display = 'none');
  const note = doc.getElementById('cg-stale');
  if (note) note.style.display = '';
};
doc.querySelectorAll('.st-key-results').forEach(e => e.style.display = '');
// React reuses the note's DOM node across reruns, so undo a previous show.
const staleNote = doc.getElementById('cg-stale');
if (staleNote && staleNote.dataset.startHidden === '1') staleNote.style.display = 'none';
const ta = doc.querySelector('.st-key-plan_text_area textarea');
if (ta) {
  if (w.__cgTa && w.__cgHide) w.__cgTa.removeEventListener('input', w.__cgHide);
  w.__cgTa = ta;
  w.__cgHide = hide;
  ta.addEventListener('input', hide);
}
</script>
<!-- %s -->
"""

st.set_page_config(page_title="ClauseGuard", page_icon="\U0001F6E1", layout="wide")


def _init_state():
    defaults = {
        "scenario_confirmed": None,  # None | True | False
        "plan_text": "",
        "plan_text_area": "",
        "text_source": "pasted",
        "last_upload_id": None,
        "upload_error": None,
        "last_analyzed_hash": None,
        "model_result": None,
        "validation_result": None,
        "analyzed_at": None,
        "analyzed_text": "",
        "analyzed_line_count": 0,
        "analyzed_char_count": 0,
        "results_were_cleared": False,
        "analysis_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _clear_results():
    if st.session_state.model_result is not None:
        st.session_state.results_were_cleared = True
    st.session_state.last_analyzed_hash = None
    st.session_state.model_result = None
    st.session_state.validation_result = None
    st.session_state.analyzed_at = None
    st.session_state.analysis_error = None


def _set_plan_text(text: str, source: str):
    st.session_state.plan_text = text
    st.session_state.plan_text_area = text
    st.session_state.text_source = source
    _clear_results()


def _load_demo(filename: str, source: str):
    _set_plan_text((DATA_DIR / filename).read_text(encoding="utf-8").strip(), source)


def _html(markup: str):
    st.html(markup)


def _render_chrome(step: int):
    _html(ui.CSS)
    live = bool(os.environ.get("MODEL_API_KEY"))
    _html(ui.brand_bar(live, os.environ.get("MODEL_ID", model_client.MODEL_ID)))
    _html(ui.stepper(step))


def _render_scenario_gate():
    _render_chrome(1)
    _html(ui.scenario_panel())
    if st.session_state.scenario_confirmed is False:
        _html(ui.unsupported_panel())
        if st.button("Back to scenario question"):
            st.session_state.scenario_confirmed = None
            st.rerun()
    else:
        c1, c2, _ = st.columns([1.3, 1.3, 2])
        with c1:
            if st.button("Yes, conventional PFAS", type="primary", width="stretch"):
                st.session_state.scenario_confirmed = True
                st.rerun()
        with c2:
            if st.button("No, a different system", width="stretch"):
                st.session_state.scenario_confirmed = False
                st.rerun()
    _html(ui.footer(DISCLAIMER))


def _apply_upload():
    upload = st.session_state.get("upload")
    if upload is None or upload.file_id == st.session_state.last_upload_id:
        return
    st.session_state.last_upload_id = upload.file_id
    try:
        extracted = ingest.extract(upload.name, upload.getvalue())
    except ingest.IngestError as e:
        st.session_state.upload_error = str(e)
        return
    st.session_state.upload_error = None
    _set_plan_text(extracted.text.strip(), extracted.source)


def _render_plan_step(checks):
    _apply_upload()
    # Widget state is already updated at the start of the run. Clear in place
    # rather than st.rerun(): a rerun would discard an Analyze click that
    # arrived in the same run as the committed edit.
    if st.session_state.plan_text_area != st.session_state.plan_text:
        st.session_state.plan_text = st.session_state.plan_text_area
        st.session_state.text_source = "pasted / edited"
        _clear_results()

    _render_chrome(3 if st.session_state.model_result is not None else 2)

    left, right = st.columns([3, 2], gap="medium")
    with left:
        plan_text = st.text_area(
            "Fall protection plan text",
            height=300,
            key="plan_text_area",
            placeholder="Paste the PFAS section of the site-specific safety plan here.",
        )

        st.file_uploader(
            "Or upload a .txt file or a digitally generated .pdf",
            type=["txt", "pdf"],
            key="upload",
        )
        if st.session_state.upload_error:
            st.error(st.session_state.upload_error)

        st.caption("Development examples (not validation data):")
        d1, d2 = st.columns(2)
        with d1:
            st.button("Load Plan A (as submitted)", width="stretch", on_click=_load_demo, args=("plan_a.txt", "demo: Plan A"))
        with d2:
            st.button("Load Plan B (corrected)", width="stretch", on_click=_load_demo, args=("plan_b.txt", "demo: Plan B"))

    stripped = plan_text.strip()
    chars = len(stripped)
    lines = len(stripped.splitlines()) if stripped else 0
    ready = chars >= MIN_PLAN_CHARS
    with right:
        _html(ui.preview_panel(
            lines, chars, st.session_state.text_source,
            model_client.hash_plan(stripped) if stripped else None, ready, MIN_PLAN_CHARS,
        ))
        analyze = st.button("Analyze plan", type="primary", disabled=not ready, width="stretch")
        if st.button("Change scenario", width="stretch"):
            st.session_state.scenario_confirmed = None
            st.rerun()

    if analyze:
        _run_analysis(stripped, checks)

    if st.session_state.analysis_error:
        _html(ui.banner("incomplete", "REVIEW INCOMPLETE", st.session_state.analysis_error))

    if st.session_state.model_result is not None:
        _html(ui.stale_note(hidden=True))
        with st.container(key="results"):
            _render_results(checks)
    elif st.session_state.results_were_cleared:
        _html(ui.stale_note(hidden=False))

    components.html(
        _CLEAR_ON_KEYSTROKE_JS % (st.session_state.last_analyzed_hash or "none"),
        height=0,
    )
    _html(ui.footer(DISCLAIMER))


def _run_analysis(plan_text: str, checks):
    st.session_state.results_were_cleared = False
    st.session_state.analysis_error = None
    with st.spinner("Running the six checks..."):
        try:
            result = model_client.call_model(plan_text, checks)
        except model_client.ModelUnavailableError as e:
            st.session_state.analysis_error = str(e)
            return
        except json.JSONDecodeError:
            st.session_state.analysis_error = "The model response did not parse as JSON."
            return
        except Exception as e:  # live API failure surfaces, never silently retried
            st.session_state.analysis_error = f"Model call failed: {e}"
            return

    expected_ids = {c["check_id"] for c in checks}
    try:
        v = validator.validate(result.raw_response, plan_text, expected_ids)
    except Exception as e:
        st.session_state.analysis_error = f"Response could not be validated: {e}"
        return

    st.session_state.model_result = result
    st.session_state.validation_result = v
    st.session_state.last_analyzed_hash = model_client.hash_plan(plan_text)
    st.session_state.analyzed_at = dt.datetime.now(dt.timezone.utc)
    st.session_state.analyzed_text = plan_text
    st.session_state.analyzed_line_count = len(plan_text.splitlines())
    st.session_state.analyzed_char_count = len(plan_text)
    _log_run(plan_text, result, v)


def _log_run(plan_text, result, v):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": st.session_state.analyzed_at.isoformat(),
        "plan_sha256": st.session_state.last_analyzed_hash,
        "index_version": INDEX_VERSION,
        "model_id": result.model_id,
        "mode": result.mode,
        "schema_mode": result.schema_mode,
        "all_valid": v.all_valid,
        "global_errors": v.global_errors,
        "card_errors": {c.check_id: c.errors for c in v.cards if c.errors},
        "raw_response": result.raw_response,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _summary_banner(v, checks) -> str:
    known = {c["check_id"] for c in checks}
    if not v.all_valid:
        items = [f"Accounting: {e}" for e in v.global_errors]
        items += [f"{c.check_id}: {e}" for c in v.cards if c.check_id not in known for e in c.errors]
        bad_cards = sum(1 for c in v.cards if c.check_id in known and not c.valid)
        if bad_cards:
            items.append(f"{bad_cards} card(s) failed validation; see the red cards below.")
        return ui.banner(
            "incomplete", "REVIEW INCOMPLETE",
            "The response did not pass local validation. Rerun before relying on any result.", items,
        )
    accounting = f"{v.valid_count} of {len(checks)} checks returned with valid evidence fields."
    open_items = [
        f"{n} {label}"
        for status, label in OPEN_STATUS_LABELS.items()
        if (n := sum(1 for c in v.cards if c.status == status))
    ]
    if open_items:
        return ui.banner(
            "open", "Review is not clean",
            f"{accounting} Open items: {', '.join(open_items)}. They are on the cards below.",
        )
    return ui.banner(
        "clean", accounting,
        "Every check shows plan evidence. Interpretation still requires review by a qualified person.",
    )


def _render_results(checks):
    result = st.session_state.model_result
    v = st.session_state.validation_result
    known = {c["check_id"]: c for c in checks}
    cards_by_id = {}
    for c in v.cards:
        if c.check_id in known:
            cards_by_id.setdefault(c.check_id, c)
            if not c.valid:
                cards_by_id[c.check_id] = c

    _html(_summary_banner(v, checks))
    counts = {}
    for c in cards_by_id.values():
        counts[c.status] = counts.get(c.status, 0) + 1
    _html(ui.tally(counts))
    _html(ui.stamp(
        st.session_state.last_analyzed_hash, INDEX_VERSION, result.model_id, result.schema_mode,
        st.session_state.analyzed_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
    ))

    cards_col, plan_col = st.columns([3, 2], gap="medium")
    with cards_col:
        for check in checks:
            _html(ui.check_card(
                check, cards_by_id.get(check["check_id"]),
                st.session_state.analyzed_line_count, st.session_state.analyzed_char_count,
            ))
    with plan_col, st.container(key="planview"):
        spans = [
            (c.check_id, c.status, c.plan_span)
            for c in cards_by_id.values()
            if c.valid and c.plan_span and c.status in ("potential_conflict", "evidence_found")
        ]
        _html(ui.plan_view(highlight.highlight_html(st.session_state.analyzed_text, spans)))
        with st.expander("Raw model response (JSON)"):
            st.json(result.raw_response)


def main():
    _init_state()
    checks = model_client.load_checks()
    if not st.session_state.scenario_confirmed:
        _render_scenario_gate()
        return
    _render_plan_step(checks)


main()
