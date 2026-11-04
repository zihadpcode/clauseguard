"""App-level tests: drive the real Streamlit script headlessly (no browser,
no model call) to cover behavior that lives in the UI, not the validator."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from clauseguard import model_client

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
PLAN_A = (ROOT / "data" / "plan_a.txt").read_text(encoding="utf-8").strip()
PLAN_B = (ROOT / "data" / "plan_b.txt").read_text(encoding="utf-8").strip()


@pytest.fixture(autouse=True)
def _no_live_model(monkeypatch, tmp_path):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("CLAUSEGUARD_LOG_PATH", str(tmp_path / "runs.jsonl"))


def _confirmed_app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["scenario_confirmed"] = True
    at.run()
    return at


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def _click(at, label):
    _button(at, label).click().run()


def _html(at) -> str:
    return "\n".join(e.proto.body for e in at.get("html") if not e.proto.body.lstrip().startswith("<style"))


def _cards(at) -> list[str]:
    return [e.proto.body for e in at.get("html") if e.proto.body.startswith("<article")]


def _card(at, check_id) -> str:
    return next(c for c in _cards(at) if f'data-check="{check_id}"' in c or f">{check_id}<" in c)


def _analyze(at, text):
    at.text_area[0].input(text).run()
    _click(at, "Analyze plan")


def test_scenario_no_stops_at_profile_screen():
    at = AppTest.from_file(APP, default_timeout=30).run()
    _click(at, "No, a different system")
    assert "This scenario is not supported" in _html(at)
    assert not at.text_area


def test_scenario_yes_reaches_input_step():
    at = AppTest.from_file(APP, default_timeout=30).run()
    _click(at, "Yes, conventional PFAS")
    assert at.text_area


def test_empty_input_is_incomplete_and_cannot_analyze():
    at = _confirmed_app()
    at.text_area[0].input("too short").run()
    assert "INCOMPLETE" in _html(at)
    assert _button(at, "Analyze plan").disabled


def test_extraction_preview_shows_lines_and_characters():
    at = _confirmed_app()
    at.text_area[0].input(PLAN_A).run()
    body = _html(at)
    assert f"<b>{len(PLAN_A.splitlines())}</b><span>lines</span>" in body
    assert f"<b>{len(PLAN_A):,}</b><span>characters</span>" in body


def test_plan_a_inspection_conflict_then_fix_flips_status():
    at = _confirmed_app()
    _analyze(at, PLAN_A)
    assert "6 of 6 checks returned with valid evidence fields" in _html(at)
    inspect = _card(at, "PFAS_INSPECT_01")
    assert "Potential conflict" in inspect
    assert "inspected monthly" in inspect
    assert "prior to each use" in inspect  # regulation shown beside it

    _analyze(at, PLAN_B)
    inspect = _card(at, "PFAS_INSPECT_01")
    assert "Evidence found" in inspect
    assert "prior to each use for wear, damage, and deterioration, and defective" in inspect


def test_every_card_carries_regulation_from_index_and_disclaimer():
    at = _confirmed_app()
    _analyze(at, PLAN_A)
    checks = model_client.load_checks()
    cards = _cards(at)
    assert len(cards) == 6
    for check in checks:
        card = _card(at, check["check_id"])
        assert check["cfr_paragraph"] in card
        assert f'<span class="cg-cite">{check["cfr_paragraph"]}</span>' in card  # never uppercased
        assert check["sha256"][:12] in card
        assert "Not legal advice" in card
        assert "Source matched; interpretation requires review." in card


def test_not_located_wording_never_says_missing():
    at = _confirmed_app()
    _analyze(at, PLAN_A)
    card = _card(at, "PFAS_IMPACT_01")
    assert f"Not located in the supplied text ({len(PLAN_A.splitlines())} lines, {len(PLAN_A):,} characters)." in card
    assert "missing" not in card.lower()
    assert "noncompliant" not in card.lower()


def test_open_items_never_render_as_a_clean_review():
    at = _confirmed_app()
    _analyze(at, PLAN_B)
    body = _html(at)
    assert "cg-banner--clean" not in body
    assert "Review is not clean" in body
    assert "1 not located" in body and "1 needs information" in body


def test_result_is_stamped_with_hash_index_model_and_time():
    at = _confirmed_app()
    _analyze(at, PLAN_A)
    stamp = next(b for b in (e.proto.body for e in at.get("html")) if "cg-stamp" in b)
    assert model_client.hash_plan(PLAN_A)[:16] in stamp
    assert "checks.json v1" in stamp
    assert "muse-spark-1.3" in stamp and "STUBBED" in stamp
    assert "UTC" in stamp


def test_plan_view_highlights_quoted_evidence():
    at = _confirmed_app()
    _analyze(at, PLAN_A)
    view = next(b for b in (e.proto.body for e in at.get("html")) if "cg-planview" in b)
    assert 'cg-hl--potential_conflict' in view
    assert view.count("<mark") == 4  # rescue, inspect, freefall, train


def test_plan_text_edited_after_run_clears_results():
    at = _confirmed_app()
    _analyze(at, PLAN_A)
    assert at.session_state["model_result"] is not None

    at.text_area[0].input(PLAN_A + " One more sentence.").run()
    assert at.session_state["model_result"] is None
    body = _html(at)
    assert "cg-stamp" not in body
    assert "previous results were cleared" in body


def test_invalid_response_shows_review_incomplete_on_main_surface(monkeypatch):
    bad = {"results": [
        {
            "check_id": "PFAS_INSPECT_01",
            "status": "evidence_found",
            "plan_span": "This sentence was never in the plan text at all.",
            "interpretation": "Fabricated.",
            "evidence_request": None,
        }
    ]}

    def fake_call(plan_text, checks=None):
        return model_client.ModelCallResult(raw_response=bad, mode="stub", schema_mode="stub", model_id="test")

    monkeypatch.setattr(model_client, "call_model", fake_call)
    at = _confirmed_app()
    _analyze(at, PLAN_A)
    body = _html(at)
    assert "REVIEW INCOMPLETE" in body
    assert "Missing required check_id" in body
    inspect = _card(at, "PFAS_INSPECT_01")
    assert "Validation failure" in inspect and "do not rely on this card" in inspect
    assert "Source matched" not in inspect
    assert "No result returned" in _card(at, "PFAS_RESCUE_01")


def test_untrusted_model_output_is_escaped(monkeypatch):
    payload = '<img src=x onerror="alert(1)"><script>alert(2)</script>'
    stub = model_client._load_stub_table()[model_client.hash_plan(PLAN_A)]["response"]
    evil = {"results": [dict(r, interpretation=payload) for r in stub["results"]]}

    def fake_call(plan_text, checks=None):
        return model_client.ModelCallResult(raw_response=evil, mode="stub", schema_mode="stub", model_id="test")

    monkeypatch.setattr(model_client, "call_model", fake_call)
    at = _confirmed_app()
    _analyze(at, PLAN_A)
    body = _html(at)
    assert "<script>alert(2)" not in body and "<img src=x" not in body
    assert "&lt;script&gt;" in body


def test_unrecognized_text_in_stub_mode_refuses_instead_of_fabricating():
    at = _confirmed_app()
    _analyze(at, "All workers will wear harnesses. Inspection happens whenever convenient.")
    assert "stub mode" in _html(at)
    assert at.session_state["model_result"] is None


def test_demo_loader_sets_text_and_source():
    at = _confirmed_app()
    _click(at, "Load Plan A (as submitted)")
    assert at.text_area[0].value == PLAN_A
    assert "demo: Plan A" in _html(at)
