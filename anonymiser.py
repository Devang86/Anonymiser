"""
Text anonymisation engine.

Two-pass approach:
  1. Offset-based replacement (end→start to preserve positions).
  2. Global str.replace sweep for every known mapping (catches occurrences NER missed).
"""

from __future__ import annotations

from detectors.ner_detector import DetectedEntity
from entity_registry import EntityRegistry


def anonymise_text(
    text: str,
    entities: list[DetectedEntity],
    registry: EntityRegistry,
    skip_entities: set[str] | None = None,
) -> str:
    """Replace detected entities in *text* with consistent pseudonyms.

    Parameters
    ----------
    text : str
        The source text.
    entities : list[DetectedEntity]
        Entities detected in *text* (with char offsets).
    registry : EntityRegistry
        Shared pseudonym registry for this session.
    skip_entities : set[str] | None
        Entity texts the user has chosen NOT to anonymise.

    Returns
    -------
    str
        Anonymised text.
    """
    if skip_entities is None:
        skip_entities = set()

    # --- Pass 1: offset-based replacement (back-to-front) -----------------
    # Sort descending by start so replacements don't shift earlier offsets
    sorted_ents = sorted(entities, key=lambda e: e.start, reverse=True)

    for ent in sorted_ents:
        if ent.text in skip_entities:
            continue
        pseudonym = registry.get_pseudonym(ent.label, ent.text)
        text = text[: ent.start] + pseudonym + text[ent.end :]

    # --- Pass 2: global sweep for consistency ----------------------------
    # Some occurrences may not have been tagged by NER/regex.  Walk the
    # full mapping and replace any remaining originals.
    for row in registry.mapping_table:
        original = row["original"]
        pseudonym = row["pseudonym"]
        if original in skip_entities:
            continue
        if original in text:
            text = text.replace(original, pseudonym)

    return text
