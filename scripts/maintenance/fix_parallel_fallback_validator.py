#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "scripts/validation/validate_repository.py"
text = path.read_text(encoding="utf-8")
old_schema = '''    source_enum = run_schema["properties"]["expected_sources"]["items"].get("enum")
    if set(source_enum or []) != {"Exa"}:
        fail("Daily telemetry schema must enforce the governed active source set")
'''
new_schema = '''    expected_sources_schema = run_schema["properties"]["expected_sources"]
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
if old_schema not in text:
    raise SystemExit("schema validator anchor not found")
text = text.replace(old_schema, new_schema, 1)
old_phrase = '''    for phrase in (
        'ACTIVE_SOURCES = frozenset({"Exa"})',
        "summed(runs_subset",
'''
new_phrase = '''    for phrase in (
        'PRIMARY_SOURCE = "Exa"',
        'FALLBACK_SOURCE = "Parallel Search"',
        'ACTIVE_SOURCES = frozenset({PRIMARY_SOURCE, FALLBACK_SOURCE})',
        'SOURCE_SETS = {1: frozenset({"Consensus", "Exa"}), 2: frozenset({PRIMARY_SOURCE})}',
        "summed(runs_subset",
'''
if old_phrase not in text:
    raise SystemExit("metrics safeguard anchor not found")
text = text.replace(old_phrase, new_phrase, 1)
path.write_text(text, encoding="utf-8")
