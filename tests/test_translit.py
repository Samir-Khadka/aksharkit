from __future__ import annotations

import random
import unicodedata
from pathlib import Path

import pytest

import aksharkit
from aksharkit import to_devanagari, to_roman, translit
from aksharkit.cli import main

VIRAMA = "\u094d"
NUKTA = "\u093c"

CONSONANTS = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ"
NUKTA_LETTERS = [c + NUKTA for c in "कखगजडढफय"]
ALL_CONSONANTS = [*CONSONANTS, *NUKTA_LETTERS]
VOWELS = "अआइईउऊऋॠएऐओऔ"
MATRAS = "ािीुूृॄेैोौ"
MARKS = "\u0902\u0901\u0903"  # anusvara, candrabindu, visarga

GOLDEN = Path(__file__).parent / "golden" / "translit_words.tsv"


def _golden() -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for line in GOLDEN.read_text("utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        dev, iast, simple, review, note = line.split("\t")
        rows.append((dev, iast, simple, review, note))
    return rows


ROWS = _golden()


def roundtrip(text: str) -> str:
    return to_devanagari(to_roman(text, "iast"), "iast")


# --- tables ------------------------------------------------------------------


def test_tables_cover_the_basic_devanagari_letters() -> None:
    assert len(CONSONANTS) == 34
    assert set(CONSONANTS) == set(translit._CONSONANTS_IAST)
    assert set(CONSONANTS) == set(translit._CONSONANTS_SIMPLE)
    assert set(VOWELS) == set(translit._VOWELS_IAST) == set(translit._VOWELS_SIMPLE)
    assert set(MATRAS) == set(translit._MATRAS_IAST) == set(translit._MATRAS_SIMPLE)


def test_iast_romanisations_are_unique() -> None:
    romans = [
        *translit._CONSONANTS_IAST.values(),
        *translit._NUKTA_IAST.values(),
        *translit._VOWELS_IAST.values(),
        *translit._MARKS_IAST.values(),
    ]
    assert len(romans) == len(set(romans))
    assert all(r == unicodedata.normalize("NFC", r) for r in romans)


def test_iast_output_is_lower_case_nfc_and_free_of_devanagari_letters() -> None:
    text = "".join(c + m for c in ALL_CONSONANTS for m in MATRAS) + VOWELS + "कं कँ कः"
    out = to_roman(text)
    assert out == unicodedata.normalize("NFC", out)
    assert out == out.lower()
    assert not any("\u0900" <= ch <= "\u097f" for ch in out)


def test_simple_output_is_plain_ascii() -> None:
    text = " ".join(c + m for c in ALL_CONSONANTS for m in ("", *MATRAS))
    text += " " + " ".join(VOWELS) + " कं कँ कः गङ्गा ज्ञान। २०८३ ॥"
    assert to_roman(text, "simple").isascii()


# --- iast: exact values --------------------------------------------------------


@pytest.mark.parametrize(
    ("dev", "roman"),
    [
        ("क", "ka"),
        ("का", "kā"),
        ("कि", "ki"),
        ("की", "kī"),
        ("कु", "ku"),
        ("कू", "kū"),
        ("कृ", "kṛ"),
        ("के", "ke"),
        ("कै", "kai"),
        ("को", "ko"),
        ("कौ", "kau"),
        ("क्", "k"),
        ("कं", "kaṃ"),
        ("कँ", "kam\u0310"),
        ("कः", "kaḥ"),
        ("ङ", "ṅa"),
        ("ञ", "ña"),
        ("च", "ca"),
        ("छ", "cha"),
        ("श", "śa"),
        ("ष", "ṣa"),
        ("ण", "ṇa"),
        ("ट", "ṭa"),
        ("ठ", "ṭha"),
        ("ड", "ḍa"),
        ("ढ", "ḍha"),
        ("क्ष", "kṣa"),
        ("त्र", "tra"),
        ("ज्ञ", "jña"),
        ("श्र", "śra"),
        ("द्ध", "ddha"),
        ("अ आ इ ई उ ऊ ऋ ए ऐ ओ औ", "a ā i ī u ū ṛ e ai o au"),
        ("राम घर गयो।", "rāma ghara gayo|"),
        ("ॐ शान्ति ॥", "ॐ śānti ||"),
        ("२०८३ साल", "2083 sāla"),
        ("सोऽहम्", "so'ham"),
        ("", ""),
    ],
)
def test_iast_values(dev: str, roman: str) -> None:
    assert to_roman(dev) == roman
    assert to_devanagari(roman) == dev


@pytest.mark.parametrize(
    ("dev", "roman"),
    [
        ("कइ", "ka:i"),  # not कै
        ("कउ", "ka:u"),  # not कौ
        ("अइ", "a:i"),  # not ऐ
        ("अउ", "a:u"),  # not औ
        ("क्ह", "k:ha"),  # not ख
        ("त्ह", "t:ha"),  # not थ
        ("ड़्ह", "ṙ:ha"),  # not ढ़
        ("क्अ", "k:a"),  # halant then an independent vowel, not क
        ("क्आ", "k:ā"),  # not का
        ("राम: श्याम", "rāma: śyāma"),  # a real colon before a space is left alone
        ("क:ख", "ka::kha"),  # a real colon between letters is doubled
        ("क::ख", "ka:::kha"),
    ],
)
def test_iast_separator_keeps_ambiguous_sequences_apart(dev: str, roman: str) -> None:
    assert to_roman(dev) == roman
    assert to_devanagari(roman) == dev


def test_iast_accepts_capitals_and_iso_anusvara() -> None:
    assert to_devanagari("Nepāla") == "नेपाल"
    assert to_devanagari("KṚṢṆA") == "कृष्ण"
    assert to_devanagari("saṁsāra") == "संसार"


def test_iast_passes_unknown_characters_through() -> None:
    assert to_roman("क, ख! (ग) — घ?") == "ka, kha! (ga) — gha?"
    assert to_devanagari("ka, kha! (ga) — gha?") == "क, ख! (ग) — घ?"


def test_digits_can_be_left_alone() -> None:
    assert to_roman("२०८३", digits=False) == "२०८३"
    assert to_devanagari("2083", digits=False) == "2083"
    assert to_roman("२०८३", "simple", digits=False) == "२०८३"
    assert to_devanagari("2083", "simple", digits=False) == "2083"
    assert to_devanagari("2083") == "२०८३"


def test_precomposed_nukta_letters_are_normalised_first() -> None:
    assert to_roman("\u0958\u093e") == "qā"  # U+0958 QA
    assert to_roman("\u095b") == "za"
    assert roundtrip("\u095e\u094b\u0928") == "फ़ोन"


# --- iast: exhaustive round trips ---------------------------------------------


@pytest.mark.parametrize("consonant", ALL_CONSONANTS)
def test_iast_roundtrip_every_vowel_sign_and_mark(consonant: str) -> None:
    for tail in ("", VIRAMA, *MATRAS):
        for mark in ("", *MARKS):
            text = consonant + tail + mark
            assert roundtrip(text) == text, text
            # ... and inside a word, after and before other letters
            word = "न" + text + "म"
            assert roundtrip(word) == word, word


@pytest.mark.parametrize("first", ALL_CONSONANTS)
def test_iast_roundtrip_every_two_consonant_conjunct(first: str) -> None:
    for second in ALL_CONSONANTS:
        for tail in ("", VIRAMA, "ा", "ि", "ै", "ौ"):
            text = first + VIRAMA + second + tail
            assert roundtrip(text) == text, text


@pytest.mark.parametrize("first", ALL_CONSONANTS)
def test_iast_roundtrip_every_consonant_pair_without_conjunct(first: str) -> None:
    for second in ALL_CONSONANTS:
        text = first + second
        assert roundtrip(text) == text, text


@pytest.mark.parametrize("vowel", VOWELS)
def test_iast_roundtrip_every_vowel_in_every_position(vowel: str) -> None:
    for mark in ("", *MARKS):
        assert roundtrip(vowel + mark) == vowel + mark
    for other in VOWELS:
        assert roundtrip(vowel + other) == vowel + other
    for consonant in ALL_CONSONANTS:
        for text in (
            vowel + consonant,
            consonant + vowel,
            consonant + VIRAMA + vowel,
            consonant + "ा" + vowel,
        ):
            assert roundtrip(text) == text, text


@pytest.mark.parametrize(
    "text",
    [
        "स्त्री",
        "राष्ट्र",
        "कार्त्स्न्य",
        "उज्ज्वल",
        "लक्ष्म्य",
        "सङ्ख्या",
        "द्वन्द्व",
        "श्रृङ्खला",
        "क्\u200dष",  # with ZWJ
        "र्\u200dय",
        "श्\u200cव",  # with ZWNJ
        "ह्रस्व",
        "विद्वत्त्व",
        "ऑफिस कॉलेज",  # letters outside the scheme pass through
    ],
)
def test_iast_roundtrip_harder_conjuncts(text: str) -> None:
    assert roundtrip(text) == text


def _random_word(rng: random.Random) -> str:
    parts: list[str] = []
    for _ in range(rng.randint(1, 6)):
        if rng.random() < 0.2:
            parts.append(rng.choice(VOWELS))
        else:
            parts.append(rng.choice(ALL_CONSONANTS))
            while rng.random() < 0.3:
                parts.append(VIRAMA + rng.choice(ALL_CONSONANTS))
            roll = rng.random()
            if roll < 0.5:
                parts.append(rng.choice(MATRAS))
            elif roll < 0.6:
                parts.append(VIRAMA)
        if rng.random() < 0.15:
            parts.append(rng.choice(MARKS))
    return "".join(parts)


@pytest.mark.parametrize("seed", range(20))
def test_iast_roundtrip_random_well_formed_text(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(500):
        words = [_random_word(rng) for _ in range(rng.randint(1, 5))]
        text = rng.choice([" ", ", ", "। ", ": ", ":", "-", " २ "]).join(words)
        text = unicodedata.normalize("NFC", text)
        assert roundtrip(text) == text, text


def test_iast_roundtrip_a_paragraph() -> None:
    text = (
        "नेपाल दक्षिण एसियामा अवस्थित एक भूपरिवेष्ठित देश हो। यसको राजधानी काठमाडौँ हो। "
        "सगरमाथा विश्वको सर्वोच्च शिखर हो; यसको उचाइ ८,८४८.८६ मिटर छ। के तपाईं यहाँ आउनुभएको छ?"
    )
    assert roundtrip(text) == text


# --- hand-written word list -----------------------------------------------------


def test_golden_file_is_well_formed() -> None:
    assert len(ROWS) >= 100
    assert len({row[0] for row in ROWS}) == len(ROWS)
    for dev, iast, simple, review, note in ROWS:
        assert review in ("yes", "no"), dev
        assert simple.isascii() and simple == simple.lower(), dev
        assert iast == unicodedata.normalize("NFC", iast), dev
        assert review == "no" or note, f"{dev}: a review row needs a note"


@pytest.mark.parametrize(("dev", "iast"), [(r[0], r[1]) for r in ROWS])
def test_golden_iast(dev: str, iast: str) -> None:
    assert to_roman(dev, "iast") == iast
    assert to_devanagari(iast, "iast") == unicodedata.normalize("NFC", dev)


@pytest.mark.parametrize(("dev", "simple"), [(r[0], r[2]) for r in ROWS])
def test_golden_simple(dev: str, simple: str) -> None:
    assert to_roman(dev, "simple") == simple


def test_required_examples_are_in_the_golden_list() -> None:
    words = {row[0] for row in ROWS}
    assert {"नेपाल", "काठमाडौँ", "नमस्ते", "धन्यवाद"} <= words


# --- simple: Devanagari -> Roman rules -------------------------------------------


@pytest.mark.parametrize(
    ("dev", "simple"),
    [
        ("म घर जान्छु।", "ma ghar janchhu."),
        ("नेपाल राम्रो छ। २०८३", "nepal ramro chha. 2083"),
        ("के छ? ठिक छ!", "ke chha? thik chha!"),
        ("अंक", "anka"),  # anusvara before a velar, final a kept
        ("सम्म", "samma"),
        ("पम्प", "pampa"),
        ("संबन्ध", "sambandha"),  # anusvara before a labial is m
        ("कं", "kam"),
        ("किं", "kin"),
        ("प्रायः", "prayah"),  # final visarga is h
        ("निःशुल्क", "nishulka"),  # visarga inside a word is silent
        ("त्व", "twa"),
        ("वन", "van"),
        ("ज्ञ", "gya"),
        ("यज्ञ", "yagya"),
        ("क्ष", "ksha"),
        ("ङ", "nga"),
        ("ञ", "nya"),
        ("ऐन", "ain"),
        ("औषधि", "aushadhi"),
        ("र्\u200dयाल", "ryal"),  # joiners are ignored
        ("सोऽहम्", "so'ham"),
        ("॥", "||"),
    ],
)
def test_simple_rules(dev: str, simple: str) -> None:
    assert to_roman(dev, "simple") == simple


def test_simple_loses_information() -> None:
    assert to_roman("दिन", "simple") == to_roman("दीन", "simple") == "din"
    assert to_roman("तल", "simple")[0] == to_roman("टल", "simple")[0] == "t"
    assert to_roman("सर", "simple") != to_roman("शर", "simple")
    assert to_roman("शर", "simple") == to_roman("षर", "simple") == "shar"


# --- simple: Roman -> Devanagari (best effort) ------------------------------------


@pytest.mark.parametrize(
    ("simple", "dev"),
    [
        ("namaste", "नमस्ते"),
        ("mero", "मेरो"),
        ("ghar", "घर"),
        ("kasto", "कस्तो"),
        ("chha", "छ"),
        ("hunchha", "हुन्छ"),
        ("garchha", "गर्छ"),
        ("ma", "म"),
        ("raamro", "राम्रो"),
        ("nepaal", "नेपाल"),
        ("bhaat", "भात"),
        ("gyaan", "ज्ञान"),
        ("lakshmi", "लक्ष्मि"),
        ("shikshak", "शिक्षक"),
        ("sambandha", "सम्बन्ध"),
        ("sangha", "सङ्घ"),
        ("ganga", "गङ्ग"),
        ("rang", "रङ"),
        ("aama", "आम"),
        ("ek", "एक"),
        ("oo", "ऊ"),
        ("ee", "ई"),
        ("fon", "फोन"),
        ("zarur", "जरुर"),
        ("wari", "वरि"),
        ("taxi", "तक्सि"),
        ("cat", "कत"),
        ("quiz", "कुइज"),
        ("Mero Naam Samir ho.", "मेरो नाम समिर हो।"),
        ("ma bhaat khaanchhu. 2083", "म भात खान्छु। २०८३"),
        ("ke chha? thik chha!", "के छ? थिक छ!"),
        ("a | b ||", "अ । ब ॥"),
        ("3.5 kilo", "३.५ किलो"),
        ("", ""),
    ],
)
def test_simple_to_devanagari(simple: str, dev: str) -> None:
    assert to_devanagari(simple, "simple") == dev


@pytest.mark.parametrize(
    ("typed", "got", "intended"),
    [
        ("nepal", "नेपल", "नेपाल"),  # one "a" is always the short vowel
        ("ramro", "रम्रो", "राम्रो"),
        ("timi", "तिमि", "तिमी"),  # short i unless "ee" or "ii" is typed
        ("kathmandu", "कथ्मन्दु", "काठमाडौँ"),  # t/d are always dental
        ("rishi", "रिशि", "ऋषि"),  # sh is always श (except in "ksh"); ri is never ऋ
        ("jankari", "जङ्करि", "जानकारी"),  # n before k/g becomes ङ
        ("garchhan", "गर्छन", "गर्छन्"),  # no halant is added at the end
    ],
)
def test_simple_to_devanagari_known_wrong_guesses(typed: str, got: str, intended: str) -> None:
    """Pinned so that a change in these documented limits is noticed."""
    assert to_devanagari(typed, "simple") == got
    assert got != intended


def test_simple_is_not_a_round_trip() -> None:
    lossy = [r[0] for r in ROWS if to_devanagari(r[2], "simple") != r[0]]
    exact = [r[0] for r in ROWS if to_devanagari(r[2], "simple") == r[0]]
    assert len(lossy) > len(exact) > 0


# --- errors, API, command line -----------------------------------------------------


@pytest.mark.parametrize("scheme", ["", "IAST", "hk", "itrans"])
def test_unknown_scheme(scheme: str) -> None:
    with pytest.raises(ValueError, match="unknown scheme"):
        to_roman("क", scheme)
    with pytest.raises(ValueError, match="unknown scheme"):
        to_devanagari("ka", scheme)


def test_public_api() -> None:
    assert aksharkit.to_roman is translit.to_roman
    assert aksharkit.to_devanagari is translit.to_devanagari
    assert translit.SCHEMES == ("iast", "simple")
    assert to_roman("नेपाल") == to_roman("नेपाल", "iast") == "nepāla"


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["translit", "नेपाल राम्रो छ।"], "nepāla rāmro cha|"),
        (["translit", "--scheme", "simple", "नेपाल राम्रो छ।"], "nepal ramro chha."),
        (["translit", "--to", "devanagari", "nepāla rāmro cha|"], "नेपाल राम्रो छ।"),
        (["translit", "--to", "devanagari", "--scheme", "simple", "mero ghar"], "मेरो घर"),
        (["translit", "--to", "roman", "--scheme", "iast", "२०८३"], "2083"),
        (["translit", "--keep-digits", "२०८३ साल"], "२०८३ sāla"),
    ],
)
def test_cli_translit(argv: list[str], expected: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 0
    assert capsys.readouterr().out == expected + "\n"


def test_cli_translit_rejects_unknown_scheme(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["translit", "--scheme", "hk", "क"])
    assert info.value.code == 2
