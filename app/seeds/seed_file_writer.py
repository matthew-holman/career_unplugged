"""Append career page entries to the seed files in ``app/seeds/data/``.

Each seed file is a Python module holding one list of dicts, e.g.::

    RECRUITEE_PAGE_SEEDS = [
        {"company_name": "acme", "url": "https://acme.recruitee.com", "active": True},
    ]

New entries are inserted before the closing ``]`` in the same layout Black
produces, so the files stay formatted and diffs stay one entry per change.
"""

from __future__ import annotations

import json
import os
import re
import tempfile

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

SEED_DATA_DIR = Path(__file__).parent / "data"

_BLACK_LINE_LENGTH = 88
_URL_RE = re.compile(r'"url":\s*"([^"]+)"')


@dataclass(frozen=True)
class SeedEntry:
    company_name: str
    url: str

    def as_seed(self) -> dict[str, object]:
        return {"company_name": self.company_name, "url": self.url, "active": True}


class SeedFileError(Exception):
    pass


def format_seed_entry(entry: SeedEntry) -> str:
    """One list item, laid out the way Black would."""
    name = _literal(entry.company_name)
    url = _literal(entry.url)
    one_line = f'    {{"company_name": {name}, "url": {url}, "active": True}},\n'
    if len(one_line.rstrip("\n")) <= _BLACK_LINE_LENGTH:
        return one_line
    return (
        "    {\n"
        f'        "company_name": {name},\n'
        f'        "url": {url},\n'
        '        "active": True,\n'
        "    },\n"
    )


def append_seed_entries(
    seed_file: str,
    entries: Sequence[SeedEntry],
    data_dir: Path | None = None,
) -> list[SeedEntry]:
    """
    Append entries whose URL is not already in the file, sorted by company
    name. Returns the entries actually written. The file is replaced
    atomically, so a failure never leaves it half-written.
    """
    path = _seed_path(seed_file, data_dir)
    text = path.read_text(encoding="utf-8")

    known = {_normalise_url(url) for url in _URL_RE.findall(text)}
    new: list[SeedEntry] = []
    for entry in sorted(entries, key=lambda e: (e.company_name, e.url)):
        url = _normalise_url(entry.url)
        if url in known:
            continue
        known.add(url)
        new.append(SeedEntry(company_name=entry.company_name, url=url))
    if not new:
        return []

    body = text.rstrip()
    if not body.endswith("]"):
        raise SeedFileError(f"{path.name}: expected the seed list to end with ']'")
    head = body[:-1].rstrip()
    if not (head.endswith(",") or head.endswith("[")):
        raise SeedFileError(f"{path.name}: last seed entry has no trailing comma")

    updated = head + "\n" + "".join(format_seed_entry(e) for e in new) + "]\n"
    _atomic_write(path, updated)
    return new


def _seed_path(seed_file: str, data_dir: Path | None) -> Path:
    if Path(seed_file).name != seed_file or not seed_file.endswith(".py"):
        raise SeedFileError(f"not a seed file name: {seed_file!r}")
    path = (data_dir or SEED_DATA_DIR) / seed_file
    if not path.is_file():
        raise SeedFileError(f"seed file does not exist: {path}")
    return path


def _normalise_url(url: str) -> str:
    return url.rstrip("/")


def _literal(value: str) -> str:
    # JSON string syntax is valid Python and double-quoted, as Black wants.
    return json.dumps(value, ensure_ascii=False)


def _atomic_write(path: Path, text: str) -> None:
    mode = path.stat().st_mode & 0o777
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp_name, mode)  # mkstemp creates files as 0600
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise
