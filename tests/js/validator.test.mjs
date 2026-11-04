// Holds the web build's JS validator to the Python validator's golden outputs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { validate } = require("../../web/src/validator.js");
const cases = JSON.parse(readFileSync(new URL("../vectors/validator_cases.json", import.meta.url), "utf8"));

for (const c of cases) {
  test(c.name, () => {
    const v = validate(c.response, c.plan_text, c.expected_ids);
    assert.deepEqual(
      {
        all_valid: v.all_valid,
        valid_count: v.valid_count,
        global_errors: v.global_errors,
        cards: v.cards.map((card) => ({ check_id: card.check_id, errors: card.errors })),
      },
      c.expected,
    );
  });
}
