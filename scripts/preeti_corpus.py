"""Count how the Preeti converter does on a local folder of real PDFs.

The numbers in ``docs/preeti.md`` ("Tested on real documents") come from this
script. It needs a folder of PDFs that embed a font named Preeti and the
``pdftohtml`` program from poppler. Neither is part of this repository: the
PDFs are other people's documents and are not copied here. With no folder, or
no ``pdftohtml``, the script says so and exits 0, so it is safe to run
anywhere.

What it does, per PDF:

* asks ``pdftohtml -xml`` for the text with its font, and keeps only the text
  set in a font whose name contains "Preeti" (documents mix fonts; a row that
  also holds text in another font is still used, without that text);
* puts the pieces of one printed line together, with a space where the page
  has a gap, and a new line where a table has a wide gap;
* converts every line and counts key characters, words and the characters
  that had no entry.

Usage::

    python scripts/preeti_corpus.py FOLDER            # the summary
    python scripts/preeti_corpus.py FOLDER --json     # the same as JSON
    python scripts/preeti_corpus.py FOLDER --strict   # only entries no table disputes

``FOLDER`` may also be given in the environment as ``AKSHARKIT_PREETI_PDFS``.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aksharkit.legacy import convert_preeti  # noqa: E402

ENV = "AKSHARKIT_PREETI_PDFS"
_PAGE = re.compile(r"(?=<page )")
_FONT = re.compile(r'<fontspec id="(\d+)" size="-?\d+" family="([^"]*)"')
_TEXT = re.compile(
    r'<text top="(-?\d+)" left="(-?\d+)" width="(-?\d+)" height="(-?\d+)" font="(\d+)">'
    r"(.*?)</text>",
    re.S,
)
_TAG = re.compile(r"</?[a-z][^>]*>")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def preeti_lines(xml: str) -> list[str]:
    """The lines of text set in a font named Preeti, from ``pdftohtml -xml`` output."""
    fonts: dict[str, str] = {}
    lines: list[str] = []
    for page in _PAGE.split(_CONTROL.sub("", xml)):
        if not page.startswith("<page "):
            continue
        for match in _FONT.finditer(page):
            fonts[match[1]] = match[2]
        pieces: list[tuple[float, int, int, int, bool, str]] = []
        for match in _TEXT.finditer(page):
            top, left, width, height = (int(match[i]) for i in range(1, 5))
            text = html.unescape(_TAG.sub("", match[6]))
            wanted = "preeti" in fonts.get(match[5], "").lower()
            pieces.append((top + height / 2, left, width, height, wanted, text))
        pieces.sort(key=lambda piece: (piece[0], piece[1]))
        rows: list[list[tuple[float, int, int, int, bool, str]]] = []
        for piece in pieces:
            if rows:
                last = rows[-1][-1]
                if abs(last[0] - piece[0]) < max(4.0, 0.45 * min(piece[3], last[3])):
                    rows[-1].append(piece)
                    continue
            rows.append([piece])
        for row in rows:
            row.sort(key=lambda piece: piece[1])
            cells: list[list[tuple[float, int, int, int, bool, str]]] = [[]]
            for piece in row:
                if cells[-1]:
                    last = cells[-1][-1]
                    if piece[1] - (last[1] + last[2]) > 2.5 * piece[3]:
                        cells.append([])
                cells[-1].append(piece)
            for cell in cells:
                text = ""
                before: tuple[float, int, int, int, bool, str] | None = None
                for piece in cell:
                    if not piece[4]:
                        continue
                    if before is not None:
                        gap = piece[1] - (before[1] + before[2])
                        if gap > 0.18 * piece[3] and not text.endswith(" ") and piece[5][:1] != " ":
                            text += " "
                    text += piece[5]
                    before = piece
                if text.strip():
                    lines.append(text.strip())
    return lines


def measure(lines: list[str], *, strict: bool = False) -> dict[str, Any]:
    """Convert ``lines`` and count what happened."""
    left: dict[str, int] = {}
    counts = {"lines": len(lines), "characters": 0, "words": 0, "unmapped": 0, "lines_unmapped": 0}
    for line in lines:
        result = convert_preeti(line, strict=strict, keep_links=False)
        counts["characters"] += sum(1 for ch in line if not ch.isspace())
        counts["words"] += len(line.split())
        counts["unmapped"] += len(result.unmapped)
        counts["lines_unmapped"] += bool(result.unmapped)
        for item in result.unmapped:
            left[item.char] = left.get(item.char, 0) + 1
    return {**counts, "unmapped_by_character": left}


def audit(folder: Path, *, strict: bool = False) -> dict[str, Any]:
    """Measure every PDF in ``folder``; documents with no Preeti text are listed apart."""
    documents: list[dict[str, Any]] = []
    without: list[str] = []
    for pdf in sorted(folder.glob("*.pdf")):
        done = subprocess.run(
            ["pdftohtml", "-xml", "-i", "-q", "-stdout", str(pdf)],
            capture_output=True,
            check=False,
        )
        lines = preeti_lines(done.stdout.decode("utf-8", "replace"))
        if not lines:
            without.append(pdf.name)
            continue
        documents.append({"file": pdf.name, **measure(lines, strict=strict)})
    total: dict[str, Any] = {
        name: sum(doc[name] for doc in documents)
        for name in ("lines", "characters", "words", "unmapped", "lines_unmapped")
    }
    by_character: dict[str, int] = {}
    for doc in documents:
        for char, count in doc["unmapped_by_character"].items():
            by_character[char] = by_character.get(char, 0) + count
    total["unmapped_by_character"] = dict(sorted(by_character.items(), key=lambda kv: -kv[1]))
    total["unmapped_share"] = total["unmapped"] / total["characters"] if total["characters"] else 0
    return {"documents": documents, "without_preeti": without, "total": total}


def summary(report: dict[str, Any]) -> str:
    out = []
    for doc in report["documents"]:
        out.append(
            f"{doc['file']}: {doc['lines']} lines, {doc['characters']} key characters, "
            f"{doc['words']} words, {doc['unmapped']} with no entry"
        )
    for name in report["without_preeti"]:
        out.append(f"{name}: no text in a font named Preeti")
    total = report["total"]
    out.append(
        f"all {len(report['documents'])} document(s): {total['lines']} lines, "
        f"{total['characters']} key characters, {total['words']} words, "
        f"{total['unmapped']} with no entry ({100 * total['unmapped_share']:.4f}%) "
        f"on {total['lines_unmapped']} line(s)"
    )
    if total["unmapped_by_character"]:
        shown = ", ".join(
            f"{char!r} U+{ord(char):04X} x{count}"
            for char, count in total["unmapped_by_character"].items()
        )
        out.append(f"with no entry: {shown}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("folder", nargs="?", default=os.environ.get(ENV), help="folder of PDFs")
    parser.add_argument("--strict", action="store_true", help="only entries no table disputes")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    if not args.folder:
        print(f"skipped: no folder given (argument or {ENV})")
        return 0
    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        print(f"skipped: {folder} is not a folder")
        return 0
    if shutil.which("pdftohtml") is None:
        print("skipped: pdftohtml (poppler) is not installed")
        return 0
    report = audit(folder, strict=args.strict)
    if not report["documents"]:
        print(f"skipped: no PDF in {folder} has text in a font named Preeti")
        return 0
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
