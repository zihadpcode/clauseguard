"""Builds web/dist/clauseguard.html: one self-contained page (the hosted demo
runs in a sandbox that blocks fetches), with the pinned regulatory index,
the stub responses and the two development plans embedded as JSON."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clauseguard import model_client  # noqa: E402

SRC = ROOT / "web" / "src"
OUT = ROOT / "web" / "dist" / "clauseguard.html"


def ascii_js(path: Path) -> str:
    # Keeps sources free of raw U+2028/U+2029 and friends, which end a JS
    # regex literal; every non-ASCII char becomes a \u escape.
    text = path.read_text(encoding="utf-8")
    return "".join(ch if ord(ch) < 128 else "\\u%04x" % ord(ch) for ch in text)


def main():
    plan_a = (ROOT / "data" / "plan_a.txt").read_text(encoding="utf-8").strip()
    plan_b = (ROOT / "data" / "plan_b.txt").read_text(encoding="utf-8").strip()
    stubs = {k: {"label": v["label"], "response": v["response"]}
             for k, v in model_client._load_stub_table().items() if not k.startswith("_")}
    data = {
        "checks": model_client.load_checks(),
        "stubs": stubs,
        "plans": {"a": plan_a, "b": plan_b, "a_hash": model_client.hash_plan(plan_a)},
    }
    data_json = json.dumps(data, ensure_ascii=True).replace("</", "<\\/")
    page = (SRC / "page.html").read_text(encoding="utf-8")
    for key, value in {
        "{{STYLES}}": (SRC / "styles.css").read_text(encoding="utf-8"),
        "{{DATA}}": data_json,
        "{{VALIDATOR}}": ascii_js(SRC / "validator.js"),
        "{{HIGHLIGHT}}": ascii_js(SRC / "highlight.js"),
        "{{APP}}": ascii_js(SRC / "app.js"),
    }.items():
        assert page.count(key) == 1, key
        page = page.replace(key, value)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
