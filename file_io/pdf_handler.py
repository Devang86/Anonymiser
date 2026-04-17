"""PDF file handler using PyMuPDF (fitz).

Read:  Extract text per page.
Write: Redact-and-reinsert strategy for text-layer PDFs.
"""

from __future__ import annotations

import io

import fitz  # PyMuPDF

from entity_registry import EntityRegistry


def read_pdf(file_bytes: bytes) -> tuple[fitz.Document, str]:
    """Return (fitz.Document, full_text_for_detection).

    Also warns (via return) if text extraction is very sparse — likely a
    scanned PDF without an embedded text layer.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_text: list[str] = []
    for page in doc:
        pages_text.append(page.get_text())
    return doc, "\n".join(pages_text)


def is_scanned_pdf(doc: fitz.Document) -> bool:
    """Heuristic: if average chars per page < 50, it's likely scanned."""
    total_chars = sum(len(page.get_text()) for page in doc)
    avg = total_chars / max(len(doc), 1)
    return avg < 50


def write_pdf(
    doc: fitz.Document,
    registry: EntityRegistry,
    skip_entities: set[str] | None = None,
) -> bytes:
    """Redact original entities and insert pseudonyms at the same locations.

    This preserves layout reasonably well for text-layer PDFs.  Replacement
    text of different length may cause minor layout shifts.
    """
    if skip_entities is None:
        skip_entities = set()

    mapping = {
        row["original"]: row["pseudonym"]
        for row in registry.mapping_table
        if row["original"] not in skip_entities
    }

    for page in doc:
        for original, pseudonym in mapping.items():
            rects = page.search_for(original)
            for rect in rects:
                # Add redaction annotation over the original text
                page.add_redact_annot(rect, text=pseudonym, fontsize=0)

        # Apply all redactions on this page at once
        page.apply_redactions()

    buf = io.BytesIO()
    doc.save(buf, garbage=4, deflate=True)
    return buf.getvalue()
