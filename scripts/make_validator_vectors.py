"""Generates tests/vectors/validator_cases.json: inputs plus the Python
validator's exact outputs. The web build's JS validator must reproduce
these byte for byte (tests/js/validator.test.mjs), and pytest checks the
Python validator still does (tests/test_vectors.py)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clauseguard import model_client, validator  # noqa: E402

IDS = sorted(c["check_id"] for c in model_client.load_checks())
PLAN_A = (ROOT / "data" / "plan_a.txt").read_text(encoding="utf-8").strip()
PLAN_B = (ROOT / "data" / "plan_b.txt").read_text(encoding="utf-8").strip()
STUB = model_client._load_stub_table()
RESP_A = STUB[model_client.hash_plan(PLAN_A)]["response"]
RESP_B = STUB[model_client.hash_plan(PLAN_B)]["response"]
INSPECT_A = "Harnesses and lanyards will be inspected monthly by the site safety coordinator, and damaged equipment will be tagged out."


def with_card(resp, target_id, **changes):
    out = json.loads(json.dumps(resp))
    for r in out["results"]:
        if r["check_id"] == target_id:
            r.update(changes)
    return out


def cases():
    yield "plan_a_stub_valid", PLAN_A, RESP_A
    yield "plan_b_stub_valid", PLAN_B, RESP_B
    yield "unknown_check_id", PLAN_A, with_card(RESP_A, "PFAS_RESCUE_01", check_id="PFAS_MADE_UP_01")
    dup = json.loads(json.dumps(RESP_A))
    dup["results"][1] = dict(dup["results"][0])
    yield "duplicate_check_id", PLAN_A, dup
    yield "five_results", PLAN_A, {"results": RESP_A["results"][:5]}
    yield "seven_results", PLAN_A, {"results": RESP_A["results"] + [RESP_A["results"][0]]}
    yield "conflict_null_span", PLAN_A, with_card(RESP_A, "PFAS_INSPECT_01", plan_span=None)
    yield "span_not_in_plan", PLAN_A, with_card(RESP_A, "PFAS_INSPECT_01", plan_span="Harnesses will be inspected yearly by nobody at all.")
    yield "span_too_short", PLAN_A, with_card(RESP_A, "PFAS_INSPECT_01", plan_span="inspected monthly")
    yield "not_located_null_request", PLAN_A, with_card(RESP_A, "PFAS_IMPACT_01", evidence_request=None)
    yield "needs_info_blank_request", PLAN_A, with_card(RESP_A, "PFAS_CERT_01", evidence_request="   ")
    yield "empty_interpretation", PLAN_A, with_card(RESP_A, "PFAS_TRAIN_01", interpretation="")
    yield "invented_status", PLAN_A, with_card(RESP_A, "PFAS_TRAIN_01", status="compliant")
    yield "linebreak_and_spaces_pass", PLAN_A, with_card(
        RESP_A, "PFAS_INSPECT_01", plan_span=INSPECT_A.replace("inspected monthly", "inspected\n   monthly"),
    )
    plan_apos = PLAN_A.replace("site safety coordinator", "site's safety coordinator")
    yield "curly_apostrophe_pass", plan_apos, with_card(
        RESP_A, "PFAS_INSPECT_01",
        plan_span=INSPECT_A.replace("site safety coordinator", "site’s safety coordinator"),
    )
    yield "fullwidth_nfkc_pass", PLAN_A, with_card(
        RESP_A, "PFAS_INSPECT_01", plan_span=INSPECT_A.replace("monthly", "ｍｏｎｔｈｌｙ"),
    )
    yield "trailing_period_and_case_pass", PLAN_A, with_card(
        RESP_A, "PFAS_INSPECT_01", plan_span=INSPECT_A.rstrip(".").upper(),
    )
    yield "irrelevant_real_span_passes", PLAN_A, with_card(
        RESP_A, "PFAS_INSPECT_01", status="evidence_found",
        plan_span="Training certification records are maintained by the HR office.",
    )
    yield "non_string_span_rejected", PLAN_A, with_card(RESP_A, "PFAS_INSPECT_01", plan_span=12345)
    yield "list_check_id_rejected", PLAN_A, with_card(RESP_A, "PFAS_RESCUE_01", check_id=["PFAS_RESCUE_01"])
    not_obj = json.loads(json.dumps(RESP_A))
    not_obj["results"][0] = "PFAS_RESCUE_01 looks fine"
    yield "result_not_an_object", PLAN_A, not_obj
    yield "results_not_a_list", PLAN_A, {"results": "six results, trust me"}
    yield "no_results_key", PLAN_A, {"checks": []}


def run(plan, response):
    v = validator.validate(response, plan, set(IDS))
    return {
        "all_valid": v.all_valid,
        "valid_count": v.valid_count,
        "global_errors": v.global_errors,
        "cards": [{"check_id": c.check_id, "errors": c.errors} for c in v.cards],
    }


def main():
    out = [
        {"name": name, "plan_text": plan, "expected_ids": IDS, "response": resp, "expected": run(plan, resp)}
        for name, plan, resp in cases()
    ]
    path = ROOT / "tests" / "vectors" / "validator_cases.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} cases to {path}")
    for c in out:
        print(f"  {c['name']:34} all_valid={c['expected']['all_valid']}")


if __name__ == "__main__":
    main()
