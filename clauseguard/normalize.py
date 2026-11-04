"""Span-matching normalization (spec section 4.3).

Applied identically to a model-returned plan_span and to the full plan text
before checking containment. Without this, exact matching fails on line
breaks and smart quotes and produces false validation failures.
"""
import unicodedata

_QUOTE_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "′": "'", "ʼ": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"',
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for curly, straight in _QUOTE_MAP.items():
        text = text.replace(curly, straight)
    text = " ".join(text.split())
    text = text.lower()
    if text.endswith("."):
        text = text[:-1]
    return text
