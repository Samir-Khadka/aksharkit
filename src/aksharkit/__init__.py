"""aksharkit: typed, zero-dependency building blocks for Nepali text.

Implemented: Unicode normalisation, numerals, number words in both
directions, tokenisation, script detection, Bikram Sambat dates and date
arithmetic (BS 2000-2083) and transliteration (a reversible IAST-style
scheme and an approximate plain-ASCII one).
Stubbed (raises :class:`DataNotVerifiedError`): legacy-font conversion, until
its glyph table is verified.
"""

from __future__ import annotations

from ._errors import DataNotVerifiedError
from .dates import (
    BSDate,
    BSDifference,
    DateRangeError,
    DisputedDateError,
    ad_to_bs,
    add_days,
    add_months,
    age,
    bs_to_ad,
    days_between,
    days_in_month,
    difference,
    fiscal_year,
    format_bs,
    format_month_calendar,
    month_calendar,
    parse_bs,
    today_bs,
)
from .detect import (
    detect_script,
    looks_romanised_nepali,
    romanised_nepali_score,
    script_counts,
    script_shares,
    token_scripts,
)
from .normalize import normalize
from .numerals import format_number, parse_number, to_ascii_digits, to_devanagari_digits
from .stopwords import STOPWORDS, is_stopword, remove_stopwords
from .tokens import Token, sentences, tokenize, tokenize_spans
from .translit import to_devanagari, to_roman
from .words import currency_to_words, integer_to_words, number_to_words, parse_words

__version__ = "0.4.0"

__all__ = [
    "STOPWORDS",
    "BSDate",
    "BSDifference",
    "DataNotVerifiedError",
    "DateRangeError",
    "DisputedDateError",
    "Token",
    "__version__",
    "ad_to_bs",
    "add_days",
    "add_months",
    "age",
    "bs_to_ad",
    "currency_to_words",
    "days_between",
    "days_in_month",
    "detect_script",
    "difference",
    "fiscal_year",
    "format_bs",
    "format_month_calendar",
    "format_number",
    "integer_to_words",
    "is_stopword",
    "looks_romanised_nepali",
    "month_calendar",
    "normalize",
    "number_to_words",
    "parse_bs",
    "parse_number",
    "parse_words",
    "remove_stopwords",
    "romanised_nepali_score",
    "script_counts",
    "script_shares",
    "sentences",
    "to_ascii_digits",
    "to_devanagari",
    "to_devanagari_digits",
    "to_roman",
    "today_bs",
    "token_scripts",
    "tokenize",
    "tokenize_spans",
]
