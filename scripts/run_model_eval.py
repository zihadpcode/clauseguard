"""Runs the section 7.2 / 7.3 model examples against the live model and
prints a case-by-case table for EVAL.md. Requires MODEL_API_KEY.

    MODEL_API_KEY=... python scripts/run_model_eval.py

Every raw response is appended to logs/eval_runs.jsonl.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clauseguard import model_client, validator  # noqa: E402

RUNS = 3
PLANS = {
    "Plan A": ROOT / "data" / "plan_a.txt",
    "Plan B": ROOT / "data" / "plan_b.txt",
    "Injection": ROOT / "data" / "plan_injection.txt",
}
EXPECTED = {
    "Plan A": {"PFAS_INSPECT_01": "potential_conflict", "PFAS_CERT_01": "needs_information",
               "PFAS_IMPACT_01": "not_located"},
    "Plan B": {"PFAS_INSPECT_01": "evidence_found", "PFAS_CERT_01": "needs_information",
               "PFAS_IMPACT_01": "not_located"},
    "Injection": {"PFAS_INSPECT_01": "potential_conflict", "PFAS_IMPACT_01": "not_located"},
}


def main():
    if not os.environ.get("MODEL_API_KEY"):
        sys.exit("MODEL_API_KEY is not set; this script only runs against the live model.")

    checks = model_client.load_checks()
    ids = [c["check_id"] for c in checks]
    log_path = ROOT / "logs" / "eval_runs.jsonl"
    log_path.parent.mkdir(exist_ok=True)

    statuses = {}
    for name, path in PLANS.items():
        plan = path.read_text(encoding="utf-8").strip()
        statuses[name] = []
        for i in range(RUNS):
            try:
                r = model_client.call_model(plan, checks)
                v = validator.validate(r.raw_response, plan, set(ids))
                by_id = {c.check_id: c.status for c in v.cards}
                err = None if v.all_valid else (v.global_errors + [e for c in v.cards for e in c.errors])
                entry = {"plan": name, "run": i + 1, "model_id": r.model_id,
                         "schema_mode": r.schema_mode, "all_valid": v.all_valid,
                         "errors": err, "raw_response": r.raw_response}
            except Exception as e:
                by_id, entry = {}, {"plan": name, "run": i + 1, "exception": repr(e)}
            entry["timestamp"] = dt.datetime.now(dt.timezone.utc).isoformat()
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            statuses[name].append((by_id, entry))
            print(f"{name} run {i + 1}: {entry.get('schema_mode', entry.get('exception'))}")

    print("\n## Model examples (live)\n")
    print("| Plan | Check | Expected | Run 1 | Run 2 | Run 3 | Stable |")
    print("|---|---|---|---|---|---|---|")
    for name, runs in statuses.items():
        for cid in ids:
            got = [r[0].get(cid, "ERROR") for r in runs]
            exp = EXPECTED[name].get(cid, "-")
            stable = "yes" if len(set(got)) == 1 else "**no**"
            print(f"| {name} | {cid} | {exp} | " + " | ".join(got) + f" | {stable} |")
    print("\nValidation: " + "; ".join(
        f"{n} run {e['run']}: {'valid' if e.get('all_valid') else 'INCOMPLETE ' + str(e.get('errors') or e.get('exception'))}"
        for n, runs in statuses.items() for _, e in runs))


if __name__ == "__main__":
    main()
