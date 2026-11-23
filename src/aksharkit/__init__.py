"""aksharkit: typed, zero-dependency building blocks for Nepali text.

Implemented: Unicode normalisation, numerals, number words, tokenisation,
Bikram Sambat dates (BS 2000-2083) and transliteration (a reversible
IAST-style scheme and an approximate plain-ASCII one).
Stubbed (raises :class:`DataNotVerifiedError`): legacy-font conversion, until
its glyph table is verified.
"""

from __future__ import annotations

from ._errors import DataNotVerifiedError
from .dates import (
    BSDate,
    DateRangeError,
    DisputedDateError,
    ad_to_bs,
    bs_to_ad,
    fiscal_year,
    format_bs,
    parse_bs,
    today_bs,
)
from .normalize import normalize
from .numerals import format_number, parse_number, to_ascii_digits, to_devanagari_digits
from .stopwords import STOPWORDS, is_stopword, remove_stopwords
from .tokens import Token, sentences, tokenize, tokenize_spans
from .translit import to_devanagari, to_roman
from .words import currency_to_words, integer_to_words, number_to_words

__version__ = "0.3.0"

__all__ = [
    "STOPWORDS",
    "BSDate",
    "DataNotVerifiedError",
    "DateRangeError",
    "DisputedDateError",
    "Token",
    "__version__",
    "ad_to_bs",
    "bs_to_ad",
    "currency_to_words",
    "fiscal_year",
    "format_bs",
    "format_number",
    "integer_to_words",
    "is_stopword",
    "normalize",
    "number_to_words",
    "parse_bs",
    "parse_number",
    "remove_stopwords",
    "sentences",
    "to_ascii_digits",
    "to_devanagari",
    "to_devanagari_digits",
    "to_roman",
    "today_bs",
    "tokenize",
    "tokenize_spans",
]
