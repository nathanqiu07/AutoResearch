"""Offline recovery budget and duplicate-call guards; no model accuracy claims."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import review_failed

class RecoveryTests(unittest.TestCase):
    def test_budget_is_remaining_original_allocation(self):
        self.assertAlmostEqual(review_failed.remaining_cap({'cap_usd':5,'charged_or_reserved_usd':.043},5),4.957)
        with self.assertRaises(ValueError):review_failed.remaining_cap({'cap_usd':5,'charged_or_reserved_usd':5},5)
        with self.assertRaises(ValueError):review_failed.remaining_cap({'cap_usd':5,'charged_or_reserved_usd':.1},10)

    def test_reject_corrupt_spend(self):
        for value in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):review_failed.remaining_cap({'cap_usd':5,'charged_or_reserved_usd':value},5)

    def test_existing_review_ledger_blocks_duplicate_call_before_key_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);out=run/'postmortem-review';out.mkdir()
            (out/'checksums.json').write_text('{}');(out/'ledger.json').write_text('{}')
            with patch.object(sys,'argv',['review_failed','--run',str(run),'--execute']),patch.object(review_failed.getpass,'getpass',side_effect=AssertionError('No credential prompt allowed')):
                with self.assertRaisesRegex(ValueError,'already attempted'):review_failed.main()

if __name__=='__main__':unittest.main()
