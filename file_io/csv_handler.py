"""CSV file handler using pandas."""

from __future__ import annotations

import io

import pandas as pd

from entity_registry import EntityRegistry


def read_csv(file_bytes: bytes) -> tuple[pd.DataFrame, str]:
    """Return (dataframe, full_text_for_detection)."""
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, keep_default_na=False)
    except UnicodeDecodeError:
        df = pd.read_csv(
            io.BytesIO(file_bytes), dtype=str, keep_default_na=False, encoding="latin-1"
        )
    full_text = "\n".join(
        df.astype(str).apply(lambda row: " ".join(row), axis=1)
    )
    return df, full_text


def write_csv(
    df: pd.DataFrame,
    registry: EntityRegistry,
    skip_entities: set[str] | None = None,
) -> bytes:
    """Replace all mapped entities in every cell and return CSV bytes."""
    if skip_entities is None:
        skip_entities = set()

    mapping = {
        row["original"]: row["pseudonym"]
        for row in registry.mapping_table
        if row["original"] not in skip_entities
    }

    def _replace_cell(val: str) -> str:
        for orig, pseudo in mapping.items():
            val = val.replace(orig, pseudo)
        return val

    df_anon = df.astype(str).map(_replace_cell)
    buf = io.BytesIO()
    df_anon.to_csv(buf, index=False, encoding="utf-8")
    return buf.getvalue()
