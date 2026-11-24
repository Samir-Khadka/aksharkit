"""Assemble the GitHub Pages site into one directory.

    python scripts/build_site.py --out _site
    python -m http.server --directory _site   # then open http://localhost:8000

The output is ``site/`` (minus the Python glue) plus ``pkg/aksharkit.zip``:
the library's own source files, ``site/playground.py`` (stored as
``aksharkit_playground.py``) and the ``LICENSE`` and ``NOTICE`` files, which
the MIT licence asks to travel with the code. The page unpacks that archive inside Pyodide,
so the playground always runs the code in this repository.

Standard library only. The archive is reproducible: files are sorted and
carry a fixed timestamp.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "aksharkit"
SITE = ROOT / "site"
GLUE = SITE / "playground.py"
GLUE_NAME = "aksharkit_playground.py"
LEGAL = ("LICENSE", "NOTICE")
ARCHIVE = "pkg/aksharkit.zip"
MANIFEST = "pkg/manifest.json"
_FIXED_TIME = (2026, 1, 1, 0, 0, 0)
_SKIP_DIRS = {"__pycache__"}
_SKIP_SUFFIXES = {".pyc", ".pyo"}


def package_files() -> list[Path]:
    """Every file of the installed package, sorted."""
    return sorted(
        path
        for path in PACKAGE.rglob("*")
        if path.is_file()
        and not _SKIP_DIRS.intersection(path.relative_to(PACKAGE).parts)
        and path.suffix not in _SKIP_SUFFIXES
    )


def package_version() -> str:
    text = (PACKAGE / "__init__.py").read_text("utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', text, re.MULTILINE)
    if match is None:
        raise SystemExit("could not read __version__ from src/aksharkit/__init__.py")
    return match.group(1)


def _add(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=_FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)


def build_archive(target: Path) -> list[str]:
    """Write the package archive and return the names stored in it."""
    target.parent.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    with zipfile.ZipFile(target, "w") as archive:
        for path in package_files():
            name = "aksharkit/" + path.relative_to(PACKAGE).as_posix()
            _add(archive, name, path.read_bytes())
            names.append(name)
        _add(archive, GLUE_NAME, GLUE.read_bytes())
        names.append(GLUE_NAME)
        for name in LEGAL:
            _add(archive, name, (ROOT / name).read_bytes())
            names.append(name)
    return names


def asset_stamp(out: Path) -> str:
    """A short hash of everything the page loads from this site."""
    digest = hashlib.sha256()
    for name in ("app.js", "style.css", ARCHIVE):
        digest.update((out / name).read_bytes())
    return digest.hexdigest()[:12]


def stamp_index(out: Path) -> str:
    """Add ``?v=<hash>`` to the script and stylesheet addresses in the built page.

    GitHub Pages lets browsers keep ``app.js``, ``style.css`` and the archive
    for hours but the page itself for minutes, so after an update a returning
    visitor could get the new page with the old script and library. A new
    address for every build avoids that; ``app.js`` reuses its own stamp when
    it fetches the archive.
    """
    stamp = asset_stamp(out)
    index = out / "index.html"
    text = index.read_text("utf-8")
    for old in ('src="app.js"', 'href="style.css"'):
        if text.count(old) != 1:
            raise SystemExit(f"expected exactly one {old} in site/index.html")
        text = text.replace(old, old[:-1] + "?v=" + stamp + '"')
    index.write_text(text, "utf-8")
    return stamp


def build(out: Path) -> dict[str, object]:
    """Build the whole site into ``out`` (emptied first) and return the manifest."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for path in sorted(SITE.iterdir()):
        if path.is_file() and path != GLUE:
            shutil.copy2(path, out / path.name)
    names = build_archive(out / ARCHIVE)
    stamp_index(out)
    manifest: dict[str, object] = {
        "version": package_version(),
        "archive": ARCHIVE,
        "sha256": hashlib.sha256((out / ARCHIVE).read_bytes()).hexdigest(),
        "files": names,
    }
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")
    # GitHub Pages must serve the files as they are, without Jekyll.
    (out / ".nojekyll").write_text("", "utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="_site", help="output directory (default: _site)")
    args = parser.parse_args(argv)
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    manifest = build(out)
    files = manifest["files"]
    assert isinstance(files, list)
    print(f"built {out} — aksharkit {manifest['version']}, {len(files)} files in {ARCHIVE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
