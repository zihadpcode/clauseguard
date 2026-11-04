"""Deterministic tests (spec section 7.1). Each test feeds a hand built
response to the validator -- no model call."""
import pytest

from clauseguard.validator import validate

EXPECTED_IDS = {
    "PFAS_RESCUE_01",
    "PFAS_INSPECT_01",
    "PFAS_IMPACT_01",
    "PFAS_FREEFALL_01",
    "PFAS_TRAIN_01",
    "PFAS_CERT_01",
}

PLAN_TEXT = (
    "Harnesses and lanyards will be inspected monthly by the site's safety "
    "coordinator, and damaged equipment will be tagged out. Training "
    "certification records are maintained by the HR office."
)


def _result(**overrides):
    base = {
        "check_id": "PFAS_INSPECT_01",
        "status": "potential_conflict",
        "plan_span": "Harnesses and lanyards will be inspected monthly by the site's safety coordinator, and damaged equipment will be tagged out.",
        "interpretation": "The plan commits to monthly inspection, weaker than prior to each use.",
        "evidence_request": None,
    }
    base.update(overrides)
    return base


def _full_response(results):
    return {"results": results}


def _six_results_with(target_check_id="PFAS_INSPECT_01", **overrides):
    """Six syntactically valid results, with target_check_id's card replaced
    by overrides (its check_id stays fixed unless overrides sets it)."""
    results = []
    for check_id in sorted(EXPECTED_IDS):
        if check_id == target_check_id:
            replacement = dict(overrides)
            replacement.setdefault("check_id", check_id)
            results.append(_result(**replacement))
        else:
            results.append(
                {
                    "check_id": check_id,
                    "status": "not_located",
                    "plan_span": None,
                    "interpretation": "Not addressed in the supplied text.",
                    "evidence_request": "Add a sentence addressing this requirement.",
                }
            )
    return results


def test_unknown_check_id_fails():
    results = _six_results_with(check_id="PFAS_NOT_A_REAL_CHECK")
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    assert not v.all_valid


def test_duplicate_check_id_fails():
    results = _six_results_with()
    results[1] = dict(results[1])
    results[1]["check_id"] = results[0]["check_id"]
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    assert not v.all_valid


def test_five_results_instead_of_six_fails():
    results = _six_results_with()[:5]
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    assert not v.all_valid
    assert any("Expected 6 results" in e for e in v.global_errors)


def test_potential_conflict_with_null_span_fails_on_that_card():
    results = _six_results_with(plan_span=None)
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    inspect_card = next(c for c in v.cards if c.check_id == "PFAS_INSPECT_01")
    assert not inspect_card.valid
    other_cards = [c for c in v.cards if c.check_id != "PFAS_INSPECT_01"]
    assert all(c.valid for c in other_cards)


def test_evidence_found_with_span_not_in_plan_fails_on_that_card():
    results = _six_results_with(
        status="evidence_found",
        plan_span="This sentence does not appear anywhere in the plan text at all.",
    )
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    inspect_card = next(c for c in v.cards if c.check_id == "PFAS_INSPECT_01")
    assert not inspect_card.valid
    assert "fabricated" in inspect_card.errors[0]


def test_not_located_with_null_evidence_request_fails_on_that_card():
    results = _six_results_with(
        status="not_located", plan_span=None, evidence_request=None
    )
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    inspect_card = next(c for c in v.cards if c.check_id == "PFAS_INSPECT_01")
    assert not inspect_card.valid


def test_span_differing_by_line_break_and_curly_quote_passes():
    span_with_quirks = (
        "Harnesses and lanyards will be inspected\nmonthly by the site’s "
        "safety coordinator, and damaged equipment will be tagged out."
    )
    results = _six_results_with(plan_span=span_with_quirks)
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    inspect_card = next(c for c in v.cards if c.check_id == "PFAS_INSPECT_01")
    assert inspect_card.valid


def test_plan_text_edited_after_a_run_clears_results():
    """This behavior lives in the Streamlit app (session-state hash check),
    not the validator, so this test asserts the hashing contract the app
    relies on: a changed plan hashes differently, which is what the app
    uses to decide whether to clear stale results."""
    from clauseguard.model_client import hash_plan

    original = PLAN_TEXT
    edited = PLAN_TEXT.replace("monthly", "prior to each use")
    assert hash_plan(original) != hash_plan(edited)


def test_interpretation_required_for_every_result():
    results = _six_results_with(interpretation="")
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    inspect_card = next(c for c in v.cards if c.check_id == "PFAS_INSPECT_01")
    assert not inspect_card.valid


def test_all_valid_six_results_pass():
    results = _six_results_with()
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    assert v.all_valid
    assert v.valid_count == 6


def test_real_but_irrelevant_span_passes_validation():
    """Boundary case 7.3: the validator proves a quote is real, not that it
    supports the conclusion. Here the certification sentence is cited as
    evidence for the inspection check -- and it passes. This is a disclosed
    limit, not a bug: source matched != interpretation correct."""
    results = _six_results_with(
        status="evidence_found",
        plan_span="Training certification records are maintained by the HR office.",
    )
    v = validate(_full_response(results), PLAN_TEXT, EXPECTED_IDS)
    assert v.all_valid
