"""
NER-based entity detection using spaCy (offline, en_core_web_sm).
"""

from __future__ import annotations

from dataclasses import dataclass

from config import REGEX_PATTERNS, SPACY_ENTITY_LABELS

# Common acronyms / label words that spaCy may wrongly tag as entities
_FALSE_POSITIVE_WORDS = {
    "pan", "gstin", "cin", "ifsc", "neft", "rtgs", "imps", "upi",
    "kyc", "aml", "rbi", "sebi", "nse", "bse", "gst", "tds", "tcs",
}


@dataclass
class DetectedEntity:
    text: str
    label: str
    start: int
    end: int
    source: str  # "ner" or "regex"


def _matches_any_regex(text: str) -> bool:
    """Return True if *text* fully matches any configured regex pattern."""
    for pattern in REGEX_PATTERNS.values():
        if pattern.fullmatch(text):
            return True
    return False


def detect_ner_entities(text: str, nlp) -> list[DetectedEntity]:
    """Run spaCy NER and return entities matching SPACY_ENTITY_LABELS.

    Filters out:
    - Common acronyms that spaCy misidentifies (PAN, GSTIN, etc.)
    - Entities whose text fully matches a regex pattern (regex detector
      will provide a more specific label for those)
    - Very short entities (1-2 chars) that are likely noise
    """
    doc = nlp(text)
    entities: list[DetectedEntity] = []
    for ent in doc.ents:
        if ent.label_ not in SPACY_ENTITY_LABELS:
            continue
        # Skip very short entities
        if len(ent.text.strip()) <= 2:
            continue
        # Skip known false-positive words
        if ent.text.strip().lower() in _FALSE_POSITIVE_WORDS:
            continue
        # Skip if the text fully matches a regex pattern
        if _matches_any_regex(ent.text.strip()):
            continue

        entities.append(
            DetectedEntity(
                text=ent.text,
                label=ent.label_,
                start=ent.start_char,
                end=ent.end_char,
                source="ner",
            )
        )
    return entities
