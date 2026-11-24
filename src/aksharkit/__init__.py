"""aksharkit: typed, zero-dependency building blocks for Nepali text.

Implemented: Unicode normalisation, akshara (written syllable) segmentation,
alphabetical sorting, numerals, number words in both directions, ordinals,
tokenisation, script detection, Bikram Sambat dates with formatting, parsing
and arithmetic (BS 2000-2083) and transliteration (a reversible IAST-style
scheme and an approximate plain-ASCII one).
Experimental: Preeti legacy-font text to Unicode and back, in plain text and
in Word (.docx) files. Its key table is agreed between permissively-licensed
tables but has not been checked against real Preeti documents; characters
with no agreed entry are reported, not guessed.
"""

from __future__ import annotations

from ._errors import DataNotVerifiedError
from .akshara import Akshara, akshara_count, akshara_spans, aksharas, truncate
from .collate import sort_key, sorted_nepali
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
from .legacy import (
    ForeignSpan,
    PreetiEncodeResult,
    PreetiEncodeStats,
    PreetiResult,
    PreetiSegment,
    PreetiStats,
    UnmappedChar,
    convert_preeti,
    encode_preeti,
    preeti_to_unicode,
    unicode_to_preeti,
)
from .legacy_docx import (
    DocxEncodeReport,
    DocxLeft,
    DocxReport,
    convert_docx,
    convert_docx_bytes,
    encode_docx,
    encode_docx_bytes,
)
from .normalize import normalize
from .numerals import format_number, parse_number, to_ascii_digits, to_devanagari_digits
from .stopwords import STOPWORDS, is_stopword, remove_stopwords
from .tokens import Token, sentences, tokenize, tokenize_spans
from .translit import to_devanagari, to_roman
from .words import (
    currency_to_words,
    integer_to_words,
    number_to_words,
    ordinal_to_words,
    parse_words,
)

__version__ = "0.8.0"

__all__ = [
    "STOPWORDS",
    "Akshara",
    "BSDate",
    "BSDifference",
    "DataNotVerifiedError",
    "DateRangeError",
    "DisputedDateError",
    "DocxEncodeReport",
    "DocxLeft",
    "DocxReport",
    "ForeignSpan",
    "PreetiEncodeResult",
    "PreetiEncodeStats",
    "PreetiResult",
    "PreetiSegment",
    "PreetiStats",
    "Token",
    "UnmappedChar",
    "__version__",
    "ad_to_bs",
    "add_days",
    "add_months",
    "age",
    "akshara_count",
    "akshara_spans",
    "aksharas",
    "bs_to_ad",
    "convert_docx",
    "convert_docx_bytes",
    "convert_preeti",
    "currency_to_words",
    "days_between",
    "days_in_month",
    "detect_script",
    "difference",
    "encode_docx",
    "encode_docx_bytes",
    "encode_preeti",
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
    "ordinal_to_words",
    "parse_bs",
    "parse_number",
    "parse_words",
    "preeti_to_unicode",
    "remove_stopwords",
    "romanised_nepali_score",
    "script_counts",
    "script_shares",
    "sentences",
    "sort_key",
    "sorted_nepali",
    "to_ascii_digits",
    "to_devanagari",
    "to_devanagari_digits",
    "to_roman",
    "today_bs",
    "token_scripts",
    "tokenize",
    "tokenize_spans",
    "truncate",
    "unicode_to_preeti",
]
