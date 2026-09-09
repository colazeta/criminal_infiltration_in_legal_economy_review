#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "scripts/validation/validate_repository.py"
text = path.read_text(encoding="utf-8")
old = '''    source_enum = run_schema["properties"]["expected_sources"]["items"].get("enum")
    if set(source_enum or []) != {"Exa"}:
        fail("Daily telemetry schema must enforce the governed active source set")
'''
new = '''    expected_sources_schema = run_schema["properties"]["expected_sources"]
    source_enum = expected_sources_schema["items"].get("enum")
    record_source_enum = run_schema["$defs"]["source"]["properties"]["source"].get("enum")
    governed_daily_sources = {"Exa", "Parallel Search"}
    if (
        set(source_enum or []) != governed_daily_sources
        or set(record_source_enum or []) != governed_daily_sources
        or expected_sources_schema.get("minItems") != 1
        or expected_sources_schema.get("maxItems") != 1
    ):
        fail("Daily telemetry schema must enforce the governed single-provider source set")
'''
if old not in text:
    raise SystemExit("validator anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
