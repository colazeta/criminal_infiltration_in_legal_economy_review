#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "scripts/ontology/validate_ontology.py"
text = path.read_text(encoding="utf-8")
old = '''    for schema, version, names in ((current, 3, ["Exa"]), (retained_v2, 2, ["Exa"]), (legacy, 1, ["Consensus", "Exa"])):
        properties = schema["properties"]
        if properties["schema_version"]["const"] != version or properties["expected_sources"]["items"]["enum"] != names:
            fail("surveillance_schema_source_drift")
        for key in ("expected_sources", "sources"):
            if properties[key]["minItems"] != len(names) or properties[key]["maxItems"] != len(names):
                fail("surveillance_schema_cardinality_drift")
'''
new = '''    source_contracts = (
        (current, 3, ["Exa", "Parallel Search"], 1),
        (retained_v2, 2, ["Exa"], 1),
        (legacy, 1, ["Consensus", "Exa"], 2),
    )
    for schema, version, names, cardinality in source_contracts:
        properties = schema["properties"]
        if properties["schema_version"]["const"] != version or properties["expected_sources"]["items"]["enum"] != names:
            fail("surveillance_schema_source_drift")
        for key in ("expected_sources", "sources"):
            if properties[key]["minItems"] != cardinality or properties[key]["maxItems"] != cardinality:
                fail("surveillance_schema_cardinality_drift")
'''
if old not in text:
    raise SystemExit("ontology source-contract anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
