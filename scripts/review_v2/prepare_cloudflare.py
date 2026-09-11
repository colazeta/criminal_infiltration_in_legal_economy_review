#!/usr/bin/env python3
"""Provision empty private V2 resources with the existing authorised deploy token.

No legacy data or secrets are copied. No review or runner is activated.
Stops on insufficient API permissions; never alters account permissions/plans.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
NAME = "criminal-infiltration-review-v2"
_resolved_account = None


def request_api(path, *, method="GET", payload=None, family="account"):
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not token:
        raise RuntimeError("Cloudflare deploy credential unavailable")
    request = Request(f"https://api.cloudflare.com/client/v4/{path}",
                      data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as error:
        # Never echo response bodies, request headers, account IDs or secrets into CI logs.
        raise RuntimeError(f"Cloudflare {family} permission/request failure: HTTP {error.code}") from None
    if not result.get("success"):
        raise RuntimeError(f"Cloudflare {family} operation failed")
    return result.get("result")


def resolve_account():
    global _resolved_account
    if _resolved_account:
        return _resolved_account
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not account:
        accounts = request_api("accounts?per_page=50&page=1")
        # Match Wrangler's single-account discovery; never choose among accounts.
        if not isinstance(accounts, list) or len(accounts) != 1:
            raise RuntimeError("A unique Cloudflare account could not be verified; configure CLOUDFLARE_ACCOUNT_ID")
        account = accounts[0].get("id", "")
    if not re.fullmatch(r"[a-f0-9]{32}", account):
        raise RuntimeError("Cloudflare account identifier is invalid")
    _resolved_account = account
    return account


def api(resource, *, method="GET", payload=None):
    return request_api(f"accounts/{resolve_account()}/{resource}", method=method, payload=payload, family=resource.split("/")[0])


def prepare(output, *, storage_only=False):
    matches = []
    for page in range(1, 101):
        databases = api(f"d1/database?per_page=100&page={page}")
        matches.extend(d for d in databases if d["name"] == NAME)
        if len(databases) < 100:
            break
    else:
        raise RuntimeError("D1 inventory pagination incomplete")
    if len(matches) > 1:
        raise RuntimeError("D1 resource name is ambiguous")
    database = matches[0] if matches else api("d1/database", method="POST", payload={"name": NAME})
    database_id = database["uuid"]
    sql = (ROOT / "curator-app/migrations/0001_review_v2.sql").read_text()
    digest = hashlib.sha256(sql.encode()).hexdigest()
    query = f"d1/database/{database_id}/query"
    tables = api(query, method="POST", payload={"sql": "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('reviews','cile_schema_versions')"})[0]["results"]
    names = {t["name"] for t in tables}
    if "reviews" in names:
        if "cile_schema_versions" not in names:
            raise RuntimeError("Existing database has no verified migration receipt; manual inspection required")
        recorded = api(query, method="POST", payload={"sql": "SELECT sha256 FROM cile_schema_versions WHERE version='0001'"})[0]["results"]
        if recorded != [{"sha256": digest}]:
            raise RuntimeError("Applied migration differs; an additive migration is required")
    else:
        # D1 executes multi-statement requests as a batch. No scientific data INSERT is present.
        migration = sql.replace("PRAGMA foreign_keys = ON;", "") + "\nCREATE TABLE cile_schema_versions(version TEXT PRIMARY KEY,sha256 TEXT NOT NULL);\nINSERT INTO cile_schema_versions VALUES ('0001','" + digest + "');"
        api(query, method="POST", payload={"sql": migration})
    for path in sorted((ROOT / "curator-app/migrations").glob("*.sql")):
        version = path.name.split("_", 1)[0]
        if version == "0001":
            continue
        sql = path.read_text()
        digest = hashlib.sha256(sql.encode()).hexdigest()
        recorded = api(query, method="POST", payload={"sql": "SELECT sha256 FROM cile_schema_versions WHERE version=?", "params": [version]})[0]["results"]
        if recorded:
            if recorded != [{"sha256": digest}]:
                raise RuntimeError("Applied additive migration differs; manual inspection required")
        else:
            migration = sql + "\nINSERT INTO cile_schema_versions VALUES ('" + version + "','" + digest + "');"
            api(query, method="POST", payload={"sql": migration})
    buckets = api("r2/buckets")
    if not any(b["name"] == NAME for b in buckets.get("buckets", [])):
        api("r2/buckets", method="POST", payload={"name": NAME})
    # R2 is private by default. Fail if a pre-existing bucket has a public development URL.
    access = api(f"r2/buckets/{NAME}/domains/managed")
    if access.get("enabled"):
        raise RuntimeError("Evidence bucket has public access enabled; refusing to bind it")
    custom = api(f"r2/buckets/{NAME}/domains/custom")
    if custom.get("domains"):
        raise RuntimeError("Evidence bucket has public custom domains; refusing to bind it")
    if storage_only:
        config = {
            "d1_databases": [{"binding": "REVIEW_DB", "database_name": NAME, "database_id": database_id}],
            "r2_buckets": [{"binding": "REVIEW_EVIDENCE", "bucket_name": NAME}],
            "triggers": {"crons": ["*/15 * * * *"]},
        }
        Path(output).write_text(json.dumps(config, indent=2) + "\n")
        print("Private storage prepared without discovery queues. Enrichment remains explicitly gated.")
        return
    queues = []
    for page in range(1, 101):
        part = api(f"queues?per_page=100&page={page}")
        queues.extend(part)
        if len(part) < 100:
            break
    else:
        raise RuntimeError("Queue inventory pagination incomplete")
    for queue_name in [NAME, NAME + "-dead-letter"]:
        if not any(q["queue_name"] == queue_name for q in queues):
            api("queues", method="POST", payload={"queue_name": queue_name})
    config = {
        "d1_databases": [{"binding": "REVIEW_DB", "database_name": NAME, "database_id": database_id}],
        "r2_buckets": [{"binding": "REVIEW_EVIDENCE", "bucket_name": NAME}],
        "queues": {"producers": [{"binding": "REVIEW_JOBS", "queue": NAME}],
                   "consumers": [{"queue": NAME, "max_batch_size": 1, "max_retries": 3, "dead_letter_queue": NAME + "-dead-letter"}]},
        "triggers": {"crons": ["*/15 * * * *"]},
    }
    Path(output).write_text(json.dumps(config, indent=2) + "\n")
    print("Private V2 storage and queue prepared. Review rows: not created. Runner: disabled.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--storage-only", action="store_true", help="Do not require discovery queues")
    args = parser.parse_args()
    try:
        prepare(args.output, storage_only=args.storage_only)
    except (RuntimeError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"V2 preparation blocked: {error}") from None
