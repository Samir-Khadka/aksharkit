"""aksharkit: typed, zero-dependency building blocks for Nepali text.

Implemented: Unicode normalisation, numerals, number words, tokenisation.
Stubbed (raise :class:`DataNotVerifiedError`): legacy-font conversion and
Bikram Sambat dates, until their data tables are verified.
"""

from __future__ import annotations

from ._errors import DataNotVerifiedError
from .normalize import normalize
from .numerals import format_number, parse_number, to_ascii_digits, to_devanagari_digits
from .stopwords import STOPWORDS, is_stopword, remove_stopwords
from .tokens import Token, sentences, tokenize, tokenize_spans
from .words import currency_to_words, integer_to_words, number_to_words

__version__ = "0.1.0.dev0"

__all__ = [
    "STOPWORDS",
    "DataNotVerifiedError",
    "Token",
    "__version__",
    "currency_to_words",
    "format_number",
    "integer_to_words",
    "is_stopword",
    "normalize",
    "number_to_words",
    "parse_number",
    "remove_stopwords",
    "sentences",
    "to_ascii_digits",
    "to_devanagari_digits",
    "tokenize",
    "tokenize_spans",
]
