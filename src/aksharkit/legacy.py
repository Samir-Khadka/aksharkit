"""Legacy (pre-Unicode) Nepali font conversion. NOT IMPLEMENTED YET.

Fonts such as Preeti, Kantipur, Himali and Sagarmatha draw Devanagari shapes
on ASCII key positions, so ``g]kfn`` on disk displays as ``नेपाल``. Converting
needs (1) an exact per-font glyph table and (2) reordering rules, for
example moving the short-i sign that legacy text stores *before* its
consonant.

The glyph tables live in ``data/font_<name>.json`` and are currently empty.
They will not be guessed and will not be copied from projects whose licence
does not allow it. Until a table is verified, every function here raises
:class:`aksharkit.DataNotVerifiedError`.
"""

from __future__ import annotations

from ._data import load_table, require_verified

__all__ = [
    "SUPPORTED_FONTS",
    "load_font_map",
    "preeti_to_unicode",
    "to_unicode",
    "unicode_to_preeti",
]

#: Fonts with a data file in the package (verified or not).
SUPPORTED_FONTS: tuple[str, ...] = ("preeti",)


def load_font_map(font: str) -> dict[str, str]:
    """Return the verified glyph map for ``font``.

    Raises :class:`aksharkit.DataNotVerifiedError` while the table is empty
    or unverified, and :class:`ValueError` for a font with no data file.
    """
    key = font.strip().lower()
    if key not in SUPPORTED_FONTS:
        raise ValueError(f"unknown font {font!r}; known fonts: {', '.join(SUPPORTED_FONTS)}")
    table = load_table(f"font_{key}")
    mapping = require_verified(table, f"{key.title()} conversion", "mapping")
    if not isinstance(mapping, dict):
        raise ValueError(f"font table for {font!r} is malformed: 'mapping' must be an object")
    return {str(k): str(v) for k, v in mapping.items()}


def to_unicode(text: str, font: str = "preeti") -> str:
    """Convert legacy-font ``text`` to Unicode. Not implemented yet."""
    load_font_map(font)
    raise NotImplementedError(  # pragma: no cover - reachable only with verified data
        "the reordering rules for legacy-font conversion are not implemented yet"
    )


def preeti_to_unicode(text: str) -> str:
    """Convert Preeti-encoded ``text`` to Unicode. Not implemented yet."""
    return to_unicode(text, "preeti")


def unicode_to_preeti(text: str) -> str:
    """Convert Unicode ``text`` to Preeti key codes. Not implemented yet."""
    load_font_map("preeti")
    raise NotImplementedError(  # pragma: no cover - reachable only with verified data
        "Unicode to Preeti conversion is not implemented yet"
    )
