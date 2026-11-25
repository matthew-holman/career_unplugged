import ast

from pathlib import Path

import pytest

from sqlmodel import Session, select

from app.models import CareerPage
from app.seeds import discover_career_pages
from app.seeds.career_pages import CareerPageSeeder
from app.seeds.seed_file_writer import (
    SeedEntry,
    SeedFileError,
    append_seed_entries,
    format_seed_entry,
)

SEED_FILE = "acme_pages.py"
ORIGINAL = """ACME_PAGE_SEEDS = [
    {"company_name": "beta", "url": "https://beta.recruitee.com", "active": True},
    {
        "company_name": "gamma",
        "url": "https://gamma.recruitee.com/a-very-long-path-that-forces-a-wrap",
        "active": True,
    },
]
"""


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    (tmp_path / SEED_FILE).write_text(ORIGINAL, encoding="utf-8")
    return tmp_path


def _load(data_dir: Path) -> list[dict[str, object]]:
    module = ast.parse((data_dir / SEED_FILE).read_text(encoding="utf-8"))
    assign = module.body[0]
    assert isinstance(assign, ast.Assign)
    value = ast.literal_eval(assign.value)
    assert isinstance(value, list)
    return value


def test_format_seed_entry_matches_black_layout() -> None:
    short = SeedEntry(company_name="acme", url="https://acme.recruitee.com")
    assert format_seed_entry(short) == (
        '    {"company_name": "acme", "url": "https://acme.recruitee.com", '
        '"active": True},\n'
    )

    long = SeedEntry(company_name="acme", url="https://acme.recruitee.com/" + "x" * 60)
    assert format_seed_entry(long).splitlines() == [
        "    {",
        '        "company_name": "acme",',
        f'        "url": "{long.url}",',
        '        "active": True,',
        "    },",
    ]


def test_format_seed_entry_escapes_strings() -> None:
    entry = SeedEntry(company_name='mal"mö', url="https://x.recruitee.com")
    line = format_seed_entry(entry)
    assert ast.literal_eval(line.strip().rstrip(",")) == entry.as_seed()


def test_append_adds_new_entries_sorted_and_skips_known(data_dir: Path) -> None:
    added = append_seed_entries(
        SEED_FILE,
        [
            SeedEntry(company_name="zeta", url="https://zeta.recruitee.com/"),
            SeedEntry(company_name="alpha", url="https://alpha.recruitee.com"),
            # Already present, with and without a trailing slash.
            SeedEntry(company_name="beta", url="https://beta.recruitee.com/"),
            # Duplicate within the batch.
            SeedEntry(company_name="alpha", url="https://alpha.recruitee.com/"),
        ],
        data_dir=data_dir,
    )

    assert [e.url for e in added] == [
        "https://alpha.recruitee.com",
        "https://zeta.recruitee.com",
    ]
    seeds = _load(data_dir)
    assert [s["company_name"] for s in seeds] == ["beta", "gamma", "alpha", "zeta"]
    assert all(s["active"] is True for s in seeds)
    text = (data_dir / SEED_FILE).read_text(encoding="utf-8")
    assert text.startswith(ORIGINAL[: -len("]\n")])
    assert text.endswith("},\n]\n")


def test_append_nothing_new_leaves_file_untouched(data_dir: Path) -> None:
    before = (data_dir / SEED_FILE).stat().st_mtime_ns
    added = append_seed_entries(
        SEED_FILE,
        [SeedEntry(company_name="beta", url="https://beta.recruitee.com")],
        data_dir=data_dir,
    )
    assert added == []
    assert (data_dir / SEED_FILE).stat().st_mtime_ns == before


def test_append_to_empty_list(tmp_path: Path) -> None:
    (tmp_path / SEED_FILE).write_text("ACME_PAGE_SEEDS = [\n]\n", encoding="utf-8")
    append_seed_entries(
        SEED_FILE,
        [SeedEntry(company_name="acme", url="https://acme.recruitee.com")],
        data_dir=tmp_path,
    )
    assert [s["url"] for s in _load(tmp_path)] == ["https://acme.recruitee.com"]


@pytest.mark.parametrize(
    "seed_file, content",
    [
        ("../acme_pages.py", None),
        ("missing_pages.py", None),
        (SEED_FILE, "ACME_PAGE_SEEDS = [\n    {}\n]\n"),  # no trailing comma
        (SEED_FILE, "ACME_PAGE_SEEDS = (\n)\n"),  # not a list
    ],
)
def test_append_rejects_bad_files(
    tmp_path: Path, seed_file: str, content: str | None
) -> None:
    if content is not None:
        (tmp_path / SEED_FILE).write_text(content, encoding="utf-8")
    with pytest.raises(SeedFileError):
        append_seed_entries(
            seed_file,
            [SeedEntry(company_name="acme", url="https://acme.recruitee.com")],
            data_dir=tmp_path,
        )
    if content is not None:
        assert (tmp_path / SEED_FILE).read_text(encoding="utf-8") == content


def test_write_seed_files_stage(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.seeds.seed_file_writer.SEED_DATA_DIR", data_dir)
    results = {
        SEED_FILE: [
            ("https://new.recruitee.com", "new", "recruitee.com"),
            ("https://beta.recruitee.com", "beta", "recruitee.com"),
        ],
        "missing_pages.py": [("https://x.recruitee.com", "x", "recruitee.com")],
    }

    written = discover_career_pages.write_seed_files(results)

    assert written == {
        SEED_FILE: [SeedEntry(company_name="new", url="https://new.recruitee.com")]
    }


def test_seeder_seed_inserts_only_new_pages(db_session: Session) -> None:
    db_session.add(CareerPage(company_name=None, url="https://old.recruitee.com"))
    db_session.flush()

    created = CareerPageSeeder(db_session).seed(
        [
            SeedEntry(company_name="old", url="https://old.recruitee.com/").as_seed(),
            SeedEntry(company_name="new", url="https://new.recruitee.com").as_seed(),
        ]
    )
    db_session.flush()

    assert created == 1
    pages = db_session.exec(select(CareerPage).order_by(CareerPage.url)).all()
    assert [(p.company_name, p.url, p.active) for p in pages] == [
        ("new", "https://new.recruitee.com", True),
        ("old", "https://old.recruitee.com", True),
    ]
