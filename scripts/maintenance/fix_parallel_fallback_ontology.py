#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "scripts/ontology/validate_ontology.py"
text = path.read_text(encoding="utf-8")
old_contract = '''    for schema, version, names in ((current, 3, ["Exa"]), (retained_v2, 2, ["Exa"]), (legacy, 1, ["Consensus", "Exa"])):
        properties = schema["properties"]
        if properties["schema_version"]["const"] != version or properties["expected_sources"]["items"]["enum"] != names:
            fail("surveillance_schema_source_drift")
        for key in ("expected_sources", "sources"):
            if properties[key]["minItems"] != len(names) or properties[key]["maxItems"] != len(names):
                fail("surveillance_schema_cardinality_drift")
'''
new_contract = '''    source_contracts = (
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
if old_contract not in text:
    raise SystemExit("ontology source-contract anchor not found")
text = text.replace(old_contract, new_contract, 1)
old_registration = '''    registration_schema = load_json(ROOT / registration["run_schema"])
    if registration_schema["properties"]["schema_version"]["const"] != 3 or registration_schema["properties"]["expected_sources"]["items"]["enum"] != ["Exa"]:
        fail("invalid_registration_surveillance_schema")
'''
new_registration = '''    registration_schema = load_json(ROOT / registration["run_schema"])
    registration_sources = registration_schema["properties"]["expected_sources"]
    if (
        registration_schema["properties"]["schema_version"]["const"] != 3
        or registration_sources["items"]["enum"] != ["Exa", "Parallel Search"]
        or registration_sources["minItems"] != 1
        or registration_sources["maxItems"] != 1
    ):
        fail("invalid_registration_surveillance_schema")
'''
if old_registration not in text:
    raise SystemExit("registration surveillance anchor not found")
text = text.replace(old_registration, new_registration, 1)
path.write_text(text, encoding="utf-8")
