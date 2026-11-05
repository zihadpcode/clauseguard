"""Builds data/checks.json: computes the SHA-256 of each verbatim eCFR
excerpt and writes the index. Run this, don't hand-edit hashes.

PROVENANCE NOTE: this sandbox's network policy blocks outbound requests to
www.ecfr.gov, www.osha.gov, and law.cornell.edu (DNS resolution fails for
all three -- confirmed, not assumed). The text below was therefore typed
from the author's trained knowledge of this specific, heavily-reproduced
regulation, not copied from a live fetch during this build. It has NOT been
re-verified against eCFR by a human as section 4.4 of the proposal requires.
Do this before relying on it: open each URL below and diff the quoted text
against the current eCFR section by eye.

UPDATE 2026-11-04: every excerpt was compared, fragment by fragment, against
the official OSHA copies (osha.gov/laws-regs/regulations/standardnumber/1926/
1926.502 and 1926.503); eCFR itself refused automated fetches. All six
matched except (d)(21), which read "damage, and" where the official text has
"damage and"; that comma was removed. PFAS_CERT_01 is an excerpt: it omits
the last sentence of (b)(1) on training done by another employer. The flag
below stays False because no human has yet read the excerpts against eCFR.
"""
import hashlib
import json
from pathlib import Path

RETRIEVAL_DATE = "2026-11-04"
NOT_VERIFIED_AGAINST_LIVE_ECFR = True  # see module docstring

CHECKS = [
    {
        "check_id": "PFAS_RESCUE_01",
        "question": "Does the plan provide for prompt rescue, or assure employees can rescue themselves?",
        "cfr_paragraph": "29 CFR 1926.502(d)(20)",
        "ecfr_url": "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1926/subpart-M/section-1926.502",
        "kind": "conduct",
        "verbatim_text": (
            "The employer shall provide for prompt rescue of employees in the "
            "event of a fall or shall assure that employees are able to rescue "
            "themselves."
        ),
    },
    {
        "check_id": "PFAS_INSPECT_01",
        "question": "Does the plan require PFAS inspection prior to each use, with defective components removed from service?",
        "cfr_paragraph": "29 CFR 1926.502(d)(21)",
        "ecfr_url": "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1926/subpart-M/section-1926.502",
        "kind": "conduct",
        "verbatim_text": (
            "Personal fall arrest systems shall be inspected prior to each use "
            "for wear, damage and other deterioration, and defective "
            "components shall be removed from service."
        ),
    },
    {
        "check_id": "PFAS_IMPACT_01",
        "question": "Does the plan remove impact loaded components from service until a competent person clears them?",
        "cfr_paragraph": "29 CFR 1926.502(d)(19)",
        "ecfr_url": "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1926/subpart-M/section-1926.502",
        "kind": "conduct",
        "verbatim_text": (
            "Personal fall arrest systems and components subjected to impact "
            "loading shall be immediately removed from service and shall not "
            "be used again for employee protection until inspected and "
            "determined by a competent person to be undamaged and suitable "
            "for reuse."
        ),
    },
    {
        "check_id": "PFAS_FREEFALL_01",
        "question": "Does the plan state the free fall and deceleration limits?",
        "cfr_paragraph": "29 CFR 1926.502(d)(16)(iii)-(iv)",
        "ecfr_url": "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1926/subpart-M/section-1926.502",
        "kind": "conduct",
        "verbatim_text": (
            "Personal fall arrest systems, when stopping a fall, shall: ... "
            "(iii) be rigged such that an employee can neither free fall more "
            "than 6 feet (1.8 m), nor contact any lower level; [and] (iv) "
            "bring an employee to a complete stop and limit maximum "
            "deceleration distance an employee travels to 3.5 feet (1.07 m)."
        ),
    },
    {
        "check_id": "PFAS_TRAIN_01",
        "question": "Does the plan provide a training program for employees exposed to fall hazards?",
        "cfr_paragraph": "29 CFR 1926.503(a)(1)",
        "ecfr_url": "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1926/subpart-M/section-1926.503",
        "kind": "conduct",
        "verbatim_text": (
            "The employer shall provide a training program for each employee "
            "who might be exposed to fall hazards. The program shall enable "
            "each employee to recognize the hazards of falling and shall "
            "train each employee in the procedures to be followed in order "
            "to minimize these hazards."
        ),
    },
    {
        "check_id": "PFAS_CERT_01",
        "question": "Does the plan address the written training certification record?",
        "cfr_paragraph": "29 CFR 1926.503(b)(1)",
        "ecfr_url": "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1926/subpart-M/section-1926.503",
        "kind": "documentation",
        "verbatim_text": (
            "The employer shall verify compliance with paragraph (a) of this "
            "section by preparing a written certification record. The written "
            "certification record shall contain the name or other identity of "
            "the employee trained, the date(s) of the training, and the "
            "signature of the person who conducted the training or the "
            "signature of the employer."
        ),
    },
]

for c in CHECKS:
    c["retrieval_date"] = RETRIEVAL_DATE
    c["sha256"] = hashlib.sha256(c["verbatim_text"].encode("utf-8")).hexdigest()
    c["verified_against_live_ecfr_by_human"] = False

out_path = Path(__file__).resolve().parent.parent / "data" / "checks.json"
out_path.write_text(json.dumps({"checks": CHECKS}, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {out_path} with {len(CHECKS)} checks.")
