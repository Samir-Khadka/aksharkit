"""A small, hand-curated Nepali stopword list.

Provenance: written by hand for this project from closed-class words only
(postpositions, particles, pronouns, conjunctions, auxiliaries). It was not
copied from any other package or corpus. It is deliberately short and is
awaiting native-speaker review; see ``docs/sources.md``.
"""

from __future__ import annotations

from collections.abc import Iterable

__all__ = ["STOPWORDS", "is_stopword", "remove_stopwords"]

STOPWORDS: frozenset[str] = frozenset(
    {
        # postpositions and case markers
        "को", "का", "की", "ले", "लाई", "मा", "बाट", "देखि", "सम्म", "सँग", "द्वारा", "तिर",
        "लागि", "भित्र", "बाहिर", "माथि", "तल", "अघि", "पछि", "बिना", "बारे",
        # particles
        "नै", "पनि", "त", "नि", "र", "रे", "चाहिँ", "मात्र", "झन्", "अझ",
        # conjunctions
        "तर", "वा", "कि", "अनि", "अथवा", "किनभने", "यदि", "भने", "त्यसैले", "तापनि",
        # pronouns and demonstratives
        "म", "हामी", "तिमी", "तपाईं", "ऊ", "उनी", "उहाँ", "यो", "त्यो", "यी", "ती",
        "यस", "त्यस", "यहाँ", "त्यहाँ", "के", "कुन", "जो", "जुन",
        "मेरो", "हाम्रो", "तिम्रो", "तपाईंको", "उसको", "उनको", "आफ्नो", "आफू",
        # auxiliaries and copulas
        "छ", "छन्", "छु", "छौँ", "छैन", "छैनन्", "हो", "होइन", "हुन्", "हुन्छ", "हुन्छन्",
        "थियो", "थिए", "थिएन", "भयो", "भए", "भएको", "गरेको", "रहेको",
        # quantifiers and misc.
        "एक", "एउटा", "धेरै", "केही", "सबै", "अरू", "अर्को", "यति", "त्यति", "कति",
        "अब", "अहिले", "फेरि", "त्यसपछि", "जस्तै", "जस्तो",
    }
)  # fmt: skip


def is_stopword(word: str) -> bool:
    """Return ``True`` if ``word`` is in :data:`STOPWORDS` (exact match)."""
    return word in STOPWORDS


def remove_stopwords(tokens: Iterable[str]) -> list[str]:
    """Return ``tokens`` without the stopwords, order preserved."""
    return [token for token in tokens if token not in STOPWORDS]
