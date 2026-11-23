"""Loading and validating bundled data tables.

A table is a JSON file with a ``status`` field. Only ``"verified"`` tables
may be used; anything else raises :class:`DataNotVerifiedError`, so a
half-filled or guessed table can never silently produce wrong output.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from ._errors import DataNotVerifiedError

__all__ = ["VERIFIED", "load_table", "require_verified"]

VERIFIED = "verified"


def load_table(name: str) -> dict[str, Any]:
    """Read ``data/<name>.json`` from the installed package."""
    raw = (resources.files("aksharkit") / "data" / f"{name}.json").read_text("utf-8")
    table = json.loads(raw)
    if not isinstance(table, dict) or "status" not in table:
        raise ValueError(f"data table {name!r} is malformed: missing 'status'")
    return table


def require_verified(table: dict[str, Any], feature: str, payload_key: str) -> Any:
    """Return ``table[payload_key]`` if the table is verified and non-empty."""
    status = table.get("status")
    payload = table.get(payload_key)
    if status != VERIFIED or not payload:
        raise DataNotVerifiedError(
            f"{feature} is not available yet: its data table has status "
            f"{status!r}. The table must be filled from a trusted source and "
            "reviewed before this feature is switched on. See docs/sources.md."
        )
    if not table.get("sources"):
        raise DataNotVerifiedError(
            f"{feature}: the data table is marked verified but lists no sources"
        )
    return payload
