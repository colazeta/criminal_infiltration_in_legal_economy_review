#!/usr/bin/env python3
"""Run lightweight integrity checks on the generated static site."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"] or "")
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.references.append(value)


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def main() -> None:
    index = SITE / "index.html"
    if not index.exists():
        fail("site/index.html is missing")
    parser = ReferenceParser()
    parser.feed(index.read_text(encoding="utf-8"))

    required_ids = {
        "archive",
        "archive-controls",
        "search-input",
        "paper-list",
        "result-count",
        "methodology",
    }
    missing_ids = sorted(required_ids - parser.ids)
    if missing_ids:
        fail(f"Site is missing required interface IDs: {', '.join(missing_ids)}")

    for reference in parser.references:
        if reference.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        if reference.startswith("/"):
            fail(f"Root-relative reference will break on GitHub project Pages: {reference}")
        target = (SITE / reference.split("#", 1)[0].split("?", 1)[0]).resolve()
        if not target.exists():
            fail(f"Broken local reference in index.html: {reference}")

    payload = json.loads((SITE / "data/archive.json").read_text(encoding="utf-8"))
    if payload.get("counts", {}).get("records") != len(payload.get("records", [])):
        fail("Rendered-data count mismatch")
    if not payload.get("records"):
        fail("The deployed archive would be empty")

    javascript = (SITE / "app.js").read_text(encoding="utf-8")
    if re.search(r"\.innerHTML\s*=|insertAdjacentHTML", javascript):
        fail("Site JavaScript must not inject bibliographic metadata as HTML")
    if "fetch(\"./data/archive.json\")" not in javascript:
        fail("Site does not load the generated archive dataset")

    print(
        f"[OK] Static site validation passed: {len(payload['records'])} public record(s)."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, json.JSONDecodeError) as exc:
        fail(str(exc))
