#!/usr/bin/env python3
"""Run offline integrity and accessibility checks on the static site."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT / "scripts"))

from build_archive import build_payload  # noqa: E402


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []
        self.ids: list[str] = []
        self.h1_count = 0
        self.main_count = 0
        self.lang = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang") or ""
        if tag == "h1":
            self.h1_count += 1
        if tag == "main":
            self.main_count += 1
        if values.get("id"):
            self.ids.append(values["id"] or "")
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.references.append(value)


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    duplicates = sorted(value for value, count in Counter(parser.ids).items() if count > 1)
    if duplicates:
        fail(f"{path.name}: duplicate id(s): {', '.join(duplicates)}")
    if parser.lang != "en":
        fail(f"{path.name}: expected html lang=en")
    if parser.main_count != 1 or parser.h1_count != 1:
        fail(f"{path.name}: expected exactly one main and one h1")
    return parser


def check_reference(path: Path, reference: str, ids: set[str]) -> None:
    if reference.startswith("#"):
        if reference[1:] not in ids:
            fail(f"{path.name}: broken fragment {reference}")
        return
    if reference.startswith(("mailto:", "data:")):
        return
    parsed = urlsplit(reference)
    if parsed.scheme:
        if parsed.scheme != "https":
            fail(f"{path.name}: external URL must use HTTPS: {reference}")
        return
    if reference.startswith("/"):
        if path.name != "404.html":
            fail(f"{path.name}: root-relative link breaks GitHub project Pages")
        return
    relative = parsed.path
    if not relative:
        return
    target = (path.parent / relative).resolve()
    if SITE.resolve() not in (target, *target.parents):
        fail(f"{path.name}: reference escapes site root: {reference}")
    if not target.exists():
        fail(f"{path.name}: broken local reference {reference}")


def validate_pages() -> None:
    pages = sorted(SITE.glob("*.html"))
    if {path.name for path in pages} != {"index.html", "404.html"}:
        fail("Expected index.html and 404.html only")
    parsed: dict[Path, PageParser] = {path: parse_page(path) for path in pages}
    required_ids = {
        "archive",
        "archive-controls",
        "search-input",
        "paper-list",
        "result-count",
        "methodology",
        "archive-version",
        "coverage-date",
    }
    index_ids = set(parsed[SITE / "index.html"].ids)
    missing = sorted(required_ids - index_ids)
    if missing:
        fail(f"index.html missing interface ID(s): {', '.join(missing)}")
    for path, parser in parsed.items():
        for reference in parser.references:
            check_reference(path, reference, set(parser.ids))


def validate_payload() -> int:
    payload = json.loads((SITE / "data/archive.json").read_text(encoding="utf-8"))
    if payload != build_payload(ROOT):
        fail("archive.json is stale relative to the governed registries")
    records = payload.get("records")
    if not isinstance(records, list):
        fail("archive.json records must be a list")
    if payload.get("counts", {}).get("records") != len(records):
        fail("Rendered-data count mismatch")
    for record in records:
        links = record.get("links") or {}
        for name, value in links.items():
            parsed = urlsplit(value)
            if name != "doi" or parsed.scheme != "https" or parsed.netloc != "doi.org":
                fail(f"{record.get('id')}: unexpected external public link")
    return len(records)


def validate_assets() -> None:
    javascript = (SITE / "app.js").read_text(encoding="utf-8")
    if re.search(r"\.innerHTML\s*=|insertAdjacentHTML", javascript):
        fail("JavaScript must not inject bibliographic metadata as HTML")
    if 'fetch("./data/archive.json")' not in javascript:
        fail("Site does not load the generated archive dataset")
    if "replaceChildren" not in javascript or "textContent" not in javascript:
        fail("Site must render untrusted metadata through DOM text nodes")

    css = (SITE / "styles.css").read_text(encoding="utf-8")
    for required in (
        ":focus-visible",
        "outline: 3px solid #fff",
        "box-shadow: 0 0 0 6px var(--ink)",
        "prefers-reduced-motion: reduce",
    ):
        if required not in css:
            fail(f"styles.css missing accessibility safeguard: {required}")


def main() -> None:
    validate_pages()
    count = validate_payload()
    validate_assets()
    print(f"[OK] Static site validation passed: {count} public record(s).")


if __name__ == "__main__":
    try:
        main()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        fail(str(exc))
