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
                    [field('viewer','viewer')], [field('accounts','account')], [field('durableObjectsSqlStorageGroups', 'Groups')], [field('sum', 'Sum')],
                    [field('sqlRowsRead', 'UInt64'), field('sqlRowsWritten', 'UInt64'), field('privateNote', 'String')]
                ]), patch.object(quota, 'query', side_effect=[{'__schema':{'queryType':{'name':'query'}}}, {'viewer': {'accounts': [{'durableObjectsSqlStorageGroups': [
                    {'sum': {'sqlRowsRead': 5000000, 'sqlRowsWritten': 42000}}]}]}}]) as call:
            out = quota.observe()
            self.assertEqual(out['metrics']['sqlRowsRead'], 5000000)
            self.assertFalse(out['billing_changed'])
            self.assertNotIn('a' * 32, str(out))
            self.assertNotIn('privateNote', call.call_args.args[0])

    def test_unknown_schema_names_cannot_become_queries(self):
        with self.assertRaisesRegex(RuntimeError, 'quota_schema_invalid'):
            quota.fields('private { archive }')

    def test_schema_diagnostic_retains_names_without_values_or_descriptions(self):
        self.assertEqual(quota.schema_names([{'name': 'rowsReadCount', 'description': 'private', 'value': 'secret'}]), ['rowsReadCount'])
        for unsafe in [[{'name': 'unsafe field'}], [{'name': None}], [{'name': 'x'}] * 101]:
            with self.assertRaisesRegex(RuntimeError, 'quota_schema_invalid'):
                quota.schema_names(unsafe)

    def test_nested_non_null_list_wrappers_resolve_without_assuming_a_type_name(self):
        ref = {'name': 'account', 'kind': 'OBJECT'}
        for kind in ['NON_NULL','LIST','NON_NULL']:
            ref = {'kind': kind, 'name': None, 'ofType': ref}
        self.assertEqual(quota.named({'type': ref}), 'account')
        with self.assertRaisesRegex(RuntimeError, 'quota_type_wrapper_unavailable'):
            quota.named({'type': {'kind': 'NON_NULL', 'name': None}})
