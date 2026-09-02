#!/usr/bin/env python3
"""Classify curator candidates as open, restricted, or unknown.

This is a mechanical access layer, separate from eligibility and abstract coverage.
It persists no article text. `restricted` is only assigned when a matched scholarly
provider explicitly reports closed/non-OA access and no verified open manifestation
is already known. Observed anonymous full-text access takes precedence over metadata.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "data" / "curation" / "review_queue.csv"
RETRIEVAL_PATH = ROOT / "data" / "curation" / "retrieval_coverage.csv"
ABSTRACT_PATH = ROOT / "data" / "curation" / "abstract_coverage.csv"
COVERAGE_PATH = ROOT / "data" / "curation" / "access_coverage.csv"
OPENALEX_API = "https://api.openalex.org"
UNPAYWALL_API = "https://api.unpaywall.org/v2"
PROBE_BYTES = 500_000

FIELDS = [
    "candidate_id",
    "title",
    "doi",
    "access_status",
    "access_kind",
    "access_url",
    "evidence_source",
    "evidence_detail",
    "checked_at",
    "notes",
]
STATUSES = {"open", "restricted", "unknown"}


class AccessCoverageError(ValueError):
    pass


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


def year_compatible(requested: object, candidate: object) -> bool:
    try:
        left = int(str(requested))
        right = int(str(candidate))
    except (TypeError, ValueError):
        return True
    return abs(left - right) <= 1


def request_json(url: str, attempts: int = 3) -> tuple[Any | None, str]:
    last_error = ""
    for attempt in range(1, attempts + 1):
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "criminal-infiltration-access-classifier/1.0",
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


def safe_probe_url(value: object) -> str:
    candidate = clean(value, 2000)
    if not candidate:
        return ""
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    if parsed.scheme != "https:" or not parsed.netloc:
        return ""
    host = (parsed.hostname or "").lower()
    if not host or host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        return ""
    if host == "doi.org" or host.endswith(".doi.org"):
        return ""
    ipv4 = host.split(".")
    if len(ipv4) == 4 and all(part.isdigit() for part in ipv4):
        octets = [int(part) for part in ipv4]
        if any(value > 255 for value in octets):
            return ""
        if (
            octets[0] in {0, 10, 127}
            or (octets[0] == 169 and octets[1] == 254)
            or (octets[0] == 172 and 16 <= octets[1] <= 31)
            or (octets[0] == 192 and octets[1] == 168)
        ):
            return ""
    return candidate


def extract_document_title(source: str) -> str:
    patterns = [
        r'<meta\b[^>]*(?:name|property)=["\'](?:citation_title|dc.title|dcterms.title|og:title)["\'][^>]*content=["\']([^"\']+)',
        r'<meta\b[^>]*content=["\']([^"\']+)["\'][^>]*(?:name|property)=["\'](?:citation_title|dc.title|dcterms.title|og:title)["\']',
        r'<article-title\b[^>]*>([\s\S]*?)</article-title>',
        r'<title\b[^>]*>([\s\S]*?)</title>',
    ]
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if not match:
            continue
        title = clean(re.sub(r"<[^>]+>", " ", match.group(1)), 1200)
        if title:
            return title
    return ""


def probe_public_full_text(url: object, requested_title: object) -> tuple[bool, str]:
    """Verify anonymous full-text access without retaining the response body."""
    target = safe_probe_url(url)
    if not target:
        return False, ""
    request = Request(
        target,
        headers={
            "Accept": "application/pdf,application/xml,text/xml,text/html,application/xhtml+xml,*/*;q=0.2",
            "Range": f"bytes=0-{PROBE_BYTES - 1}",
            "User-Agent": "criminal-infiltration-access-classifier/1.0",
        },
    )
    try:
        with urlopen(request, timeout=25) as response:
            if response.status not in {200, 206}:
                return False, f"HTTP {response.status}"
            content_type = clean(response.headers.get("Content-Type"), 200).lower()
            payload = response.read(PROBE_BYTES)
            final_url = clean(response.geturl(), 2000)
    except HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except (URLError, TimeoutError, ValueError) as exc:
        return False, exc.__class__.__name__

    if "pdf" in content_type or payload.startswith(b"%PDF"):
        return True, f"Anonymous full-text probe returned PDF ({content_type or 'application/pdf'})."

    if not any(marker in content_type for marker in ("html", "xml", "text/")):
        return False, f"Unsupported content type: {content_type or 'unknown'}"

    source = payload.decode("utf-8", errors="replace")
    matched_title = extract_document_title(source)
    title_score = title_similarity(requested_title, matched_title) if matched_title else 0.0
    lower = source.lower()
    path = urlsplit(final_url or target).path.lower()
    explicit_full_text = (
        "/full-xml/" in path
        or ("<article" in lower and any(marker in lower for marker in ("<body", "<sec", "<ref-list", "<back")))
        or ("<body" in lower and "references" in lower and len(source) >= 20_000)
    )
    if explicit_full_text and matched_title and title_score >= 0.72:
        return True, f"Anonymous full-text probe returned {content_type or 'HTML/XML'} and matched the candidate title (score {title_score:.3f})."
    return False, f"Public response did not verify full text (title score {title_score:.3f})."


def openalex_match(row: dict[str, str]) -> tuple[dict[str, Any] | None, str]:
    doi = normalise_doi(row.get("doi"))
    if doi:
        payload, error = request_json(f"{OPENALEX_API}/works/https://doi.org/{quote(doi, safe='/:()')}")
        return (payload if isinstance(payload, dict) else None), error

    query: dict[str, str] = {"search": row["title"], "per_page": "5"}
    if row.get("year"):
        query["filter"] = f"publication_year:{row['year']}"
    payload, error = request_json(f"{OPENALEX_API}/works?{urlencode(query)}")
    works = payload.get("results", []) if isinstance(payload, dict) else []
    valid = [
        work for work in works
        if isinstance(work, dict)
        and title_similarity(row["title"], work.get("display_name") or work.get("title")) >= 0.88
        and year_compatible(row.get("year"), work.get("publication_year"))
    ]
    valid.sort(
        key=lambda work: title_similarity(row["title"], work.get("display_name") or work.get("title")),
        reverse=True,
    )
    return (valid[0] if valid else None), error


def unpaywall_match(row: dict[str, str], email: str) -> tuple[dict[str, Any] | None, str]:
    doi = normalise_doi(row.get("doi"))
    if not email or not doi:
        return None, ""
    payload, error = request_json(
        f"{UNPAYWALL_API}/{quote(doi, safe='/:()')}?{urlencode({'email': email})}"
    )
    return (payload if isinstance(payload, dict) else None), error


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def by_candidate(path: Path) -> dict[str, dict[str, str]]:
    return {row.get("candidate_id", ""): row for row in read_csv(path) if row.get("candidate_id")}


def first_url(*values: object) -> str:
    for value in values:
        url = clean(value, 2000)
        if url.startswith("https://"):
            return url
    return ""


def classify_row(
    row: dict[str, str],
    retrieval: dict[str, str] | None,
    abstract: dict[str, str] | None,
    checked_at: str,
) -> dict[str, str]:
    retrieval = retrieval or {}
    abstract = abstract or {}
    notes: list[str] = []

    # Strongest practical evidence: our zero-cost backfill successfully downloaded
    # and parsed the governed PDF without credentials.
    if abstract.get("coverage_status") == "available" and abstract.get("match_type") == "resolved_pdf":
        url = first_url(abstract.get("article_url"), retrieval.get("full_text_url"), retrieval.get("best_url"))
        return access_row(
            row, "open", "public_full_text", url,
            "Governed PDF fetch", "Unauthenticated PDF download and local text extraction succeeded.",
            checked_at, "",
        )

    # Existing resolver already labels OA locations from OpenAlex/Unpaywall.
    oa_url = first_url(retrieval.get("open_access_url"))
    if oa_url:
        return access_row(
            row, "open", "open_access_location", oa_url,
            "Retrieval coverage", "Resolver recorded an explicit open-access location.",
            checked_at, "",
        )

    # Observed anonymous full-text access outranks provider-level OA metadata. This
    # catches public publisher XML/HTML manifestations such as SAGE full-xml pages.
    full_text_url = first_url(retrieval.get("full_text_url"))
    if full_text_url:
        publicly_accessible, probe_detail = probe_public_full_text(full_text_url, row.get("title"))
        if publicly_accessible:
            return access_row(
                row, "open", "public_full_text", full_text_url,
                "Full-text probe", probe_detail,
                checked_at, "",
            )
        if probe_detail:
            notes.append(f"Full-text probe:{probe_detail}")

    openalex, oa_error = openalex_match(row)
    if oa_error:
        notes.append(f"OpenAlex:{oa_error}")
    oa_closed = False
    oa_detail = ""
    if openalex:
        open_access = openalex.get("open_access") if isinstance(openalex.get("open_access"), dict) else {}
        is_oa = bool(open_access.get("is_oa"))
        oa_status = clean(open_access.get("oa_status"), 80).lower()
        best = openalex.get("best_oa_location") if isinstance(openalex.get("best_oa_location"), dict) else {}
        oa_url = first_url(
            open_access.get("oa_url"),
            best.get("pdf_url"),
            best.get("landing_page_url"),
        )
        if is_oa or oa_status in {"gold", "green", "hybrid", "bronze"}:
            return access_row(
                row, "open", f"openalex_{oa_status or 'oa'}", oa_url,
                "OpenAlex", f"OpenAlex open_access reports is_oa=true / oa_status={oa_status or 'open'}.",
                checked_at, "; ".join(notes),
            )
        oa_closed = oa_status == "closed" or ("is_oa" in open_access and not bool(open_access.get("is_oa")))
        if oa_closed:
            oa_detail = f"OpenAlex open_access reports is_oa=false / oa_status={oa_status or 'closed'}."

    email = clean(os.environ.get("UNPAYWALL_EMAIL"), 320)
    unpaywall, up_error = unpaywall_match(row, email)
    if up_error:
        notes.append(f"Unpaywall:{up_error}")
    up_closed = False
    up_detail = ""
    if unpaywall:
        if bool(unpaywall.get("is_oa")):
            best = unpaywall.get("best_oa_location") if isinstance(unpaywall.get("best_oa_location"), dict) else {}
            url = first_url(best.get("url_for_pdf"), best.get("url_for_landing_page"), best.get("url"), unpaywall.get("doi_url"))
            return access_row(
                row, "open", "unpaywall_oa", url,
                "Unpaywall", "Unpaywall reports is_oa=true.",
                checked_at, "; ".join(notes),
            )
        if "is_oa" in unpaywall and not bool(unpaywall.get("is_oa")):
            up_closed = True
            up_detail = "Unpaywall reports is_oa=false."

    # Restricted is positive evidence, never a failure-to-find inference.
    if up_closed or oa_closed:
        evidence = "; ".join(part for part in (oa_detail, up_detail) if part)
        source = "OpenAlex + Unpaywall" if oa_closed and up_closed else ("Unpaywall" if up_closed else "OpenAlex")
        return access_row(
            row, "restricted", "closed_metadata", first_url(retrieval.get("landing_url"), retrieval.get("doi_url"), retrieval.get("best_url")),
            source, evidence, checked_at, "; ".join(notes),
        )

    if not email:
        notes.append("Unpaywall:not_configured")
    return access_row(
        row, "unknown", "insufficient_evidence", first_url(retrieval.get("best_url"), retrieval.get("doi_url")),
        "Access classifier", "No verified open manifestation and no explicit closed-access signal were available.",
        checked_at, "; ".join(notes),
    )


def access_row(
    row: dict[str, str],
    status: str,
    kind: str,
    url: str,
    source: str,
    detail: str,
    checked_at: str,
    notes: str,
) -> dict[str, str]:
    return {
        "candidate_id": row["candidate_id"],
        "title": clean(row.get("title"), 1200),
        "doi": normalise_doi(row.get("doi")),
        "access_status": status,
        "access_kind": kind,
        "access_url": url,
        "evidence_source": source,
        "evidence_detail": clean(detail, 1200),
        "checked_at": checked_at,
        "notes": clean(notes, 1200),
    }


def validate_coverage(queue: list[dict[str, str]], coverage: list[dict[str, str]], fields: list[str]) -> dict[str, int]:
    if fields != FIELDS:
        raise AccessCoverageError(f"access_fields_mismatch:{fields}")
    if len(queue) != len(coverage):
        raise AccessCoverageError(f"access_count_mismatch:{len(coverage)}:{len(queue)}")
    counts = {status: 0 for status in STATUSES}
    for index, (candidate, row) in enumerate(zip(queue, coverage, strict=True)):
        if row.get("candidate_id") != candidate.get("candidate_id"):
            raise AccessCoverageError(f"access_order_mismatch:{index}:{row.get('candidate_id')}:{candidate.get('candidate_id')}")
        status = row.get("access_status", "")
        if status not in STATUSES:
            raise AccessCoverageError(f"invalid_access_status:{row.get('candidate_id')}:{status}")
        if not row.get("checked_at"):
            raise AccessCoverageError(f"missing_checked_at:{row.get('candidate_id')}")
        if status in {"open", "restricted"} and not row.get("evidence_source"):
            raise AccessCoverageError(f"missing_access_evidence:{row.get('candidate_id')}")
        counts[status] += 1
    return {"total": len(coverage), **counts}


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output", type=Path, default=COVERAGE_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    queue = read_csv(QUEUE_PATH)
    if args.check:
        fields: list[str] = []
        rows: list[dict[str, str]] = []
        if args.output.exists():
            with args.output.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                fields = list(reader.fieldnames or [])
                rows = [dict(row) for row in reader]
        print(json.dumps(validate_coverage(queue, rows, fields), sort_keys=True))
        return

    retrieval = by_candidate(RETRIEVAL_PATH)
    abstract = by_candidate(ABSTRACT_PATH)
    coverage: list[dict[str, str]] = []
    for index, row in enumerate(queue, start=1):
        coverage.append(classify_row(row, retrieval.get(row["candidate_id"]), abstract.get(row["candidate_id"]), args.date))
        if index % 10 == 0 or index == len(queue):
            print(f"Access coverage: {index}/{len(queue)}")
        time.sleep(0.2)
    write_csv(coverage, args.output)
    print(json.dumps(validate_coverage(queue, coverage, FIELDS), sort_keys=True))


if __name__ == "__main__":
    main()
