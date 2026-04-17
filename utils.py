"""
Shared utilities: file-type detection, entity merging, mapping export.
"""

from __future__ import annotations

import os

from detectors.ner_detector import DetectedEntity


# ---------------------------------------------------------------------------
# File-type detection
# ---------------------------------------------------------------------------
EXTENSION_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".xlsx": "excel",
    ".xls": "excel",
    ".docx": "word",
    ".csv": "csv",
    ".txt": "text",
}


def detect_file_type(filename: str) -> str:
    """Return one of 'pdf', 'excel', 'word', 'csv', 'text' based on extension."""
    ext = os.path.splitext(filename)[1].lower()
    return EXTENSION_MAP.get(ext, "text")


# ---------------------------------------------------------------------------
# Entity merging
# ---------------------------------------------------------------------------
def merge_entity_lists(
    ner_entities: list[DetectedEntity],
    regex_entities: list[DetectedEntity],
) -> list[DetectedEntity]:
    """Merge NER + regex entities, deduplicating overlapping spans.

    Rules:
    - Prefer longer span when two spans overlap.
    - When spans are equal length, prefer regex label (more specific).
    """
    combined = ner_entities + regex_entities
    # Sort by start ascending, then by span length descending
    combined.sort(key=lambda e: (e.start, -(e.end - e.start)))

    merged: list[DetectedEntity] = []
    for ent in combined:
        if merged and ent.start < merged[-1].end:
            # Overlap — keep the one with the longer span
            prev = merged[-1]
            prev_len = prev.end - prev.start
            cur_len = ent.end - ent.start
            if cur_len > prev_len:
                merged[-1] = ent
            elif cur_len == prev_len and ent.source == "regex":
                merged[-1] = ent  # prefer regex label
        else:
            merged.append(ent)

    return merged
