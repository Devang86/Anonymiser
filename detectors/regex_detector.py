"""
Regex-based entity detection for Indian financial identifiers and contact details.
"""

from __future__ import annotations

from config import (
    BANK_ACCOUNT_CONTEXT_WINDOW,
    BANK_ACCOUNT_CONTEXT_WORDS,
    REGEX_PATTERNS,
)
from detectors.ner_detector import DetectedEntity


def _has_context(text: str, start: int, end: int, words: list[str], window: int) -> bool:
    """Check if any context word appears within *window* chars of the match."""
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    snippet = text[ctx_start:ctx_end].lower()
    return any(w in snippet for w in words)


def detect_regex_entities(text: str) -> list[DetectedEntity]:
    """Scan *text* with all configured regex patterns and return matches."""
    entities: list[DetectedEntity] = []

    for label, pattern in REGEX_PATTERNS.items():
        for m in pattern.finditer(text):
            # Bank account numbers need context gating
            if label == "BANK_ACCOUNT":
                if not _has_context(
                    text, m.start(), m.end(),
                    BANK_ACCOUNT_CONTEXT_WORDS,
                    BANK_ACCOUNT_CONTEXT_WINDOW,
                ):
                    continue

            entities.append(
                DetectedEntity(
                    text=m.group(),
                    label=label,
                    start=m.start(),
                    end=m.end(),
                    source="regex",
                )
            )

    return entities
