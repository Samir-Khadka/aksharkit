"""Compare the Preeti key tables of four MIT-licensed projects.

This script documents how ``src/aksharkit/data/font_preeti.json`` was made.
It reads ``scripts/preeti_sources.json`` (the single-key facts as each
project states them, with attribution) and sorts every key into one tier:

``agreed``
    At least two independent families give the same letter and nobody
    disagrees.
``majority``
    At least two independent families give the same letter, and one table
    says something else. Used by default; ``strict=True`` leaves these out.
``single``
    Only one family has the key, and nobody disagrees. Not used unless the
    caller asks for unconfirmed entries.
``disputed``
    Anything else. Never used.

Two projects whose rule lists are the same list, entry for entry, are one
*family*, not two sources. A family votes for a key only when every member
that has the key gives the same letter.

``m`` and ``{`` are not letters. They are strokes that change or move the
letter before them, and the converter handles them in code, so they are not
in the table.

Since 0.9 the script also reads ``scripts/preeti_evidence.json``: what real
Preeti documents show. A key the tables left open is ``settled`` when the
glyph in the documents settles it, and every key is marked ``confirmed``
(read by eye, and used in documents from at least three publishers),
``seen`` (read by eye, fewer publishers) or ``never seen``. The tables decide
what a key means; the documents only settle what the tables left open and
say how far each entry has been checked.

Run ``python scripts/compare_preeti_sources.py`` for the report,
``--write`` to regenerate the data file, ``--check`` to confirm the data
file still matches the comparison (the test suite does this).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "scripts" / "preeti_sources.json"
EVIDENCE_FILE = ROOT / "scripts" / "preeti_evidence.json"
TABLE_FILE = ROOT / "src" / "aksharkit" / "data" / "font_preeti.json"

#: Keys the converter treats as strokes, not letters.
STRUCTURAL_KEYS = frozenset({"m", "{"})

#: Minimum number of independent families that must agree.
QUORUM = 2

STATUS = "tested"
LABEL = (
    "tested on real documents — mapping agreed by at least {quorum} of {families} "
    "permissively-licensed table families ({projects} projects) and checked by eye against "
    "{documents} public Preeti documents from {publishers} publishers ({confirmed} keys "
    "confirmed, {unseen} never seen); not reviewed by a native reader"
)


def load_sources() -> dict[str, Any]:
    data = json.loads(SOURCES_FILE.read_text("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("preeti_sources.json must hold an object")
    return data


def load_evidence() -> dict[str, Any]:
    data = json.loads(EVIDENCE_FILE.read_text("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("preeti_evidence.json must hold an object")
    return data


def classify(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one record per key, sorted by code point."""
    family_of = {name: str(meta["family"]) for name, meta in data["sources"].items()}
    tables: dict[str, dict[str, str]] = data["tables"]
    keys = sorted({key for table in tables.values() for key in table} - STRUCTURAL_KEYS)
    records: list[dict[str, Any]] = []
    for key in keys:
        stated = {name: table[key] for name, table in tables.items() if key in table}
        family_values: dict[str, set[str]] = {}
        for name, value in stated.items():
            family_values.setdefault(family_of[name], set()).add(value)
        votes = {fam: next(iter(vals)) for fam, vals in family_values.items() if len(vals) == 1}
        split = sorted(fam for fam, vals in family_values.items() if len(vals) > 1)
        tally: dict[str, list[str]] = {}
        for fam, value in votes.items():
            tally.setdefault(value, []).append(fam)
        best_value = ""
        best_families: list[str] = []
        for value, fams in tally.items():
            if len(fams) > len(best_families):
                best_value, best_families = value, sorted(fams)
        tied = sum(1 for fams in tally.values() if len(fams) == len(best_families)) > 1
        record: dict[str, Any] = {"key": key, "codepoint": f"U+{ord(key):04X}", "stated": stated}
        if len(best_families) >= QUORUM and not tied:
            dissent = {name: value for name, value in stated.items() if value != best_value}
            record["value"] = best_value
            record["families"] = best_families
            record["tier"] = "majority" if dissent else "agreed"
            if dissent:
                record["dissent"] = dissent
        elif len(votes) == 1 and not split and len(family_values) == 1:
            ((fam, value),) = votes.items()
            record["value"] = value
            record["families"] = [fam]
            record["tier"] = "single"
        else:
            record["tier"] = "disputed"
        records.append(record)
    return records


def sight(keys: list[str], evidence: dict[str, Any]) -> dict[str, list[str]]:
    """Sort ``keys`` by how far the documents bear them out."""
    need = int(evidence["publishers_needed"])
    seen: dict[str, Any] = evidence["keys"]
    out: dict[str, list[str]] = {"confirmed": [], "seen": [], "never_seen": []}
    for key in keys:
        if key not in seen:
            out["never_seen"].append(key)
        elif int(seen[key]["publishers"]) >= need:
            out["confirmed"].append(key)
        else:
            out["seen"].append(key)
    return out


def build_table(data: dict[str, Any], evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the content of ``font_preeti.json`` from the comparison."""
    if evidence is None:
        evidence = load_evidence()
    records = classify(data)
    families = sorted({str(meta["family"]) for meta in data["sources"].values()})
    settled: dict[str, Any] = evidence["settled"]
    by_key = {rec["key"]: rec for rec in records}
    for key in settled:
        tier = by_key[key]["tier"] if key in by_key else "absent"
        if tier not in ("disputed", "absent"):
            raise ValueError(f"the documents may only settle a key the tables left open: {key!r}")
    documents = {doc["id"]: doc for doc in evidence["documents"]}

    def proof(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "publisher": documents[item["document"]]["name"],
                "url": documents[item["document"]]["url"],
                "page": item["page"],
                "keys": item["keys"],
                "reads": item["reads"],
            }
            for item in items
        ]

    def entries(tier: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for rec in records:
            if rec["tier"] != tier:
                continue
            entry: dict[str, Any] = {"to": rec["value"], "families": rec["families"]}
            if "dissent" in rec:
                entry["dissent"] = rec["dissent"]
            out[rec["key"]] = entry
        return out

    def sequences(confirmed: bool) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for seq in data["sequences"]:
            if "to" not in seq:
                continue
            if (len(seq["families"]) >= QUORUM) is confirmed:
                out[seq["keys"]] = {"to": seq["to"], "families": seq["families"]}
        return out

    def from_documents(section: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key in sorted(section):
            item = section[key]
            entry: dict[str, Any] = {"to": item["to"], "why": item["why"]}
            if key in by_key:
                entry["tables"] = by_key[key]["stated"]
            entry["evidence"] = proof(item["evidence"])
            out[key] = entry
        return out

    all_keys = sorted({rec["key"] for rec in records} | set(settled) | STRUCTURAL_KEYS)
    checked = sight(all_keys, evidence)
    publishers = sorted({doc["publisher"] for doc in evidence["documents"]})
    return {
        "status": STATUS,
        "font": "Preeti",
        "label": LABEL.format(
            quorum=QUORUM,
            families=len(families),
            projects=len(data["sources"]),
            documents=len(documents),
            publishers=len(publishers),
            confirmed=len(checked["confirmed"]),
            unseen=len(checked["never_seen"]),
        ),
        "note": (
            "Made by scripts/compare_preeti_sources.py from scripts/preeti_sources.json and "
            "scripts/preeti_evidence.json. "
            "Families: A = nepali-unicoder + nepalikit (same rule list, counted once), "
            "B = preeti-unicode-converter, C = nepali-keyboard. 'mapping' needs two "
            "families and no dissent; 'majority' has two families and one dissenting "
            "table; 'unconfirmed' has one family only and is off by default; 'disputed' "
            "is never used; 'settled' holds keys the tables left open and the glyph in "
            "real documents settles. 'm' and '{' are strokes handled in code. 'sight' "
            "says which keys were read by eye in real documents. See docs/preeti.md."
        ),
        "sources": [
            {
                "name": name,
                "family": meta["family"],
                "url": meta["url"],
                "commit": meta["commit"],
                "licence": meta["licence"],
                "copyright": meta["copyright"],
            }
            for name, meta in data["sources"].items()
        ],
        "read_on": data["read_on"],
        "documents": [
            {
                "publisher": doc["name"],
                "kind": doc["kind"],
                "url": doc["url"],
                "pages": doc["pages"],
                "font": doc["font"],
            }
            for doc in evidence["documents"]
        ],
        "sight": {
            "checked_on": evidence["checked_on"],
            "method": evidence["method"],
            "lines_read": evidence["lines_read_by_sight"],
            "publishers": len(publishers),
            "publishers_needed": evidence["publishers_needed"],
            **checked,
        },
        "mapping": entries("agreed"),
        "majority": entries("majority"),
        "unconfirmed": entries("single"),
        "disputed": {
            rec["key"]: rec["stated"]
            for rec in records
            if rec["tier"] == "disputed" and rec["key"] not in settled
        },
        "settled": from_documents(settled),
        "sequences": sequences(True),
        "settled_sequences": from_documents(evidence["sequences"]),
        "unconfirmed_sequences": sequences(False),
    }


def render(table: dict[str, Any]) -> str:
    return json.dumps(table, ensure_ascii=False, indent=2) + "\n"


def report(data: dict[str, Any]) -> str:
    records = classify(data)
    lines: list[str] = []
    counts: dict[str, int] = {}
    for rec in records:
        counts[rec["tier"]] = counts.get(rec["tier"], 0) + 1
    lines.append(f"keys compared: {len(records)}")
    for tier in ("agreed", "majority", "single", "disputed"):
        lines.append(f"  {tier}: {counts.get(tier, 0)}")
    table = build_table(data)
    lines.append(f"  settled by documents: {len(table['settled'])} ({' '.join(table['settled'])})")
    for name in ("confirmed", "seen", "never_seen"):
        keys = table["sight"][name]
        shown = " ".join(keys) if name != "confirmed" else ""
        lines.append(f"  {name.replace('_', ' ')}: {len(keys)} {shown}".rstrip())
    without_a = sum(
        1
        for rec in records
        if rec["tier"] in ("agreed", "majority") and {"B", "C"} <= set(rec["families"])
    )
    lines.append(f"  agreed or majority entries that B and C carry without family A: {without_a}")
    thin = [
        rec["key"]
        for rec in records
        if rec["tier"] in ("agreed", "majority")
        and set(rec["stated"]) == {"nepalikit", "nepali-keyboard"}
    ]
    lines.append(
        f"  entries resting on nepalikit + nepali-keyboard alone: {len(thin)} ({' '.join(thin)})"
    )
    for tier in ("majority", "single", "disputed"):
        lines.append(f"\n{tier}:")
        for rec in records:
            if rec["tier"] != tier:
                continue
            shown = ", ".join(f"{name}={value!r}" for name, value in sorted(rec["stated"].items()))
            lines.append(f"  {rec['key']!r} {rec['codepoint']}: {shown}")
    names = list(data["tables"])
    lines.append("\npairwise (keys in common / same letter):")
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            a, b = data["tables"][left], data["tables"][right]
            common = set(a) & set(b)
            same = sum(1 for key in common if a[key] == b[key])
            lines.append(f"  {left} / {right}: {len(common)} / {same}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="regenerate font_preeti.json")
    group.add_argument("--check", action="store_true", help="fail if font_preeti.json is stale")
    args = parser.parse_args(argv)
    data = load_sources()
    text = render(build_table(data))
    if args.write:
        TABLE_FILE.write_text(text, "utf-8")
        print(f"wrote {TABLE_FILE.relative_to(ROOT)}")
        return 0
    if args.check:
        if TABLE_FILE.read_text("utf-8") != text:
            print("font_preeti.json does not match the comparison", file=sys.stderr)
            return 1
        print("font_preeti.json matches the comparison")
        return 0
    print(report(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
