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
from curation.build_curator_options import build_payload as build_curator_options  # noqa: E402
from curation.build_curator_stats import build_payload as build_curator_payload  # noqa: E402
from metrics.surveillance import MetricsError, validate_public_payload  # noqa: E402


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


def parse_page(path: Path, expected_lang: str) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    duplicates = sorted(value for value, count in Counter(parser.ids).items() if count > 1)
    if duplicates:
        fail(f"{path.name}: duplicate id(s): {', '.join(duplicates)}")
    if parser.lang != expected_lang:
        fail(f"{path.name}: expected html lang={expected_lang}")
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
    expected_languages = {
        "index.html": "en",
        "404.html": "en",
        "curate.html": "it",
        "stats.html": "it",
    }
    if {path.name for path in pages} != set(expected_languages):
        fail("Expected index.html, stats.html, curate.html and 404.html only")
    parsed: dict[Path, PageParser] = {
        path: parse_page(path, expected_languages[path.name]) for path in pages
    }
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
    curator_ids = set(parsed[SITE / "curate.html"].ids)
    missing = sorted(
        {
            "curator-workflow",
            "curator-actions",
            "queue-total",
            "queue-metadata",
            "queue-manual",
            "queue-abstract",
            "queue-legacy-rejected",
            "queue-origin-summary",
            "last-run-status",
            "editorial-app",
            "curator-login-panel",
            "editorial-console",
            "candidate-list",
            "candidate-detail",
            "decision-form",
            "screening-stage",
            "decision",
            "evidence-basis",
            "decision-rationale",
            "explicit-confirmation",
            "submit-decision",
        }
        - curator_ids
    )
    if missing:
        fail(f"curate.html missing interface ID(s): {', '.join(missing)}")
    stats_ids = set(parsed[SITE / "stats.html"].ids)
    missing = sorted(
        {
            "research-statistics",
            "new-candidates-7",
            "all-time-candidates",
            "unique-results-7",
            "source-completion-30",
            "data-through",
            "daily-chart",
            "source-table-body",
            "daily-table-body",
        }
        - stats_ids
    )
    if missing:
        fail(f"stats.html missing interface ID(s): {', '.join(missing)}")
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


def validate_statistics() -> int:
    payload = json.loads((SITE / "data/research-stats.json").read_text(encoding="utf-8"))
    validate_public_payload(payload)
    return len(payload["daily"])


def validate_curator_statistics() -> dict[str, object]:
    payload = json.loads(
        (SITE / "data/curator-stats.json").read_text(encoding="utf-8")
    )
    if payload != build_curator_payload(ROOT):
        fail("curator-stats.json is stale relative to the governed queue")
    expected = {
        "schemaVersion",
        "totalMaterialised",
        "open",
        "completed",
        "actionCount",
        "byStage",
        "openByOrigin",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        fail("curator-stats.json must use the closed aggregate field set")
    integer_fields = (
        payload["totalMaterialised"],
        payload["open"],
        payload["completed"],
        payload["actionCount"],
    )
    if any(type(value) is not int or value < 0 for value in integer_fields):
        fail("curator-stats.json top-level counts must be non-negative integers")
    by_stage = payload["byStage"]
    by_origin = payload["openByOrigin"]
    if not isinstance(by_stage, dict) or set(by_stage) != {
        "metadataFix",
        "manualReview",
        "abstractReview",
        "legacyRejectionReview",
    }:
        fail("curator-stats.json has an invalid stage aggregate")
    if not isinstance(by_origin, dict) or set(by_origin) != {"legacy", "daily"}:
        fail("curator-stats.json has an invalid origin aggregate")
    if any(
        type(value) is not int or value < 0
        for value in (*by_stage.values(), *by_origin.values())
    ):
        fail("curator-stats.json nested counts must be non-negative integers")
    if sum(by_stage.values()) != payload["open"]:
        fail("curator-stats.json stage counts do not sum to open")
    if sum(by_origin.values()) != payload["open"]:
        fail("curator-stats.json origin counts do not sum to open")
    if payload["open"] + payload["completed"] != payload["totalMaterialised"]:
        fail("curator-stats.json open/completed counts do not reconcile")
    return payload


def validate_curator_options() -> dict[str, object]:
    payload = json.loads(
        (SITE / "data/curator-options.json").read_text(encoding="utf-8")
    )
    if payload != build_curator_options(ROOT):
        fail("curator-options.json is stale relative to the controlled registries")
    expected = {
        "schemaVersion",
        "screeningStages",
        "decisions",
        "confidenceLevels",
        "exclusionReasons",
        "topics",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        fail("curator-options.json must use the closed controlled field set")
    for key in expected - {"schemaVersion"}:
        rows = payload[key]
        if not isinstance(rows, list) or not rows:
            fail(f"curator-options.json {key} must be a non-empty list")
        codes = [row.get("code") for row in rows if isinstance(row, dict)]
        if len(codes) != len(rows) or "" in codes or len(codes) != len(set(codes)):
            fail(f"curator-options.json {key} contains an invalid or duplicate code")
    rendered = json.dumps(payload).lower()
    for value in ("candidate_id", "github_issue", "actor", "rationale", "evidence_basis"):
        if re.search(rf'"{re.escape(value)}"\s*:', rendered):
            fail(f"curator-options.json contains candidate or reviewer field: {value}")
    return payload


def validate_assets() -> None:
    javascript = (SITE / "app.js").read_text(encoding="utf-8")
    if re.search(r"\.innerHTML\s*=|insertAdjacentHTML", javascript):
        fail("JavaScript must not inject bibliographic metadata as HTML")
    if 'fetch("./data/archive.json")' not in javascript:
        fail("Site does not load the generated archive dataset")
    if "replaceChildren" not in javascript or "textContent" not in javascript:
        fail("Site must render untrusted metadata through DOM text nodes")
    for required in (
        "No publications are currently public",
        "pending publication review, withholding, or withdrawal",
        "No publications match these filters",
    ):
        if required not in javascript:
            fail(f"app.js missing governed empty-state copy: {required}")
    for unsupported_inference in (
        "Screening is still in progress",
        "No work currently has independent publication approval",
    ):
        if unsupported_inference in javascript:
            fail(f"app.js infers an ungoverned empty-state reason: {unsupported_inference}")

    css = (SITE / "styles.css").read_text(encoding="utf-8")
    for required in (
        ":focus-visible",
        "outline: 3px solid #fff",
        "box-shadow: 0 0 0 6px var(--ink)",
        "prefers-reduced-motion: reduce",
    ):
        if required not in css:
            fail(f"styles.css missing accessibility safeguard: {required}")

    curator = (SITE / "curate.html").read_text(encoding="utf-8")
    if re.search(r"<input\b[^>]*type=[\"']password[\"']", curator, re.I):
        fail("curate.html must never collect a password")
    if re.search(r"<(?:input|textarea)\b[^>]*(?:name|id)=[\"'][^\"']*(?:token|secret|password)", curator, re.I):
        fail("curate.html contains a credential-shaped input")
    if re.search(r"<form\b[^>]*\baction=", curator, re.I):
        fail("curate.html form must submit only through the authenticated JavaScript client")
    for private_registry_reference in ("data/registry", "papers.csv"):
        if private_registry_reference in curator:
            fail(
                "curate.html must not link directly to governed registry data: "
                f"{private_registry_reference}"
            )
    for phrase in (
        "GitHub Actions",
        "personal access token",
        "curation.yml",
        "APPLY",
        "candidate_decision.yml",
        "curation%3Aqueue",
        "Una decisione modifica la coda, non pubblica il paper",
        "Accedi con GitHub",
        "Invia la decisione",
        "GitHub App curatoriale",
    ):
        if phrase not in curator:
            fail(f"curate.html missing curator guidance: {phrase}")
    if re.search(r"E0(?:R1)?-[A-Z]\d{3}", curator):
        fail("curate.html must not expose a candidate record")

    curator_javascript = (SITE / "curator.js").read_text(encoding="utf-8")
    if re.search(r"\.innerHTML\s*=|insertAdjacentHTML", curator_javascript):
        fail("curator.js must not inject data as HTML")
    for required in (
        'fetch("./data/curator-stats.json")',
        'fetch("./data/research-stats.json")',
        'fetch("./data/curator-options.json")',
        'apiFetch("/api/session")',
        'apiFetch("/api/candidates")',
        'apiFetch("/api/decisions"',
        "sessionStorage",
        "history.replaceState",
        "crypto.randomUUID",
        "reportValidity",
        "replaceChildren",
        "textContent",
        "legacyRejectionReview",
        "openByOrigin",
        "lastRunStatus",
    ):
        if required not in curator_javascript:
            fail(f"curator.js missing safe aggregate rendering: {required}")
    for forbidden in (
        "data/curation",
        "review_queue",
        "api.github.com",
        "GITHUB_CLIENT_SECRET",
        "GITHUB_PRIVATE_KEY",
        "localStorage",
    ):
        if forbidden in curator_javascript:
            fail(f"curator.js crosses the public candidate boundary: {forbidden}")

    curator_config = (SITE / "curator-config.js").read_text(encoding="utf-8")
    if "CURATOR_APP_CONFIG" not in curator_config or "apiBaseUrl" not in curator_config:
        fail("curator-config.js lacks the reviewed API endpoint contract")
    for forbidden in ("clientSecret", "GITHUB_CLIENT_SECRET", "SESSION_SECRET", "ghu_"):
        if forbidden in curator_config:
            fail(f"curator-config.js contains forbidden secret material: {forbidden}")

    statistics = (SITE / "stats.html").read_text(encoding="utf-8")
    statistics_flat = " ".join(statistics.split()).lower()
    for phrase in (
        "Nuovo non significa eleggibile",
        "Una ricerca non riuscita non vale zero",
        "La sorveglianza non misura la saturazione",
        "issues/30",
    ):
        if phrase.lower() not in statistics_flat:
            fail(f"stats.html missing interpretation safeguard: {phrase}")

    stats_javascript = (SITE / "stats.js").read_text(encoding="utf-8")
    if re.search(r"\.innerHTML\s*=|insertAdjacentHTML", stats_javascript):
        fail("stats.js must not inject ledger data as HTML")
    for required in (
        'fetch("./data/research-stats.json")',
        "replaceChildren",
        "textContent",
        "completed.length < 8",
        "calendarWindow(rows, 30)",
        "sourceCompletionRate",
    ):
        if required not in stats_javascript:
            fail(f"stats.js missing rendering safeguard: {required}")


def main() -> None:
    validate_pages()
    count = validate_payload()
    metric_days = validate_statistics()
    curator_stats = validate_curator_statistics()
    curator_options = validate_curator_options()
    validate_assets()
    print(
        "[OK] Static site validation passed: "
        f"{count} public record(s), {metric_days} daily metric row(s), "
        f"{curator_stats['open']} open curator item(s), "
        f"{len(curator_options['decisions'])} curator decision option(s)."
    )


if __name__ == "__main__":
    try:
        main()
    except (MetricsError, OSError, json.JSONDecodeError, ValueError) as exc:
        fail(str(exc))
