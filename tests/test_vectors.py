"""The Python validator must keep producing the golden outputs that the web
build's JS validator is held to (tests/js/validator.test.mjs)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from clauseguard import validator

ROOT = Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / "tests" / "vectors" / "validator_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_python_validator_matches_golden_vector(case):
    v = validator.validate(case["response"], case["plan_text"], set(case["expected_ids"]))
    got = {
        "all_valid": v.all_valid,
        "valid_count": v.valid_count,
        "global_errors": v.global_errors,
        "cards": [{"check_id": c.check_id, "errors": c.errors} for c in v.cards],
    }
    assert got == case["expected"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_validator_matches_golden_vectors():
    out = subprocess.run(
        ["node", "--test", *map(str, sorted((ROOT / "tests" / "js").glob("*.test.mjs")))],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert out.returncode == 0, out.stdout[-3000:] + out.stderr[-2000:]
