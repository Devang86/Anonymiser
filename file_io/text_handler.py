"""Plain-text file handler."""

from __future__ import annotations


def read_text(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def write_text(anonymised_text: str) -> bytes:
    return anonymised_text.encode("utf-8")
