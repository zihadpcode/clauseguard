"""Deterministic, no-model validation (spec section 4.3).

The model decides *what* a check's status is; this module decides whether
the response can be trusted to render at all. It never judges whether an
interpretation is correct -- only whether the response is complete,
well-formed, and whether every quoted span actually exists in the plan.
"""
from dataclasses import dataclass, field

from .normalize import normalize

EXPECTED_STATUSES = {"potential_conflict", "evidence_found", "needs_information", "not_located"}
SPAN_STATUSES = {"potential_conflict", "evidence_found"}
EVIDENCE_REQUEST_STATUSES = {"needs_information", "not_located"}
MIN_SPAN_LENGTH = 20


@dataclass
class CardValidation:
    check_id: str
    status: str | None
    plan_span: str | None
    interpretation: str | None
    evidence_request: str | None
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class ValidationResult:
    cards: list[CardValidation]
    global_errors: list[str] = field(default_factory=list)

    @property
    def all_valid(self) -> bool:
        return not self.global_errors and all(c.valid for c in self.cards)

    @property
    def valid_count(self) -> int:
        return sum(1 for c in self.cards if c.valid)


def validate(response: dict, plan_text: str, expected_check_ids: set[str]) -> ValidationResult:
    """Rules 1-6 of spec section 4.3. Rule 1 (parses as JSON) is the
    caller's responsibility -- a json.JSONDecodeError never reaches here."""
    global_errors: list[str] = []
    cards: list[CardValidation] = []

    results = response.get("results") if isinstance(response, dict) else None
    if not isinstance(results, list):
        global_errors.append("Response has no 'results' array.")
        return ValidationResult(cards=[], global_errors=global_errors)

    # Rule 2: exactly six results; set of check_id equals expected; no duplicates.
    if len(results) != len(expected_check_ids):
        global_errors.append(
            f"Expected {len(expected_check_ids)} results, got {len(results)}."
        )

    seen_ids: list[str] = []
    for raw in results:
        # json_object fallback mode has no schema enforcement, so a field can
        # arrive as any JSON type; non-strings are rejected, never len()'d or hashed.
        type_errors: list[str] = []
        if not isinstance(raw, dict):
            type_errors.append("Result is not an object.")

        def field(name):
            value = raw.get(name) if isinstance(raw, dict) else None
            if value is not None and not isinstance(value, str):
                type_errors.append(f"{name} must be a string or null.")
                return None
            return value

        check_id = field("check_id")
        status = field("status")
        plan_span = field("plan_span")
        interpretation = field("interpretation")
        evidence_request = field("evidence_request")

        card = CardValidation(
            check_id=check_id,
            status=status,
            plan_span=plan_span,
            interpretation=interpretation,
            evidence_request=evidence_request,
            errors=type_errors,
        )

        if check_id in seen_ids:
            card.errors.append(f"Duplicate check_id '{check_id}'.")
        seen_ids.append(check_id)

        if check_id not in expected_check_ids:
            card.errors.append(f"Unknown check_id '{check_id}'.")

        # Rule 3: status is one of the four values.
        if status not in EXPECTED_STATUSES:
            card.errors.append(f"Status '{status}' is not one of the four allowed values.")
            cards.append(card)
            continue

        # Rule 4: potential_conflict / evidence_found require a real span.
        if status in SPAN_STATUSES:
            if not plan_span or len(plan_span) < MIN_SPAN_LENGTH:
                card.errors.append(
                    f"Status '{status}' requires plan_span of at least "
                    f"{MIN_SPAN_LENGTH} characters."
                )
            elif normalize(plan_span) not in normalize(plan_text):
                card.errors.append(
                    "plan_span does not occur in the plan text after normalization "
                    "(possible fabricated quote)."
                )

        # Rule 5: needs_information / not_located require a non-empty evidence_request.
        if status in EVIDENCE_REQUEST_STATUSES:
            if not evidence_request or not evidence_request.strip():
                card.errors.append(
                    f"Status '{status}' requires a non-empty evidence_request."
                )

        # Rule 6: interpretation non-empty for every result.
        if not interpretation or not interpretation.strip():
            card.errors.append("interpretation is empty.")

        cards.append(card)

    missing = expected_check_ids - set(seen_ids)
    for missing_id in sorted(missing):
        global_errors.append(f"Missing required check_id '{missing_id}'.")

    return ValidationResult(cards=cards, global_errors=global_errors)
