"""
EntityRegistry — maintains a consistent pseudonym mapping across a session.

Every unique (entity_type, normalised_text) pair gets a stable pseudonym.
The mapping can be exported as CSV or JSON for reversal.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field

from config import PSEUDONYM_TEMPLATES


@dataclass
class EntityRegistry:
    _map: dict[tuple[str, str], str] = field(default_factory=dict)
    _originals: dict[tuple[str, str], str] = field(default_factory=dict)  # first-seen casing
    _counters: dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    def get_pseudonym(self, entity_type: str, original: str) -> str:
        """Return a consistent pseudonym for *original* under *entity_type*."""
        key = (entity_type, original.strip().lower())
        if key in self._map:
            return self._map[key]

        # Assign next counter for this type
        n = self._counters.get(entity_type, 0) + 1
        self._counters[entity_type] = n

        template = PSEUDONYM_TEMPLATES.get(entity_type, f"{entity_type}-{{n}}")
        pseudonym = template.format(n=n)

        self._map[key] = pseudonym
        self._originals[key] = original.strip()  # preserve first-seen casing
        return pseudonym

    @property
    def mapping_table(self) -> list[dict[str, str]]:
        """Return list of {original, pseudonym, type} dicts."""
        rows = []
        for (etype, _norm), pseudonym in self._map.items():
            rows.append(
                {
                    "original": self._originals[(etype, _norm)],
                    "pseudonym": pseudonym,
                    "type": etype,
                }
            )
        return rows

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------
    def to_csv_bytes(self) -> bytes:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["original", "pseudonym", "type"])
        writer.writeheader()
        writer.writerows(self.mapping_table)
        return buf.getvalue().encode("utf-8")

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.mapping_table, indent=2, ensure_ascii=False).encode("utf-8")

    # ------------------------------------------------------------------
    # Reverse lookup
    # ------------------------------------------------------------------
    @property
    def reverse_map(self) -> dict[str, str]:
        """pseudonym → original (first-seen casing)."""
        return {v: self._originals[k] for k, v in self._map.items()}

    def __len__(self) -> int:
        return len(self._map)
