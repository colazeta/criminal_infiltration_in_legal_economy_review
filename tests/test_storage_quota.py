import os
import unittest
from unittest.mock import patch
from scripts.architecture import storage_quota as quota


class StorageQuotaTest(unittest.TestCase):
    def test_only_aggregate_allowlisted_numbers_are_exported(self):
        def field(name, kind):
            return {'name': name, 'type': {'name': kind}}
        with patch.dict(os.environ, {'CLOUDFLARE_ACCOUNT_ID': 'a' * 32}), patch.object(
                quota, 'fields', side_effect=[
                    [field('durableObjectsStorageGroups', 'Groups')], [field('sum', 'Sum')],
                    [field('sqlRowsRead', 'UInt64'), field('sqlRowsWritten', 'UInt64'), field('privateNote', 'String')]
                ]), patch.object(quota, 'query', return_value={'viewer': {'accounts': [{'durableObjectsStorageGroups': [
                    {'sum': {'sqlRowsRead': 5000000, 'sqlRowsWritten': 42000}}]}]}}) as call:
            out = quota.observe()
            self.assertEqual(out['metrics']['sqlRowsRead'], 5000000)
            self.assertFalse(out['billing_changed'])
            self.assertNotIn('a' * 32, str(out))
            self.assertNotIn('privateNote', call.call_args.args[0])

    def test_unknown_schema_names_cannot_become_queries(self):
        with self.assertRaisesRegex(RuntimeError, 'quota_schema_invalid'):
            quota.fields('private { archive }')
