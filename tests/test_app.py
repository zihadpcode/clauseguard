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


def _click(at, label):
    next(b for b in at.button if b.label == label).click().run()


def _all_text(at):
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [e.value for e in at.error] + [s.value for s in at.success]
    parts += [w.value for w in at.warning]
    return "\n".join(str(p) for p in parts)


def test_scenario_no_stops_at_profile_screen():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio[0].set_value("No").run()
    assert any("not supported" in e.value for e in at.error)
    assert not at.text_area  # never reaches the input step


def test_empty_input_is_incomplete_and_cannot_analyze():
    at = _confirmed_app()
    at.text_area[0].input("too short").run()
    assert any("INCOMPLETE" in w.value for w in at.warning)
    analyze = next(b for b in at.button if b.label == "Analyze")
    assert analyze.disabled


def test_plan_a_inspection_conflict_then_fix_flips_status():
    at = _confirmed_app()
    at.text_area[0].input(PLAN_A).run()
    _click(at, "Analyze")
    text = _all_text(at)
    assert "6 of 6 checks returned with valid evidence fields" in text
    assert "Potential conflict" in text
    assert "inspected monthly" in text

    at.text_area[0].input(PLAN_B).run()
    _click(at, "Analyze")
    text = _all_text(at)
    assert "Potential conflict" not in text
    assert "prior to each use for wear" in text


def test_open_items_never_render_as_a_clean_review():
    at = _confirmed_app()
    at.text_area[0].input(PLAN_B).run()
    _click(at, "Analyze")
    assert not at.success
    banner = at.warning[0].value
    assert "Review is not clean" in banner
    assert "1 not located" in banner
    assert "1 needs information" in banner


def test_plan_text_edited_after_run_clears_results():
    at = _confirmed_app()
    at.text_area[0].input(PLAN_A).run()
    _click(at, "Analyze")
    assert at.session_state["model_result"] is not None

    at.text_area[0].input(PLAN_A + " One more sentence.").run()
    assert at.session_state["model_result"] is None
    assert "Stamp:" not in _all_text(at)


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
        return model_client.ModelCallResult(
            raw_response=bad, mode="stub", schema_mode="stub", model_id="test"
        )

    monkeypatch.setattr(model_client, "call_model", fake_call)
    at = _confirmed_app()
    at.text_area[0].input(PLAN_A).run()
    _click(at, "Analyze")
    errors = [e.value for e in at.error]
    assert "REVIEW INCOMPLETE" in errors
    assert any("Missing required check_id" in e for e in errors)
    assert any("Validation failure on this card" in e for e in errors)


def test_unrecognized_text_in_stub_mode_refuses_instead_of_fabricating():
    at = _confirmed_app()
    at.text_area[0].input(
        "All workers will wear harnesses. Inspection happens whenever convenient."
    ).run()
    _click(at, "Analyze")
    assert any("stub mode" in e.value for e in at.error)
    assert at.session_state["model_result"] is None
