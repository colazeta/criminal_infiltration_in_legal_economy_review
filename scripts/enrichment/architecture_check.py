"""Execute the closed, read-only complete-store audit; print only its safe receipt."""
import json
from scripts.enrichment.service_client import call, current_commit


def check():
    expected = current_commit()
    receipt = call('architecture-audit', expected_commit=expected)
    required = {'contract', 'commit', 'backend', 'scope', 'complete', 'counts',
                'schema_sha256', 'state_sha256', 'checked_public_targets',
                'public_states', 'completion_states', 'issues', 'integrity_verified',
                'private_content_exported', 'scientific_decisions_changed', 'cutover_ready'}
    if (not isinstance(receipt, dict) or set(receipt) != required
            or receipt['contract'] != 'CILE-ARCHITECTURE-AUDIT-1'
            or receipt['commit'] != expected or receipt['complete'] is not True
            or receipt['private_content_exported'] is not False
            or receipt['scientific_decisions_changed'] is not False
            or receipt['cutover_ready'] is not False):
        raise RuntimeError('architecture_receipt_invalid')
    for name in ['counts', 'public_states', 'completion_states', 'issues']:
        if (not isinstance(receipt[name], dict)
                or any(not isinstance(k, str) or not k.replace('_', '').isalnum()
                       or type(v) is not int or v < 0 for k, v in receipt[name].items())):
            raise RuntimeError('architecture_receipt_invalid')
    return receipt


if __name__ == '__main__':
    try:
        result = check()
        print(json.dumps(result, indent=2))
        if result['integrity_verified'] is not True:
            raise SystemExit('architecture_integrity_gate_failed')
    except RuntimeError as error:
        if str(error).endswith(':architecture_schema_set_mismatch'):
            diagnostic = call('architecture-schema', expected_commit=current_commit())
            # The server returns only public mapped names and hashes; never raw DDL.
            expected_keys = {'contract', 'commit', 'expected_present', 'expected_missing',
                             'other_mapped_present', 'platform_present', 'unknown_table_sha256',
                             'schema_sha256', 'private_content_exported'}
            if (set(diagnostic) == expected_keys
                    and diagnostic['contract'] == 'CILE-ARCHITECTURE-SCHEMA-1'
                    and diagnostic['private_content_exported'] is False):
                print(json.dumps(diagnostic, indent=2))
        raise SystemExit(str(error)) from None
