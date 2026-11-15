import json
import tempfile
import unittest
from pathlib import Path

from autoresearch.taste.viewer import build_viewer, validate_bundle


def bundle():
    choice = {"context": "A new question", "a_text": "A", "b_text": "B"}
    return {"format": "taste-run-bundle-v1", "mode": "offline_fixture",
            "registration": {}, "report": {}, "examples": [{
                "user_id": "fixture:user", "method": "m0", "history": [choice],
                "target": choice, "actual": "a", "prediction": None,
                "artifacts": None, "error": "deliberate fixture failure"}]}


class ViewerTests(unittest.TestCase):
    def test_requires_explicit_mode_and_actual_records(self):
        b = bundle()
        del b["mode"]
        with self.assertRaises(ValueError):
            validate_bundle(b)
        b = bundle()
        b["examples"][0]["target"] = None
        with self.assertRaises(ValueError):
            validate_bundle(b)

    def test_embedding_does_not_execute_dataset_text(self):
        b = bundle()
        attack = '</script><script>alert("dataset")</script>'
        b["examples"][0]["target"]["context"] = attack
        with tempfile.TemporaryDirectory() as d:
            path = build_viewer(b, Path(d) / "viewer.html")
            text = path.read_text()
            self.assertNotIn(attack, text)
            raw = text.split('<script id="embedded-run" type="application/json">', 1)[1].split('</script>', 1)[0]
            self.assertEqual(json.loads(raw)["examples"][0]["target"]["context"], attack)
            self.assertIn('type="file"', text)
            with self.assertRaises(FileExistsError):
                build_viewer(b, path)

    def test_keeps_failures_and_fixture_label(self):
        with tempfile.TemporaryDirectory() as d:
            path = build_viewer(bundle(), Path(d) / "viewer.html")
            text = path.read_text()
            self.assertIn('"mode": "offline_fixture"', text)
            self.assertIn('deliberate fixture failure', text)


if __name__ == "__main__":
    unittest.main()
