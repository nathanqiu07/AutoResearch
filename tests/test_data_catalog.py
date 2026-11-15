"""data/README.md is the index of committed data: every folder, and every file a researcher's
folder holds or the code writes there, must have a row."""
import os
import re
import unittest

from autoresearch.taste import timesplit, track_eval, trackp

DATA = "data"


def catalogued(section: str) -> set:
    """Backticked names in the first column of the table under `section`."""
    text = open(os.path.join(DATA, "README.md")).read()
    body = text.split(section, 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `([^`]+)`", body, re.M))


class DataCatalogTest(unittest.TestCase):
    def test_every_data_folder_has_a_row(self):
        folders = {f + "/" for f in os.listdir(DATA) if os.path.isdir(os.path.join(DATA, f))}
        self.assertEqual(folders - catalogued("## Folders"), set())

    def test_every_file_in_a_researcher_folder_has_a_row(self):
        rows = catalogued("## A researcher's folder")
        root = os.path.join(DATA, "researchers")
        found = {f + ("/" if os.path.isdir(os.path.join(root, slug, f)) else "")
                 for slug in os.listdir(root) if os.path.isdir(os.path.join(root, slug))
                 for f in os.listdir(os.path.join(root, slug))}
        self.assertEqual(found - rows, set())

    def test_every_file_the_track_code_writes_has_a_row(self):
        rows = catalogued("## A researcher's folder")
        written = {trackp.SEED_PAIRS, trackp.SEED_CHOICES, trackp.LABELS, trackp.RECHECK, trackp.HISTORY,
                   trackp.USERMODEL, timesplit.PAIRS, timesplit.REVIEW, timesplit.HISTORY,
                   timesplit.HELDOUT, timesplit.IDENTITY, track_eval.GATE}
        written |= {p.split(os.sep)[0] + "/" for p in (timesplit.DECISIONS, timesplit.EXA_EXTRACT)}
        self.assertEqual(written - rows, set())


if __name__ == "__main__":
    unittest.main()
