"""Compare published Bikram Sambat month-length tables, year by year.

Not part of the package. It reads raw data files that were downloaded by
hand (see docs/sources.md for the URLs), treats them as plain text, and
prints where they agree. Nothing from those projects is imported or run.

Usage: python scripts/compare_bs_sources.py <directory with the raw files> [years.json]
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

Table = dict[int, tuple[int, ...]]


def read_csv_table(path: Path) -> Table:
    out: Table = {}
    with path.open(encoding="utf-8") as fh:
        rows = csv.reader(fh)
        next(rows)
        for row in rows:
            if row:
                out[int(row[0])] = tuple(int(n) for n in row[1:13])
    return out


def read_json_object(path: Path) -> Table:
    raw = json.loads(path.read_text("utf-8"))
    return {int(y): tuple(int(n) for n in months) for y, months in raw.items()}


def read_json_list(path: Path) -> Table:
    raw = json.loads(path.read_text("utf-8"))
    return {int(r["year"]): tuple(int(n) for n in r["months"]) for r in raw}


def read_python_tuples(path: Path, first_year: int) -> Table:
    text = path.read_text("utf-8")
    start = text.index("NP_MONTHS_DATA = [")
    end = text.index("\n    ]", start)
    rows = re.findall(r"\(\s*((?:\d+\s*,\s*){11}\d+)\s*,?\s*\)", text[start:end])
    return {
        first_year + i: tuple(int(n) for n in re.findall(r"\d+", row)) for i, row in enumerate(rows)
    }


def read_ts_objects(path: Path) -> Table:
    text = path.read_text("utf-8")
    out: Table = {}
    for year, body in re.findall(r"'(\d{4})':\s*\{([^}]*)\}", text):
        months = tuple(int(n) for n in re.findall(r":\s*(\d+)", body))
        out[int(year)] = months
    return out


def main(directory: str) -> int:
    d = Path(directory)
    sources: dict[str, Table] = {
        "nepali-datetime": read_csv_table(d / "nd_calendar_bs.csv"),
        "medic/bikram-sambat": read_json_object(d / "medic_daysInMonth.json"),
        "py-nepali": read_python_tuples(d / "pynepali_date_converter.py", 2000),
        "subeshb1/Nepali-Date": read_ts_objects(d / "subesh_date-config.ts"),
        "nepkit": read_json_list(d / "nepkit_calendar.json"),
    }
    for name, table in sources.items():
        bad = [y for y, m in table.items() if len(m) != 12 or not all(29 <= n <= 32 for n in m)]
        odd = [y for y, m in table.items() if sum(m) not in (365, 366)]
        print(
            f"{name}: {min(table)}-{max(table)} ({len(table)} years) malformed={bad} "
            f"not-365/366={odd}"
        )

    years = sorted(set().union(*(t.keys() for t in sources.values())))
    agreed: Table = {}
    print("\nDisagreements (year: source -> months):")
    for year in years:
        have = {n: t[year] for n, t in sources.items() if year in t}
        distinct = set(have.values())
        if len(distinct) == 1 and len(have) >= 2:
            agreed[year] = next(iter(distinct))
        elif len(distinct) > 1:
            print(f"  {year}:")
            for n, m in have.items():
                print(f"    {n:22s} {list(m)} sum={sum(m)}")
    print("\nYears where every source that covers them agrees (>=2 sources):")
    print(" ", _ranges(sorted(agreed)))
    for k in (5, 4, 3):
        ys = [y for y in agreed if sum(y in t for t in sources.values()) >= k]
        print(f"  covered by >= {k} sources: {_ranges(ys)}")

    # Anchor walk: BS 2000-01-01 = AD 1943-04-14 (stated by py-nepali and nepkit);
    # medic states BS 1970-01-01 = AD 1913-04-13. Walk medic's own table.
    medic = sources["medic/bikram-sambat"]
    day = dt.date(1913, 4, 13)
    for y in range(1970, 2000):
        day += dt.timedelta(days=sum(medic[y]))
    print(f"\nmedic epoch walked to BS 2000-01-01 -> AD {day} (expect 1943-04-14)")

    # Longest run of fully agreed years starting at BS 2000, allowing the one
    # known 4-against-1 year (2062) to be carried as "disputed", never silently.
    table: Table = {}
    year = 2000
    while year in agreed or year == 2062:
        table[year] = agreed.get(year) or sources["medic/bikram-sambat"][year]
        year += 1
    last = dt.date(1943, 4, 14) + dt.timedelta(days=sum(sum(m) for m in table.values()) - 1)
    print(f"contiguous table: BS {min(table)}-{max(table)}, last day AD {last}")
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(
            "{\n" + ",\n".join(f'  "{y}": {list(m)}' for y, m in sorted(table.items())) + "\n}\n",
            "utf-8",
        )
        print(f"wrote {sys.argv[2]}")
    return 0


def _ranges(ys: list[int]) -> str:
    if not ys:
        return "none"
    out, a, b = [], ys[0], ys[0]
    for y in ys[1:]:
        if y == b + 1:
            b = y
        else:
            out.append(f"{a}-{b}")
            a = b = y
    out.append(f"{a}-{b}")
    return ", ".join(out)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
