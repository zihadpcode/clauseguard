"""ClauseGuard: a precheck for one workflow -- conventional personal fall
arrest system (PFAS) plans, checked against six questions drawn from
29 CFR 1926.502 and 1926.503. See the proposal in the repo root for the
full design. This file is the Streamlit UI; the actual decision logic
lives in clauseguard/model_client.py (what the model is asked) and
clauseguard/validator.py (what the application checks on its own)."""
import datetime as dt
import json
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from clauseguard import model_client, validator

# st.text_area only commits on blur/Ctrl+Enter, so server-side clearing alone
# would leave stale results visible while the user types. This hides them on
# the first keystroke; the server clears them for real on commit.
_CLEAR_ON_KEYSTROKE_JS = """
<script>
const doc = window.parent.document;
const w = window.parent;
const hide = () => doc.querySelectorAll('.st-key-results').forEach(e => e.style.display = 'none');
doc.querySelectorAll('.st-key-results').forEach(e => e.style.display = '');
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

DISCLAIMER = (
    "Not legal advice, not a compliance determination, not a substitute "
    "for a qualified safety professional."
)
MIN_PLAN_CHARS = 40
OPEN_STATUS_LABELS = {
    "potential_conflict": "potential conflict",
    "not_located": "not located",
    "needs_information": "needs information",
}
INDEX_VERSION = "checks.json v1"
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOG_PATH = Path(os.environ.get("CLAUSEGUARD_LOG_PATH", ROOT / "logs" / "runs.jsonl"))

st.set_page_config(page_title="ClauseGuard", layout="wide")


def _init_state():
    defaults = {
        "scenario_confirmed": None,  # None | True | False
        "plan_text": "",
        "plan_text_area": "",
        "last_analyzed_hash": None,
        "model_result": None,
        "validation_result": None,
        "analyzed_at": None,
        "analyzed_line_count": 0,
        "analyzed_char_count": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _clear_results():
    st.session_state.last_analyzed_hash = None
    st.session_state.model_result = None
    st.session_state.validation_result = None
    st.session_state.analyzed_at = None


def _status_badge(status: str) -> str:
    return {
        "potential_conflict": "\U0001F534 Potential conflict",
        "evidence_found": "\U0001F7E2 Evidence found",
        "needs_information": "\U0001F7E1 Needs information",
        "not_located": "⚪ Not located",
    }.get(status, status)


def _render_scenario_gate():
    st.title("ClauseGuard")
    st.caption(
        "A precheck for one workflow: conventional personal fall arrest "
        "systems (PFAS) on a construction site."
    )
    st.subheader("Step 1: Confirm the scenario")
    st.write(
        "This tool supports exactly one scenario: the work described uses "
        "**conventional personal fall arrest systems (PFAS)** -- a body "
        "harness, lanyard, and anchorage. Guardrails, safety nets, covers, "
        "roofing alternatives, and the conditional § 1926.502(k) fall "
        "protection plan are not supported."
    )
    choice = st.radio(
        "Does the plan you are submitting use conventional PFAS?",
        options=["Not answered yet", "Yes", "No"],
        index=0,
    )
    if choice == "Yes":
        if st.button("Confirm and continue", type="primary"):
            st.session_state.scenario_confirmed = True
            st.rerun()
    elif choice == "No":
        st.error(
            "This scenario is not supported. ClauseGuard only reviews "
            "conventional PFAS plans against the six checks in this "
            "build -- it has no applicability logic for guardrails, nets, "
            "covers, roofing alternatives, or a § 1926.502(k) fall "
            "protection plan."
        )
    st.divider()
    st.caption(DISCLAIMER)


def _load_demo(path: Path):
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    st.session_state.plan_text = text
    st.session_state.plan_text_area = text
    _clear_results()


def _render_input_step(checks):
    st.title("ClauseGuard")
    st.caption(
        "Scenario confirmed: conventional PFAS. Reviewing against six "
        "checks drawn from § 1926.502 and § 1926.503."
    )

    col_a, col_b, col_c = st.columns([1, 1, 4])
    with col_a:
        if st.button("Load Plan A (as submitted)"):
            _load_demo(DATA_DIR / "plan_a.txt")
            st.rerun()
    with col_b:
        if st.button("Load Plan B (corrected)"):
            _load_demo(DATA_DIR / "plan_b.txt")
            st.rerun()
    with col_c:
        if st.button("Change scenario"):
            st.session_state.scenario_confirmed = None
            st.rerun()

    plan_text = st.text_area(
        "Paste the PFAS fall protection plan text",
        height=240,
        key="plan_text_area",
    )

    # Clear in place rather than st.rerun(): a rerun here would discard an
    # Analyze click that arrived in the same run as the committed edit.
    if plan_text != st.session_state.plan_text:
        st.session_state.plan_text = plan_text
        _clear_results()

    stripped = plan_text.strip()
    char_count = len(stripped)
    line_count = len(stripped.splitlines()) if stripped else 0
    st.caption(f"Extraction preview: {line_count} lines, {char_count} characters.")

    if char_count < MIN_PLAN_CHARS:
        st.warning(
            f"INCOMPLETE: paste at least {MIN_PLAN_CHARS} characters of plan "
            "text before analyzing."
        )
        analyze_disabled = True
    else:
        analyze_disabled = False

    analyze_clicked = st.button(
        "Analyze", type="primary", disabled=analyze_disabled
    )

    if analyze_clicked:
        _run_analysis(stripped, checks)

    if st.session_state.model_result is not None:
        with st.container(key="results"):
            _render_results(checks)

    components.html(
        _CLEAR_ON_KEYSTROKE_JS % (st.session_state.last_analyzed_hash or "none"),
        height=0,
    )

    st.divider()
    st.caption(DISCLAIMER)


def _run_analysis(plan_text: str, checks):
    with st.spinner("Running the six checks..."):
        try:
            result = model_client.call_model(plan_text, checks)
        except model_client.ModelUnavailableError as e:
            st.error(str(e))
            return
        except json.JSONDecodeError:
            st.error("REVIEW INCOMPLETE: the model response did not parse as JSON.")
            return
        except Exception as e:  # pragma: no cover - live API failure path
            st.error(f"Model call failed: {e}")
            return

    expected_ids = {c["check_id"] for c in checks}
    try:
        v = validator.validate(result.raw_response, plan_text, expected_ids)
    except Exception as e:  # malformed response that isn't even a dict
        st.error(f"Response could not be validated: {e}")
        return

    st.session_state.model_result = result
    st.session_state.validation_result = v
    st.session_state.last_analyzed_hash = model_client.hash_plan(plan_text)
    st.session_state.analyzed_at = dt.datetime.now(dt.timezone.utc)
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


def _render_results(checks):
    result = st.session_state.model_result
    v = st.session_state.validation_result
    checks_by_id = {c["check_id"]: c for c in checks}

    st.markdown(
        f"**Stamp:** plan hash `{st.session_state.last_analyzed_hash[:16]}...` "
        f"| index `{INDEX_VERSION}` | model `{result.model_id}` | "
        f"schema `{result.schema_mode}` | "
        f"{st.session_state.analyzed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    if v.all_valid:
        accounting = f"{v.valid_count} of {len(checks)} checks returned with valid evidence fields."
        open_items = [
            (n, label)
            for status, label in OPEN_STATUS_LABELS.items()
            if (n := sum(1 for c in v.cards if c.status == status))
        ]
        if open_items:
            summary = ", ".join(f"{n} {label}" for n, label in open_items)
            st.warning(f"{accounting} Review is not clean: {summary}. Open items are on the cards below.")
        else:
            st.success(
                f"{accounting} All six checks show plan evidence. "
                "Interpretation still requires review."
            )
    else:
        st.error("REVIEW INCOMPLETE")
        for err in v.global_errors:
            st.error(f"Accounting failure: {err}")

    cards_by_id = {c.check_id: c for c in v.cards if c.check_id in checks_by_id}

    for check in checks:
        card = cards_by_id.get(check["check_id"])
        with st.container(border=True):
            st.markdown(f"#### {check['check_id']} — {check['question']}")
            reg_col, plan_col = st.columns(2)
            with reg_col:
                st.markdown(f"**Regulation ({check['cfr_paragraph']}):**")
                st.markdown(f"> {check['verbatim_text']}")
                st.caption(
                    f"[Source]({check['ecfr_url']}) · retrieved "
                    f"{check['retrieval_date']} · sha256 "
                    f"{check['sha256'][:12]}..."
                )
            with plan_col:
                if card is None:
                    st.error(
                        "No result was returned for this check. "
                        "REVIEW INCOMPLETE."
                    )
                    continue
                st.markdown(f"**Status:** {_status_badge(card.status)}")
                if card.plan_span:
                    st.markdown("**Quoted from plan:**")
                    st.markdown(f"> {card.plan_span}")
                if card.status == "not_located":
                    n = st.session_state.analyzed_line_count
                    m = st.session_state.analyzed_char_count
                    st.markdown(f"*Not located in the supplied text ({n} lines, {m} characters).*")
                    if card.evidence_request:
                        st.markdown(f"**What to add:** {card.evidence_request}")
                elif card.status == "needs_information" and card.evidence_request:
                    st.markdown(f"**Needs information:** {card.evidence_request}")
                if card.interpretation:
                    st.markdown(f"**Interpretation:** {card.interpretation}")
                st.caption("Source matched; interpretation requires review.")

            if not card.valid:
                for err in card.errors:
                    st.error(f"Validation failure on this card: {err}")


def main():
    _init_state()
    checks = model_client.load_checks()

    if not st.session_state.scenario_confirmed:
        _render_scenario_gate()
        return

    _render_input_step(checks)


if __name__ == "__main__":
    main()
