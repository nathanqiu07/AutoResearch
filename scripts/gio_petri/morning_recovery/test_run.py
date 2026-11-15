"""Offline execution-boundary tests; every captured request here is a fixture."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


GIO = Path(__file__).resolve().parents[1]
if str(GIO) not in sys.path:
    sys.path.insert(0, str(GIO))
from morning_recovery import budget, packet, run
from morning_recovery.test_packet import receipt, START, LEASE, SENTINEL


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FixedNow(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc)


class MorningRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        clock = patch.object(budget, 'datetime', FixedNow)
        clock.start()
        self.addCleanup(clock.stop)

    def packet_fixture(self):
        context = self.root / 'context.json'
        context.write_text(json.dumps(receipt(), ensure_ascii=False))
        source = self.root / 'source'
        settings = packet.prepare_packet([context], source, START, copy.deepcopy(LEASE))
        lease = {**copy.deepcopy(LEASE), 'lease_id': 'issued-offline-fixture',
                 'status': 'issued', 'owner_chat': budget.OWNER_CHAT,
                 'packet_checksums_sha256': sha(source / 'checksums.json')}
        return source, settings, lease

    def capture(self, index, role, request, response=None, include_request=True):
        directory = self.root / 'arm' / 'calls'
        directory.mkdir(parents=True, exist_ok=True)
        body = {'response': response or {'choices': [{'message': {'content': 'fixture reply'}}]}}
        if include_request:
            body['request'] = request
        path = directory / ('call-%04d-%s.json' % (index, role))
        path.write_text(json.dumps(body, ensure_ascii=False))
        return path

    def ordinary_captures(self):
        self.capture(0, 'auditor', {'model': 'fixture-auditor', 'messages': [
            {'role': 'system', 'content': 'Prefix\n' + SENTINEL},
            {'role': 'user', 'content': 'Fixture unchanged seed'}]})
        self.capture(1, 'target', {'model': 'fixture-target', 'messages': [
            {'role': 'user', 'content': [{'type': 'text', 'text': 'Fixture workspace'}]}]})
        self.capture(2, 'judge', {'model': 'fixture-judge', 'input': [
            {'role': 'user', 'content': [{'type': 'input_text', 'text': 'Fixture target trace'}]}]})

    def inspect_captures(self):
        return run.capture_inputs(self.root / 'arm', receipt())

    def test_freeze_uses_exact_copied_packet_and_source_changes_do_not_affect_it(self):
        source, settings, lease = self.packet_fixture()
        destination = self.root / 'frozen'
        result = run.freeze_packet(source, destination, lease, settings)
        self.assertEqual(result, settings)
        self.assertEqual(sha(destination / 'checksums.json'), lease['packet_checksums_sha256'])
        for member in source.iterdir():
            self.assertEqual((destination / member.name).read_bytes(), member.read_bytes())
        saved = (destination / 'rich.template.txt').read_bytes()
        (source / 'rich.template.txt').write_text('FIXTURE_MUTATION_AFTER_FREEZE')
        self.assertEqual((destination / 'rich.template.txt').read_bytes(), saved)
        self.assertEqual(packet.verify_packet(destination), settings)

    def test_copy_time_mutation_is_rejected_before_lease_or_execution(self):
        source, settings, lease = self.packet_fixture()
        original_copy = shutil.copytree

        def mutate_copy(src, dst):
            result = original_copy(src, dst)
            (Path(dst) / 'rich.template.txt').write_text('UNVERIFIED COPY-TIME FIXTURE')
            return result

        with patch.object(run.shutil, 'copytree', side_effect=mutate_copy), \
                patch.object(run, 'validate_execution_lease') as validate, \
                patch.object(run, 'run_arm') as dispatch:
            with self.assertRaises(ValueError):
                run.freeze_packet(source, self.root / 'frozen', lease, settings)
        validate.assert_not_called()
        dispatch.assert_not_called()

    def test_exact_lease_pin_rejects_a_valid_but_rehashed_copied_packet(self):
        source, settings, lease = self.packet_fixture()
        original_copy = shutil.copytree

        def alter_manifest_format(src, dst):
            result = original_copy(src, dst)
            manifest = Path(dst) / 'checksums.json'
            manifest.write_bytes(manifest.read_bytes() + b' ')
            return result

        with patch.object(run.shutil, 'copytree', side_effect=alter_manifest_format):
            with self.assertRaisesRegex(ValueError, 'bound to this packet'):
                run.freeze_packet(source, self.root / 'frozen', lease, settings)

    def test_wrong_lease_pin_and_changed_expected_settings_are_rejected(self):
        source, settings, lease = self.packet_fixture()
        wrong_lease = dict(lease, packet_checksums_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'bound to this packet'):
            run.freeze_packet(source, self.root / 'wrong-pin', wrong_lease, settings)
        expected = dict(settings, start_time='2026-11-15T17:00:00+00:00')
        with self.assertRaisesRegex(ValueError, 'changed while copying'):
            run.freeze_packet(source, self.root / 'wrong-settings', lease, expected)

    def test_real_request_shapes_show_auditor_context_and_protected_absence(self):
        self.ordinary_captures()
        result = self.inspect_captures()
        self.assertEqual(result['status'], 'passed_full_context_check')
        self.assertTrue(result['auditor_full_context_observed'])
        self.assertEqual(result['protected_roles_with_capture'], ['judge', 'target'])
        self.assertEqual(result['full_context_leak_paths'], [])
        self.assertEqual(len(result['records']), 3)
        for record in result['records']:
            self.assertEqual(record['sha256'], sha(self.root / 'arm' / record['path']))
        self.assertEqual(json.loads((self.root / 'arm/role-input-captures.json').read_text()), result)

    def test_no_requests_is_incomplete_not_a_pass(self):
        (self.root / 'arm').mkdir()
        result = self.inspect_captures()
        self.assertEqual(result['status'], 'incomplete')
        self.assertFalse(result['auditor_full_context_observed'])

    def test_missing_target_request_remains_incomplete(self):
        self.ordinary_captures()
        self.capture(1, 'target', None, include_request=False)
        result = self.inspect_captures()
        self.assertEqual(result['status'], 'incomplete')
        target = next(r for r in result['records'] if r['role'] == 'target')
        self.assertFalse(target['request_present'])

    def test_one_captured_target_does_not_hide_another_missing_request(self):
        self.ordinary_captures()
        self.capture(3, 'target', None)
        self.assertEqual(self.inspect_captures()['status'], 'incomplete')

    def test_empty_request_object_is_not_evidence_of_target_input(self):
        self.ordinary_captures()
        self.capture(1, 'target', {})
        self.assertEqual(self.inspect_captures()['status'], 'incomplete')

    def test_full_context_leak_to_either_protected_role_fails(self):
        self.ordinary_captures()
        for index, role in ((1, 'target'), (2, 'judge')):
            with self.subTest(role=role):
                self.ordinary_captures()
                leak = self.capture(index, role, {'messages': [
                    {'role': 'user', 'content': [{'type': 'text', 'text': SENTINEL}]}]})
                result = self.inspect_captures()
                self.assertEqual(result['status'], 'failed')
                self.assertIn(str(leak.relative_to(self.root / 'arm')), result['full_context_leak_paths'])

    def test_response_text_does_not_count_as_input_context_or_input_leak(self):
        self.ordinary_captures()
        self.capture(1, 'target', {'messages': [{'role': 'user', 'content': 'Fixture input'}]},
                     response={'choices': [{'message': {'content': SENTINEL}}]})
        self.assertEqual(self.inspect_captures()['status'], 'passed_full_context_check')
        self.capture(0, 'auditor', {'messages': [{'role': 'user', 'content': 'Fixture input'}]},
                     response={'choices': [{'message': {'content': SENTINEL}}]})
        result = self.inspect_captures()
        self.assertEqual(result['status'], 'incomplete')
        self.assertFalse(result['auditor_full_context_observed'])


if __name__ == '__main__':
    unittest.main()
