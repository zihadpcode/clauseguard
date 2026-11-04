// Port of clauseguard/validator.py + normalize.py. Held to the Python
// validator's exact outputs by tests/js/validator.test.mjs (shared vectors).
(function (root) {
  "use strict";

  const EXPECTED_STATUSES = ["potential_conflict", "evidence_found", "needs_information", "not_located"];
  const SPAN_STATUSES = ["potential_conflict", "evidence_found"];
  const EVIDENCE_REQUEST_STATUSES = ["needs_information", "not_located"];
  const MIN_SPAN_LENGTH = 20;

  const QUOTE_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u2032": "'", "\u02bc": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"', "\u2033": '"',
  };

  // Python's str.split() whitespace set (adds \x1c-\x1f, excludes \ufeff).
  const PY_WS = /[\t\n\v\f\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+/;
  const PY_STRIP = /^[\t\n\v\f\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\t\n\v\f\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g;

  const pyLen = (s) => Array.from(s).length;
  const pyStrip = (s) => s.replace(PY_STRIP, "");
  const pyStr = (v) => (v === null || v === undefined ? "None" : String(v));
  const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

  function normalize(text) {
    text = text.normalize("NFKC");
    for (const [curly, straight] of Object.entries(QUOTE_MAP)) text = text.split(curly).join(straight);
    text = text.split(PY_WS).filter(Boolean).join(" ");
    text = text.toLowerCase();
    if (text.endsWith(".")) text = text.slice(0, -1);
    return text;
  }

  function validate(response, planText, expectedCheckIds) {
    const expected = new Set(expectedCheckIds);
    const globalErrors = [];
    const cards = [];

    const results = isObj(response) ? response.results : undefined;
    if (!Array.isArray(results)) {
      globalErrors.push("Response has no 'results' array.");
      return finish(cards, globalErrors);
    }
    if (results.length !== expected.size) {
      globalErrors.push(`Expected ${expected.size} results, got ${results.length}.`);
    }

    const seen = [];
    for (const raw of results) {
      const errors = [];
      if (!isObj(raw)) errors.push("Result is not an object.");
      const field = (name) => {
        const v = isObj(raw) && name in raw ? raw[name] : null;
        if (v !== null && typeof v !== "string") {
          errors.push(`${name} must be a string or null.`);
          return null;
        }
        return v;
      };
      const card = {
        check_id: field("check_id"),
        status: field("status"),
        plan_span: field("plan_span"),
        interpretation: field("interpretation"),
        evidence_request: field("evidence_request"),
        errors,
      };
      const { check_id: checkId, status, plan_span: span } = card;

      if (seen.includes(checkId)) errors.push(`Duplicate check_id '${pyStr(checkId)}'.`);
      seen.push(checkId);
      if (!expected.has(checkId)) errors.push(`Unknown check_id '${pyStr(checkId)}'.`);

      if (!EXPECTED_STATUSES.includes(status)) {
        errors.push(`Status '${pyStr(status)}' is not one of the four allowed values.`);
        cards.push(card);
        continue;
      }
      if (SPAN_STATUSES.includes(status)) {
        if (!span || pyLen(span) < MIN_SPAN_LENGTH) {
          errors.push(`Status '${status}' requires plan_span of at least ${MIN_SPAN_LENGTH} characters.`);
        } else if (!normalize(planText).includes(normalize(span))) {
          errors.push("plan_span does not occur in the plan text after normalization (possible fabricated quote).");
        }
      }
      if (EVIDENCE_REQUEST_STATUSES.includes(status)) {
        if (!card.evidence_request || !pyStrip(card.evidence_request)) {
          errors.push(`Status '${status}' requires a non-empty evidence_request.`);
        }
      }
      if (!card.interpretation || !pyStrip(card.interpretation)) errors.push("interpretation is empty.");
      cards.push(card);
    }

    const missing = [...expected].filter((id) => !seen.includes(id)).sort();
    for (const id of missing) globalErrors.push(`Missing required check_id '${id}'.`);
    return finish(cards, globalErrors);
  }

  function finish(cards, globalErrors) {
    const validCount = cards.filter((c) => c.errors.length === 0).length;
    return {
      cards,
      global_errors: globalErrors,
      valid_count: validCount,
      all_valid: globalErrors.length === 0 && validCount === cards.length,
    };
  }

  const api = { normalize, validate, pyStrip, pyLen, MIN_SPAN_LENGTH };
  root.CGValidator = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
