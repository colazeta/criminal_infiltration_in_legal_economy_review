import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_assessment_comparison_protocol_is_mapped_to_existing_profile_concepts():
    profile = json.loads((ROOT / 'ontology/cile-review-profile.yaml').read_text())
    module = json.loads((ROOT / 'ontology/modules/assessment-comparison.json').read_text())
    assert module['profile_version'] == profile['version']
    assert module['protocols'] == ['CILE-ASSESSMENT-REFERENCE-1', 'CILE-ASSESSMENT-COMPARISON-1']
    assert set(module['classes'].values()) <= set(profile['classes'])
    assert set(module['identity'].values()) <= set(profile['slots'])
    assert 'public' not in module['storage'].lower().split('never')[0]


def test_assessment_comparison_checkpoint_protocols_match_runtime_source():
    source = (ROOT / 'curator-app/src/calibration-development-checkpoint.js').read_text()
    for protocol in ('CILE-ASSESSMENT-REFERENCE-1', 'CILE-ASSESSMENT-COMPARISON-1'):
        assert protocol in source
