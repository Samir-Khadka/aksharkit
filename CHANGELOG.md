# Changelog

## 0.2.0 — 23 November 2026

### Added

- **BS ↔ AD dates** (`aksharkit.dates`): `bs_to_ad`, `ad_to_bs`, `BSDate`,
  `parse_bs`, `format_bs` (ISO, long and full styles, optional Devanagari
  digits and names), `fiscal_year` (starts 1 Shrawan), `today_bs`,
  `days_in_month`, `days_in_year`, `is_valid_bs`, `supported_range`,
  `month_name`, `weekday_name`.
- Calendar table for **BS 2000–2083** (14 April 1943 to 13 April 2027), built
  by comparing five published tables. Sources, licences and disagreements are
  in `docs/sources.md`.
- `DateRangeError` for dates outside the table or that do not exist, and
  `DisputedDateError` for 14 May to 14 June 2005 (31 Baishakh to 32 Jestha
  2062), where the published tables differ by one day. `allow_disputed=True`
  uses the majority reading.
- `aksharkit date` command: AD → BS by default, `--to ad`, `--style`,
  `--devanagari`, `--fiscal-year`, `--allow-disputed`.
- `scripts/compare_bs_sources.py`, which repeats the table comparison.
- Preeti source research in `docs/sources.md`. No Preeti table was added.

### Changed

- `aksharkit date` used to exit with code 3 ("not available yet"); it now
  converts dates and exits with code 2 on a bad or out-of-range date.

### Not included

- BS years before 2000 and after 2083: the published tables disagree.
- Preeti conversion: still raises `DataNotVerifiedError`.

## 0.1.0 — 23 November 2026

First public commit (the package version was `0.1.0.dev0`). Unicode
normaliser, digit conversion and number formatting, numbers to words, word
tokeniser and sentence splitter, stopwords, command-line tool. Preeti
conversion and BS dates were stubs.
