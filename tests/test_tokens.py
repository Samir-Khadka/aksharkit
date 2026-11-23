from __future__ import annotations

import pytest

from aksharkit import (
    STOPWORDS,
    Token,
    is_stopword,
    remove_stopwords,
    sentences,
    tokenize,
    tokenize_spans,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("म घर जान्छु।", ["म", "घर", "जान्छु", "।"]),
        ("नेपालको जनसंख्या २,९१,६४,५७८ छ।", ["नेपालको", "जनसंख्या", "२,९१,६४,५७८", "छ", "।"]),
        ("रु. १,२३४.५०", ["रु", ".", "१,२३४.५०"]),
        ("१२, १३ र १४", ["१२", ",", "१३", "र", "१४"]),
        ("3.14 र ३.१४", ["3.14", "र", "३.१४"]),
        ("Facebookमा पोस्ट", ["Facebook", "मा", "पोस्ट"]),
        ("२०८०मा", ["२०८०", "मा"]),
        ("don't stop", ["don't", "stop"]),
        ("well-known fact", ["well-known", "fact"]),
        ("आ-आफ्नो", ["आ", "-", "आफ्नो"]),
        ("(नेपाल)", ["(", "नेपाल", ")"]),
        ("“नमस्ते”", ["“", "नमस्ते", "”"]),
        ("र्\u200dयाल थर", ["र्\u200dयाल", "थर"]),
        ("डा॰ शर्मा", ["डा॰", "शर्मा"]),
        ("ॐ शान्ति॥", ["ॐ", "शान्ति", "॥"]),
        ("www.example.com।", ["www.example.com", "।"]),
        (
            "हेर्नुहोस् https://samir-khadka.com.np/projects.",
            [
                "हेर्नुहोस्",
                "https://samir-khadka.com.np/projects",
                ".",
            ],
        ),
        ("इमेल info@example.com.np मा", ["इमेल", "info@example.com.np", "मा"]),
        ("50% छुट", ["50", "%", "छुट"]),
        ("5G नेटवर्क", ["5", "G", "नेटवर्क"]),
        ("२०८०-०१-१५", ["२०८०", "-", "०१", "-", "१५"]),
        ("हेल्लो😀", ["हेल्लो", "😀"]),
        ("a\tb\nc", ["a", "b", "c"]),
        ("के छ?!", ["के", "छ", "?", "!"]),
        ("हुँदैन, गर्दिनँ; आउँछु", ["हुँदैन", ",", "गर्दिनँ", ";", "आउँछु"]),
        ("क्षत्रिय ज्ञान श्रद्धा", ["क्षत्रिय", "ज्ञान", "श्रद्धा"]),
        ("café मा", ["café", "मा"]),
        ("", []),
        ("   \n ", []),
        ("।", ["।"]),
    ],
)
def test_tokenize(text: str, expected: list[str]) -> None:
    assert tokenize(text) == expected


SAMPLES = [
    "नेपालको जनसंख्या २,९१,६४,५७८ छ। Facebookमा 3.5% छ?",
    "  अगाडि खाली ठाउँ   र पछाडि  ",
    "इमेल a@b.com, साइट https://x.com/y?z=1).",
    "रु. १,२३४.५० मात्र — ठिक छ!",
    "mixed English र नेपाली text 123 १२३",
]


@pytest.mark.parametrize("text", SAMPLES)
def test_spans_point_back_into_the_source(text: str) -> None:
    spans = tokenize_spans(text)
    assert spans, text
    previous_end = 0
    for token in spans:
        assert isinstance(token, Token)
        assert text[token.start : token.end] == token.text
        assert token.start >= previous_end
        assert text[previous_end : token.start].strip() == ""  # only whitespace is skipped
        assert not token.text.isspace()
        previous_end = token.end
    assert text[previous_end:].strip() == ""
    assert "".join(t.text for t in spans) == "".join(text.split())


@pytest.mark.parametrize(
    ("text", "kinds"),
    [
        ("नेपाल Nepal १२ 12 । a@b.co https://x.y",
         ["word", "latin", "number", "number", "punct", "email", "url"]),
        ("१,२३४.५ %", ["number", "punct"]),
    ],
)  # fmt: skip
def test_token_kinds(text: str, kinds: list[str]) -> None:
    assert [t.kind for t in tokenize_spans(text)] == kinds


def test_token_is_frozen() -> None:
    token = tokenize_spans("क")[0]
    with pytest.raises(AttributeError):
        token.text = "ख"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("म घर जान्छु। तिमी कहाँ जान्छौ?", ["म घर जान्छु।", "तिमी कहाँ जान्छौ?"]),
        ("ऊ आयो।उसले भन्यो।", ["ऊ आयो।", "उसले भन्यो।"]),
        ("के छ? ठिक छ!", ["के छ?", "ठिक छ!"]),
        ("ॐ शान्ति॥ शान्ति॥", ["ॐ शान्ति॥", "शान्ति॥"]),
        ("डा. राम आए। उनी गए।", ["डा. राम आए।", "उनी गए।"]),
        ("वि.सं. २०८० मा भूकम्प गयो।", ["वि.सं. २०८० मा भूकम्प गयो।"]),
        ("गा.वि.स. को बैठक बस्यो।", ["गा.वि.स. को बैठक बस्यो।"]),
        ("नं. ५ मा बस्छु।", ["नं. ५ मा बस्छु।"]),
        ("मूल्य रु. 99.50 हो।", ["मूल्य रु. 99.50 हो।"]),
        ("मिति २०८०.०१.१५ हो।", ["मिति २०८०.०१.१५ हो।"]),
        ("पाई ३.१४ हो। ई २.७१ हो।", ["पाई ३.१४ हो।", "ई २.७१ हो।"]),
        ("ठिक छ. भोलि भेटौँला.", ["ठिक छ.", "भोलि भेटौँला."]),
        ("example.com मा जानुहोस्।", ["example.com मा जानुहोस्।"]),
        ("के भयो?! थाहा छैन...", ["के भयो?!", "थाहा छैन..."]),
        ("पर्खनुहोस्... म आउँदैछु।", ["पर्खनुहोस्...", "म आउँदैछु।"]),
        ('उसले भन्यो, "म जान्छु।" अनि गयो।', ['उसले भन्यो, "म जान्छु।"', "अनि गयो।"]),
        ("(यो सत्य हो।) अर्को कुरा।", ["(यो सत्य हो।)", "अर्को कुरा।"]),
        ("1. पहिलो बुँदा। 2. दोस्रो बुँदा।", ["1. पहिलो बुँदा।", "2. दोस्रो बुँदा।"]),
        ("१. पहिलो। २. दोस्रो।", ["१. पहिलो।", "२. दोस्रो।"]),
        ("पहिलो हरफ।\nदोस्रो हरफ।", ["पहिलो हरफ।", "दोस्रो हरफ।"]),
        ("अन्त्यमा विराम छैन", ["अन्त्यमा विराम छैन"]),
        ("नमस्ते", ["नमस्ते"]),
        ("", []),
        ("   ", []),
        ("।", ["।"]),
        ("Dr. Sharma came. He left.", ["Dr. Sharma came.", "He left."]),
        (
            "B. P. Koirala was born in 1914. He wrote.",
            [
                "B. P. Koirala was born in 1914.",
                "He wrote.",
            ],
        ),
        ("He paid Rs. 500. Then he left.", ["He paid Rs. 500.", "Then he left."]),
        ('He said "stop." Then left.', ['He said "stop."', "Then left."]),
        ("3.14 is pi. 2.71 is e.", ["3.14 is pi.", "2.71 is e."]),
        ("wait... what happened", ["wait... what happened"]),
        ("Use e.g. this one. Done.", ["Use e.g. this one.", "Done."]),
        ("The end.\nNew line", ["The end.", "New line"]),
        (
            "म Kathmandu गएँ। It was fun. फेरि जान्छु!",
            [
                "म Kathmandu गएँ।",
                "It was fun.",
                "फेरि जान्छु!",
            ],
        ),
        (
            "Mr. and Mrs. Thapa arrived etc. Then dinner.",
            [
                "Mr. and Mrs. Thapa arrived etc. Then dinner.",
            ],
        ),
    ],
)
def test_sentences(text: str, expected: list[str]) -> None:
    assert sentences(text) == expected


@pytest.mark.parametrize("text", SAMPLES)
def test_sentences_lose_nothing_but_spacing(text: str) -> None:
    assert "".join("".join(s.split()) for s in sentences(text)) == "".join(text.split())


def test_stopwords_basics() -> None:
    assert len(STOPWORDS) >= 100
    assert all(word == word.strip() and " " not in word for word in STOPWORDS)
    assert is_stopword("को") and is_stopword("छ") and is_stopword("र")
    assert not is_stopword("नेपाल") and not is_stopword("")


def test_remove_stopwords_keeps_order() -> None:
    tokens = tokenize("नेपाल एक सुन्दर देश हो र यहाँ धेरै हिमाल छन्।")
    assert remove_stopwords(tokens) == ["नेपाल", "सुन्दर", "देश", "हिमाल", "।"]
    assert remove_stopwords([]) == []
