#!/usr/bin/env python3
"""Resolve the best retrievable manifestation for every curator candidate.

This layer is deliberately separate from screening. It attempts bibliographic
and access resolution for 100% of rows in review_queue.csv and records an
explicit outcome even when no full text can be found.

Resolution order:
1. direct full-text links already discovered;
2. OpenAlex locations / best OA location;
3. Crossref landing and full-text links;
4. Unpaywall OA locations when UNPAYWALL_EMAIL is configured;
5. DOI resolver;
6. original discovery/source links;
7. explicit unresolved state.

The resolver never infers eligibility and never downloads or stores article
full text. It stores URLs and retrieval metadata only.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "data" / "curation" / "review_queue.csv"
COVERAGE_PATH = ROOT / "data" / "curation" / "retrieval_coverage.csv"
OPENALEX_API = "https://api.openalex.org"
CROSSREF_API = "https://api.crossref.org/v1"
UNPAYWALL_API = "https://api.unpaywall.org/v2"

FIELDS = [
    "candidate_id",
    "title",
    "doi",
    "resolution_status",
    "best_url",
    "best_url_kind",
    "full_text_url",
    "open_access_url",
    "landing_url",
    "doi_url",
    "source_urls",
    "resolved_doi",
    "resolution_sources",
    "match_method",
    "match_confidence",
    "checked_at",
    "notes",
]
STATUSES = {
    "full_text",
    "open_access_landing",
    "landing_page",
    "doi_only",
    "source_link_only",
    "unresolved",
}
URL_KINDS = {
    "full_text",
    "open_access",
    "landing",
    "doi",
    "source",
    "none",
}


class ResolutionError(ValueError):
    """Raised for structural resolver errors, never for upstream absence."""


def clean(value: object, maximum: int = 2000) -> str:
    return " ".join(str(value or "").split())[:maximum]


def normalise_doi(value: object) -> str:
    doi = clean(value, 300).lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return doi.strip()


def normalise_title(value: object) -> str:
    text = unicodedata.normalize("NFKD", clean(value, 1200))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def title_similarity(left: object, right: object) -> float:
    a = {token for token in normalise_title(left).split() if len(token) > 2}
    b = {token for token in normalise_title(right).split() if len(token) > 2}
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def safe_url(value: object) -> str:
    candidate = clean(value, 2000)
    if not candidate:
        return ""
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return candidate


def split_urls(value: object) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in str(value or "").split("; "):
        url = safe_url(raw.strip())
        if url and url not in seen:
            result.append(url)
            seen.add(url)
    return result


def looks_like_pdf(url: str) -> bool:
    path = urlsplit(url).path.lower()
    return path.endswith(".pdf") or "pdf=render" in url.lower() or "/pdf/" in path


def request_json(url: str, *, attempts: int = 3) -> tuple[Any | None, str]:
    last_error = ""
    for attempt in range(1, attempts + 1):
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "criminal-infiltration-retrieval-resolver/1.0",
            },
        )
        try:
            with urlopen(request, timeout=25) as response:
                return json.load(response), ""
        except HTTPError as exc:
            if exc.code == 404:
                return None, ""
            last_error = f"HTTP {exc.code}"
            if exc.code not in {429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc.__class__.__name__
        if attempt < attempts:
            time.sleep(attempt * 1.5)
    return None, last_error


def year_compatible(requested: object, candidate: object) -> bool:
    try:
        left = int(str(requested))
        right = int(str(candidate))
    except (TypeError, ValueError):
        return True
    return abs(left - right) <= 1


def openalex_match(row: dict[str, str], api_key: str) -> tuple[dict[str, Any] | None, str, str]:
    doi = normalise_doi(row.get("doi"))
    if doi:
        target = f"{OPENALEX_API}/works/https://doi.org/{quote(doi, safe='/:()')}"
        if api_key:
            target += "?" + urlencode({"api_key": api_key})
        payload, error = request_json(target)
        return (payload if isinstance(payload, dict) else None), "doi", error

    query: dict[str, str] = {"search": row["title"], "per_page": "5"}
    if row.get("year"):
        query["filter"] = f"publication_year:{row['year']}"
    if api_key:
        query["api_key"] = api_key
    payload, error = request_json(f"{OPENALEX_API}/works?{urlencode(query)}")
    works = payload.get("results", []) if isinstance(payload, dict) else []
    valid = [
        work
        for work in works
        if isinstance(work, dict)
        and title_similarity(row["title"], work.get("display_name") or work.get("title")) >= 0.86
        and year_compatible(row.get("year"), work.get("publication_year"))
    ]
    valid.sort(
        key=lambda work: title_similarity(row["title"], work.get("display_name") or work.get("title")),
        reverse=True,
    )
    return (valid[0] if valid else None), "title_year", error


def crossref_year(message: dict[str, Any]) -> object:
    for field in ("published", "issued", "created"):
        parts = message.get(field, {}).get("date-parts", []) if isinstance(message.get(field), dict) else []
        if parts and parts[0]:
            return parts[0][0]
    return ""


def crossref_match(row: dict[str, str]) -> tuple[dict[str, Any] | None, str, str]:
    doi = normalise_doi(row.get("doi"))
    if doi:
        payload, error = request_json(f"{CROSSREF_API}/works/{quote(doi, safe='')}" )
        message = payload.get("message") if isinstance(payload, dict) else None
        return (message if isinstance(message, dict) else None), "doi", error

    query = {"query.bibliographic": row["title"], "rows": "5"}
    if row.get("year"):
        query["filter"] = f"from-pub-date:{row['year']}-01-01,until-pub-date:{row['year']}-12-31"
    payload, error = request_json(f"{CROSSREF_API}/works?{urlencode(query)}")
    message = payload.get("message") if isinstance(payload, dict) else None
    works = message.get("items", []) if isinstance(message, dict) else []
    valid = []
    for work in works:
        if not isinstance(work, dict):
            continue
        titles = work.get("title") or []
        title = titles[0] if isinstance(titles, list) and titles else titles
        if title_similarity(row["title"], title) < 0.9:
            continue
        if not year_compatible(row.get("year"), crossref_year(work)):
            continue
        valid.append(work)
    valid.sort(
        key=lambda work: title_similarity(
            row["title"],
            (work.get("title") or [""])[0] if isinstance(work.get("title"), list) else work.get("title"),
        ),
        reverse=True,
    )
    return (valid[0] if valid else None), "title_year", error


def unpaywall_match(row: dict[str, str], email: str) -> tuple[dict[str, Any] | None, str, str]:
    if not email:
        return None, "not_configured", ""
    doi = normalise_doi(row.get("doi"))
    if doi:
        payload, error = request_json(
            f"{UNPAYWALL_API}/{quote(doi, safe='/:()')}?{urlencode({'email': email})}"
        )
        return (payload if isinstance(payload, dict) else None), "doi", error

    query = urlencode({"query": f'"{row["title"]}"', "email": email})
    payload, error = request_json(f"{UNPAYWALL_API}/search?{query}")
    results = payload.get("results", []) if isinstance(payload, dict) else []
    valid: list[dict[str, Any]] = []
    for item in results:
        work = item.get("response") if isinstance(item, dict) else None
        if not isinstance(work, dict):
            continue
        if title_similarity(row["title"], work.get("title")) < 0.92:
            continue
        if not year_compatible(row.get("year"), work.get("year")):
            continue
        valid.append(work)
    valid.sort(key=lambda work: title_similarity(row["title"], work.get("title")), reverse=True)
    return (valid[0] if valid else None), "title_year", error


def add_choice(
    choices: list[tuple[int, str, str, str]],
    seen: set[str],
    priority: int,
    kind: str,
    url: object,
    source: str,
) -> None:
    safe = safe_url(url)
    if not safe or safe in seen:
        return
    choices.append((priority, kind, safe, source))
    seen.add(safe)


def resolve_row(row: dict[str, str], checked_at: str) -> dict[str, str]:
    choices: list[tuple[int, str, str, str]] = []
    seen: set[str] = set()
    sources: list[str] = []
    errors: list[str] = []
    match_methods: list[str] = []
    resolved_doi = normalise_doi(row.get("doi"))
    source_urls = split_urls(row.get("source_links"))

    for url in source_urls:
        add_choice(choices, seen, 0 if looks_like_pdf(url) else 50, "full_text" if looks_like_pdf(url) else "source", url, "discovery")

    openalex, oa_method, oa_error = openalex_match(row, clean(os.environ.get("OPENALEX_API_KEY"), 500))
    if oa_error:
        errors.append(f"OpenAlex:{oa_error}")
    if openalex:
        sources.append("OpenAlex")
        match_methods.append(f"OpenAlex:{oa_method}")
        resolved_doi = resolved_doi or normalise_doi(openalex.get("doi"))
        locations: list[dict[str, Any]] = []
        for value in (openalex.get("best_oa_location"), openalex.get("primary_location")):
            if isinstance(value, dict):
                locations.append(value)
        locations.extend(value for value in openalex.get("locations", []) if isinstance(value, dict))
        for location in locations:
            add_choice(choices, seen, 5, "full_text", location.get("pdf_url"), "OpenAlex")
            landing = location.get("landing_page_url")
            is_oa = bool(location.get("is_oa")) or location is openalex.get("best_oa_location")
            add_choice(choices, seen, 15 if is_oa else 30, "open_access" if is_oa else "landing", landing, "OpenAlex")

    crossref, cr_method, cr_error = crossref_match(row)
    if cr_error:
        errors.append(f"Crossref:{cr_error}")
    if crossref:
        sources.append("Crossref")
        match_methods.append(f"Crossref:{cr_method}")
        resolved_doi = resolved_doi or normalise_doi(crossref.get("DOI"))
        for link in crossref.get("link", []) if isinstance(crossref.get("link"), list) else []:
            if not isinstance(link, dict):
                continue
            add_choice(choices, seen, 8, "full_text", link.get("URL"), "Crossref")
        add_choice(choices, seen, 32, "landing", crossref.get("URL"), "Crossref")

    unpaywall, up_method, up_error = unpaywall_match(row, clean(os.environ.get("UNPAYWALL_EMAIL"), 500))
    if up_error:
        errors.append(f"Unpaywall:{up_error}")
    if unpaywall:
        sources.append("Unpaywall")
        match_methods.append(f"Unpaywall:{up_method}")
        resolved_doi = resolved_doi or normalise_doi(unpaywall.get("doi"))
        best = unpaywall.get("best_oa_location")
        if isinstance(best, dict):
            add_choice(choices, seen, 3, "full_text", best.get("url_for_pdf"), "Unpaywall")
            add_choice(choices, seen, 10, "open_access", best.get("url_for_landing_page") or best.get("url"), "Unpaywall")

    doi_url = f"https://doi.org/{resolved_doi}" if resolved_doi else ""
    add_choice(choices, seen, 40, "doi", doi_url, "DOI")
    choices.sort(key=lambda item: (item[0], item[2]))

    best = choices[0] if choices else (99, "none", "", "")
    full_text_url = next((url for _, kind, url, _ in choices if kind == "full_text"), "")
    open_access_url = next((url for _, kind, url, _ in choices if kind == "open_access"), "")
    landing_url = next((url for _, kind, url, _ in choices if kind == "landing"), "")

    if full_text_url:
        status = "full_text"
    elif open_access_url:
        status = "open_access_landing"
    elif landing_url:
        status = "landing_page"
    elif doi_url:
        status = "doi_only"
    elif source_urls:
        status = "source_link_only"
    else:
        status = "unresolved"

    methods = "; ".join(match_methods)
    confidence = "high" if any(method.endswith(":doi") for method in match_methods) else ("medium" if match_methods else "low")
    notes = "; ".join(errors)
    if not os.environ.get("UNPAYWALL_EMAIL"):
        notes = "; ".join(part for part in (notes, "Unpaywall:not_configured") if part)

    return {
        "candidate_id": row["candidate_id"],
        "title": clean(row.get("title"), 1200),
        "doi": normalise_doi(row.get("doi")),
        "resolution_status": status,
        "best_url": best[2],
        "best_url_kind": best[1],
        "full_text_url": full_text_url,
        "open_access_url": open_access_url,
        "landing_url": landing_url,
        "doi_url": doi_url,
        "source_urls": "; ".join(source_urls),
        "resolved_doi": resolved_doi,
        "resolution_sources": "; ".join(dict.fromkeys(sources)),
        "match_method": methods or "source_only",
        "match_confidence": confidence,
        "checked_at": checked_at,
        "notes": notes,
    }


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def valid_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def should_refresh(row: dict[str, str], existing: dict[str, str] | None, checked_at: str, max_age_days: int) -> bool:
    if not existing:
        return True
    if clean(existing.get("title")) != clean(row.get("title")):
        return True
    if normalise_doi(existing.get("doi")) != normalise_doi(row.get("doi")):
        return True
    if clean(existing.get("source_urls")) != "; ".join(split_urls(row.get("source_links"))):
        return True
    if not valid_iso_date(existing.get("checked_at", "")):
        return True
    age = (date.fromisoformat(checked_at) - date.fromisoformat(existing["checked_at"])).days
    return age >= max_age_days


def validate_coverage(queue_rows: list[dict[str, str]], rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    if fieldnames != FIELDS:
        raise ResolutionError("retrieval_coverage.csv header does not match the governed schema")
    queue_ids = [row.get("candidate_id", "") for row in queue_rows]
    coverage_ids = [row.get("candidate_id", "") for row in rows]
    if not queue_ids or "" in queue_ids or len(queue_ids) != len(set(queue_ids)):
        raise ResolutionError("review_queue.csv candidate IDs are invalid")
    if coverage_ids != queue_ids:
        raise ResolutionError("retrieval coverage must contain exactly one row per queue candidate in queue order")
    for row in rows:
        candidate_id = row["candidate_id"]
        if row.get("resolution_status") not in STATUSES:
            raise ResolutionError(f"{candidate_id}: invalid resolution status")
        if row.get("best_url_kind") not in URL_KINDS:
            raise ResolutionError(f"{candidate_id}: invalid best URL kind")
        for field in ("best_url", "full_text_url", "open_access_url", "landing_url", "doi_url"):
            value = row.get(field, "")
            if value and not safe_url(value):
                raise ResolutionError(f"{candidate_id}: {field} is not a valid HTTP(S) URL")
        if row["resolution_status"] == "unresolved" and row.get("best_url"):
            raise ResolutionError(f"{candidate_id}: unresolved row unexpectedly has best_url")
        if row["resolution_status"] != "unresolved" and not row.get("best_url"):
            raise ResolutionError(f"{candidate_id}: resolved row lacks best_url")
        if row["resolution_status"] == "full_text" and not row.get("full_text_url"):
            raise ResolutionError(f"{candidate_id}: full_text status lacks full_text_url")
        if not valid_iso_date(row.get("checked_at", "")):
            raise ResolutionError(f"{candidate_id}: checked_at is invalid")


def write_coverage(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def resolve_all(queue_path: Path, coverage_path: Path, checked_at: str, max_age_days: int, refresh_all: bool) -> dict[str, int]:
    queue_fields, queue_rows = read_csv(queue_path)
    if not queue_fields or not queue_rows:
        raise ResolutionError("review_queue.csv is missing or empty")
    coverage_fields, old_rows = read_csv(coverage_path)
    old = {row.get("candidate_id", ""): row for row in old_rows} if coverage_fields == FIELDS else {}

    resolved: list[dict[str, str]] = []
    refreshed = 0
    for index, row in enumerate(queue_rows, start=1):
        candidate_id = row.get("candidate_id", "")
        previous = old.get(candidate_id)
        if refresh_all or should_refresh(row, previous, checked_at, max_age_days):
            print(f"[{index}/{len(queue_rows)}] resolving {candidate_id}")
            resolved.append(resolve_row(row, checked_at))
            refreshed += 1
            time.sleep(0.08)
        else:
            resolved.append(previous)

    validate_coverage(queue_rows, resolved, FIELDS)
    write_coverage(coverage_path, resolved)
    counts = {status: 0 for status in STATUSES}
    for row in resolved:
        counts[row["resolution_status"]] += 1
    counts["total"] = len(resolved)
    counts["refreshed"] = refreshed
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--coverage", type=Path, default=COVERAGE_PATH)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--max-age-days", type=int, default=30)
    parser.add_argument("--refresh-all", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        checked_at = date.fromisoformat(args.date).isoformat()
    except ValueError as exc:
        raise SystemExit("--date must use YYYY-MM-DD") from exc

    queue_fields, queue_rows = read_csv(args.queue)
    if not queue_fields or not queue_rows:
        raise SystemExit("review queue is missing or empty")

    if args.check:
        coverage_fields, rows = read_csv(args.coverage)
        validate_coverage(queue_rows, rows, coverage_fields)
        result = {"total": len(rows), "unresolved": sum(row["resolution_status"] == "unresolved" for row in rows)}
    else:
        result = resolve_all(
            args.queue,
            args.coverage,
            checked_at,
            max(1, args.max_age_days),
            args.refresh_all,
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
