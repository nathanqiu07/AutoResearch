"""Native f6 admission regression: read-only fixtures, no authority issuance."""
import copy
import importlib.util
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('remaining8_schema_review', '/private/tmp/gio_prepare_remaining8_v2.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class SchemaReview(unittest.TestCase):
    def test_actual_mixed_batch_rejects_but_two_homogeneous_batches_admit(self):
        driver = h.p.runtime()
        from autoresearch.taste.overnight.backends import DollarLedger
        # Identity-only fixture. No constructor, connection, reserve or claims.
        ledger = object.__new__(DollarLedger)
        template = h.read({'path': str(h.B / 'receipts/564a2f1ce73bc032cc70e3d7a9c6eef6bbab544dbb7a864c031de97926c413a8/preparation/prepared.json'),
                          'sha256': '337dcb9829e24d260e94bf9fcaf9a9a454479220123076e0b21653a857495468'})
        batch = {k: copy.deepcopy(template[k]) for k in ('schema_version', 'campaign_id', 'code_sha',
            'runtime_root', 'deadline', 'max_workers', 'release_schema_version', 'release_scope',
            'contract', 'env_file', 'roots', 'ledger')}
        self.assertEqual(batch['release_schema_version'], 'released-development-v2')
        rows = h.read(h.INVENTORY)['drafts']
        with patch('urllib.request.urlopen', side_effect=AssertionError('network')), \
                patch('sqlite3.connect', side_effect=AssertionError('SQL')):
            first = h.bind(h.read(rows[0]['packet']), {'path': '/synthetic-only/not-issued', 'sha256': '0' * 64})
            with self.assertRaisesRegex(ValueError, 'released schema or scope'):
                driver._prepare_packet(first, batch, ledger)
            for index, row in enumerate(rows):
                packet = h.bind(h.read(row['packet']), {'path': '/synthetic-only/not-issued', 'sha256': '0' * 64})
                schema = h.batch_blocks(rows)[index//4]['release_schema_version']
                homogeneous = dict(batch, release_schema_version=schema)
                job = driver._prepare_packet(packet, homogeneous, ledger)
                self.assertEqual(job['manifest']['job_id'], packet['manifest']['job_id'])
                self.assertEqual(job['packet']['backend']['max_calls'], 1)


if __name__ == '__main__':
    unittest.main()
