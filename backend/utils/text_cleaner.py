"""Shared text normalization helpers."""

import re


def clean_text(text: str) -> str:
    """Lowercase text and collapse non-word characters to spaces."""
    if not text:
        return ""
    text = re.sub(r"\W+", " ", text)
    return text.strip().lower()


def tokenize(text: str) -> list[str]:
    """Return whitespace-separated tokens from cleaned text."""
    cleaned = clean_text(text)
    return cleaned.split() if cleaned else []
