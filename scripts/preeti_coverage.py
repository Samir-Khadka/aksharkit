#!/usr/bin/env python3
"""Measure what the Unicode to Preeti direction can and cannot write.

Every form below is put through ``encode_preeti``. A form *passes* when all
of it is written as key codes; the encoder only ever writes keys that
``convert_preeti`` turns back into exactly the same text, so a pass is an
exact round trip. A form that does not pass is listed with the reason:

* ``no key``            no table family has a key for a character in it;
* ``unconfirmed key``   only one table family has a key; written only with
                        ``include_unconfirmed=True``;
* ``disputed key``      the families disagree about the key, so it is not used;
* ``position``          the character has a key only in another position
                        (a colon straight after a letter);
* ``does not read back`` every character has a key, but the keys convert
                        back to different text.

This measures the round trip, nothing else. Nobody has looked at the keys in
the Preeti font; a pass does not say that a typist would press these keys.

Usage::

    python scripts/preeti_coverage.py            # summary and the failures
    python scripts/preeti_coverage.py --json     # the same as JSON
    python scripts/preeti_coverage.py --markdown # the table for docs/preeti.md
    python scripts/preeti_coverage.py --check    # exit 1 if docs/preeti.md is stale
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aksharkit.legacy import convert_preeti, encode_preeti, load_font_table  # noqa: E402

VIRAMA = "\u094d"
NUKTA = "\u093c"
ZWJ = "\u200d"
ZWNJ = "\u200c"
CONSONANTS = [chr(c) for c in range(0x0915, 0x093A) if c not in (0x0929, 0x0931, 0x0933, 0x0934)]
VOWEL_SIGNS = list("ािीुूृेैोौ")
SIGNS = ["ँ", "ं", "ः", VIRAMA]
VOWELS = [*"अआइईउऊऋएऐओऔ", "अं", "अः"]
DIGITS = [chr(c) for c in range(0x0966, 0x0970)]

# Three-consonant (and longer) conjuncts met in ordinary Nepali and in
# Sanskrit loans. Written out by hand for this script.
LONG_CONJUNCTS = """
स्त्र न्त्र ष्ट्र न्द्र क्ष्म क्ष्य क्ष्ण त्त्व त्स्य न्त्य न्ध्य न्द्य म्प्र ङ्क्ष ङ्ग्र ङ्ग्य ङ्क्त
ल्क्य स्क्र स्थ्य स्त्य ष्ठ्य च्छ्र ज्ज्व त्त्र द्ध्य द्भ्य न्त्व न्ध्र न्न्य प्त्य म्ब्र र्त्य र्द्ध र्घ्य
र्त्स र्ध्व र्म्य र्ष्य ल्प्य श्च्य ष्क्र ष्प्र स्प्र स्म्य स्व्य ह्म्य क्त्र ग्ध्य ग्न्य ज्ञ्य त्क्र त्प्र
त्म्य त्क्ष द्ग्र न्क्र न्स्क म्प्य म्भ्र ल्ट्र स्ट्र म्स्क क्स्ट न्ट्र न्ड्र र्क्स न्द्व न्ध्व ण्ड्र ष्ट्य
ष्ण्य स्न्य क्ल्य त्न्य प्स्य ब्ज्य न्ह्र म्ह्र ल्ह्र न्क्ष र्ज्ञ स्थ्र श्र्य त्र्य क्र्य
""".split()  # noqa: SIM905

# Shapes with a key or a drawing of their own.
LIGATURES = """
क्ष त्र ज्ञ श्र द्य द्ध द्व द्म द्द द्र द्घ द्ब द्ग द्भ ह्म ह्य ह्र ह्न ह्ल ह्व ह्ण हृ रु रू क्त त्त
ट्ट ट्ठ ठ्ठ ड्ड ड्ढ ङ्क ङ्ख ङ्ग ङ्घ ञ्च ञ्ज न्न क्क ल्ल श्च श्व श्न श्ल स्र ध्र झ्र फ्र क्र ट्र ठ्र ड्र ढ्र छ्र ङ्र
""".split()  # noqa: SIM905

RA_FORMS = (
    [f"र{VIRAMA}{c}" for c in CONSONANTS]
    + [f"{c}{VIRAMA}र" for c in CONSONANTS]
    + [f"र{VIRAMA}{c}{v}" for c in "कगतदमयवस" for v in VOWEL_SIGNS]
    + [f"{c}{VIRAMA}र{v}" for c in "कगतदपबटड" for v in VOWEL_SIGNS]
    + [f"र{VIRAMA}{c}{v}{s}" for c in "कदम" for v in "ाेिी" for s in "ँं"]
    + [f"र{VIRAMA}{c}" for c in ("त्य", "द्ध", "ध्व", "क्ष", "ज्ञ", "त्र", "श्व", "स्य", "प्र")]
    + ["रु", "रू", "रृ", "र्‍य", "र्‍ह", "ऋ", "ॠ", "कृ", "कॄ", "गर्छ", "गर्दै", "ईं", "ई", "कर्म", "धर्मी"]
)

PUNCTUATION = [
    "।", "॥", "?", "!", ",", ";", ".", "/", "%", "+", "=", "(", ")", "“", "”", "‘", "’",
    ":", "-", "–", "—", "…", "[", "]", "{", "}", "*", '"', "'", "॰", "×", "÷", "&", "#", "@",
]  # fmt: skip

SPECIAL = ["ॐ", "ऽ", "कॅ", "कॉ", "ऍ", "ऑ", "ॠ", "ऌ", "कॢ", "क़", "ख़", "ग़", "ज़", "ड़", "ढ़", "फ़", "य़"]

JOINERS = [
    f"क{VIRAMA}{ZWJ}ष", f"क{VIRAMA}{ZWNJ}ष", f"र{VIRAMA}{ZWJ}य", f"र{VIRAMA}{ZWJ}ह",
    f"श{VIRAMA}{ZWJ}च", f"द{VIRAMA}{ZWNJ}ध", f"न{VIRAMA}{ZWJ}", f"स{VIRAMA}{ZWNJ}",
    f"ट{VIRAMA}{ZWNJ}ट", f"ह{VIRAMA}{ZWNJ}म",
]  # fmt: skip


def classes() -> list[tuple[str, str, list[str]]]:
    """``(id, description, forms)`` for every class of the audit."""
    two = [f"{a}{VIRAMA}{b}" for a in CONSONANTS for b in CONSONANTS]
    return [
        ("consonants", "The 33 consonants", CONSONANTS),
        ("vowels", "Independent vowels, with अं and अः", VOWELS),
        ("digits", "Devanagari digits", DIGITS),
        ("matra", "Consonant with a vowel sign", [c + v for c in CONSONANTS for v in VOWEL_SIGNS]),
        ("signs", "Consonant with ँ ं ः or a halant", [c + s for c in CONSONANTS for s in SIGNS]),
        (
            "matra-nasal",
            "Consonant, vowel sign, then ँ or ं",
            [c + v + s for c in CONSONANTS for v in VOWEL_SIGNS for s in "ँं"],
        ),
        ("conjunct-2", "Every two-consonant conjunct", two),
        ("conjunct-2-i", "Every two-consonant conjunct with ि", [t + "ि" for t in two]),
        (
            "conjunct-2-halant",
            "Every two-consonant conjunct with a halant",
            [t + VIRAMA for t in two],
        ),
        ("conjunct-3", "Longer conjuncts (hand list)", LONG_CONJUNCTS),
        (
            "conjunct-3-signs",
            "Longer conjuncts with ि, ी, े and ों",
            [t + v for t in LONG_CONJUNCTS for v in ("ि", "ी", "े", "ों")],
        ),
        ("ligatures", "Shapes with a key of their own (hand list)", LIGATURES),
        ("ra", "Reph, ra stroke and ऋ forms", list(dict.fromkeys(RA_FORMS))),
        ("punctuation", "Punctuation straight after a word", ["क" + p for p in PUNCTUATION]),
        (
            "punctuation-alone",
            "Punctuation standing alone between words",
            [f"क {p} ख" for p in PUNCTUATION],
        ),
        ("special", "ॐ, ऽ, borrowed vowels and nukta letters", SPECIAL),
        ("joiners", "Forms with a zero-width joiner or non-joiner", JOINERS),
    ]


def _table_values() -> set[str]:
    """Every character some table gives for a disputed key."""
    disputed: set[str] = set()
    for entry in load_font_table("preeti").get("disputed", {}).values():
        for value in entry.values():
            disputed.update(str(value))
    return disputed


def reason(form: str, strict: bool, unconfirmed: bool) -> str:
    """Say why ``form`` was not written whole."""
    result = encode_preeti(form, strict=strict, include_unconfirmed=unconfirmed)
    disputed = _table_values()
    if result.unmapped:
        parts: list[str] = []
        for ch in result.unmapped_chars:
            name = f"U+{ord(ch):04X}"
            if ch == ":":
                parts.append(f"position: a colon straight after a letter has no key ({name})")
            elif (
                not unconfirmed
                and encode_preeti(form, strict=strict, include_unconfirmed=True).complete
            ):
                parts.append(f"unconfirmed key for {name}")
            elif ch in disputed:
                parts.append(f"disputed key for {name}")
            elif ch == NUKTA:
                parts.append(
                    f"no key for this nukta letter ({name}); only ड़ and ढ़ have an unconfirmed one"
                )
            else:
                parts.append(f"no key for {name}")
        return "; ".join(parts)
    if result.skipped:
        if (
            not unconfirmed
            and encode_preeti(form, strict=strict, include_unconfirmed=True).complete
        ):
            return "unconfirmed key"
        try:
            from aksharkit.legacy import _encode_piece, _reverse

            keys = _encode_piece(result.skipped[0].text, _reverse(strict, unconfirmed))
        except KeyError as error:
            missing = str(error.args[0])
            names = " ".join(f"U+{ord(ch):04X}" for ch in missing)
            return f"no key for {missing!r} ({names})"
        back = convert_preeti(
            keys, strict=strict, include_unconfirmed=unconfirmed, keep_links=False
        )
        return f"does not read back: keys {keys!r} give {back.text!r}"
    if result.foreign:
        return "left alone: no Devanagari in it"
    return "passes"


def audit(strict: bool = False, unconfirmed: bool = False) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    total = passed = 0
    for ident, description, forms in classes():
        failures: list[dict[str, str]] = []
        for form in forms:
            result = encode_preeti(form, strict=strict, include_unconfirmed=unconfirmed)
            if result.complete and not result.foreign:
                continue
            failures.append({"form": form, "reason": reason(form, strict, unconfirmed)})
        rows.append(
            {
                "id": ident,
                "description": description,
                "forms": len(forms),
                "pass": len(forms) - len(failures),
                "failures": failures,
            }
        )
        total += len(forms)
        passed += len(forms) - len(failures)
    return {
        "strict": strict,
        "include_unconfirmed": unconfirmed,
        "forms": total,
        "pass": passed,
        "classes": rows,
    }


def markdown() -> str:
    """The summary table kept in docs/preeti.md."""
    default = audit()
    wide = audit(unconfirmed=True)
    narrow = audit(strict=True)
    lines = [
        "| Class | Forms | Default | `--unconfirmed` | `--strict` |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for a, b, c in zip(default["classes"], wide["classes"], narrow["classes"], strict=True):  # type: ignore[call-overload]
        lines.append(
            f"| {a['description']} | {a['forms']} | {a['pass']} | {b['pass']} | {c['pass']} |"
        )
    totals = " | ".join(f"**{report['pass']}**" for report in (default, wide, narrow))
    lines.append(f"| **All** | **{default['forms']}** | {totals} |")
    return "\n".join(lines)


def _print(report: dict[str, object], names: Iterable[str]) -> None:
    print(f"Unicode to Preeti coverage ({', '.join(names)})")
    print(
        f"{report['pass']} of {report['forms']} forms are written as keys and read back exactly.\n"
    )
    for row in report["classes"]:  # type: ignore[attr-defined]
        print(f"  {row['pass']:>5} / {row['forms']:<5} {row['description']}")
    print("\nForms that are not written, and why:")
    for row in report["classes"]:  # type: ignore[attr-defined]
        if not row["failures"]:
            continue
        print(f"\n  {row['description']}")
        grouped: dict[str, list[str]] = {}
        for item in row["failures"]:
            grouped.setdefault(item["reason"], []).append(item["form"])
        for why, forms in grouped.items():
            print(f"    {why} ({len(forms)}):")
            print("      " + "  ".join(forms))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true", help="only keys every family agrees on")
    parser.add_argument("--unconfirmed", action="store_true", help="also keys only one family has")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument(
        "--markdown", action="store_true", help="print the table for docs/preeti.md"
    )
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if docs/preeti.md lacks this table"
    )
    args = parser.parse_args(argv)
    if args.markdown or args.check:
        table = markdown()
        if args.markdown:
            print(table)
            return 0
        text = (ROOT / "docs" / "preeti.md").read_text(encoding="utf-8")
        if table in text:
            print("docs/preeti.md holds the current coverage table.")
            return 0
        print("docs/preeti.md does not hold the current coverage table; run with --markdown.")
        return 1
    report = audit(strict=args.strict, unconfirmed=args.unconfirmed)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    names = ["strict" if args.strict else "agreed and majority keys"]
    if args.unconfirmed:
        names.append("with unconfirmed keys")
    _print(report, names)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
