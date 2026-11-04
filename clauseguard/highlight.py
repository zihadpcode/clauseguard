"""Locates validated plan_spans in the original plan text so the UI can mark
them. Display only: validation (validator.py) is the authority on whether a
span exists; a span this module can't place is simply not highlighted."""
import html
import re

_SINGLE_QUOTES = "'‘’‚‛′ʼ"
_DOUBLE_QUOTES = '"“”„‟″'


def _span_pattern(span: str) -> re.Pattern:
    span = span.strip()
    if span.endswith("."):
        span = span[:-1]
    parts = []
    for ch in span:
        if ch.isspace():
            if not parts or parts[-1] != r"\s+":
                parts.append(r"\s+")
        elif ch in _SINGLE_QUOTES:
            parts.append(f"[{re.escape(_SINGLE_QUOTES)}]")
        elif ch in _DOUBLE_QUOTES:
            parts.append(f"[{re.escape(_DOUBLE_QUOTES)}]")
        else:
            parts.append(re.escape(ch))
    return re.compile("".join(parts) + r"\.?", re.IGNORECASE)


def find_spans(plan_text: str, spans: list[tuple[str, str, str]]) -> list[tuple[int, int, str, str]]:
    """spans: (check_id, status, span) -> non-overlapping (start, end, check_id, status)."""
    found = []
    for check_id, status, span in spans:
        if not span:
            continue
        m = _span_pattern(span).search(plan_text)
        if m:
            found.append((m.start(), m.end(), check_id, status))
    found.sort()
    result, last_end = [], -1
    for start, end, check_id, status in found:
        if start >= last_end:
            result.append((start, end, check_id, status))
            last_end = end
    return result


def highlight_html(plan_text: str, spans: list[tuple[str, str, str]]) -> str:
    out, pos = [], 0
    for start, end, check_id, status in find_spans(plan_text, spans):
        out.append(html.escape(plan_text[pos:start]))
        short = check_id.removeprefix("PFAS_").removesuffix("_01")
        out.append(
            f'<mark class="cg-hl cg-hl--{html.escape(status)}" title="{html.escape(check_id)}">'
            f"{html.escape(plan_text[start:end])}"
            f'<sup class="cg-hl-tag">{html.escape(short)}</sup></mark>'
        )
        pos = end
    out.append(html.escape(plan_text[pos:]))
    return "".join(out)
