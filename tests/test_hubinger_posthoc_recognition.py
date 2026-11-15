import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "experiments" / "hubinger_petri_20261115" / "posthoc_recognition.py"


def module():
    spec = importlib.util.spec_from_file_location("hubinger_posthoc_recognition", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class HubingerPosthocRecognitionTests(unittest.TestCase):
    def test_probability_parsing_clips_and_rejects_missing(self):
        m = module()
        parsed, probability = m.parse_probability('{"p": 0.72, "label": "EVAL"}')
        self.assertEqual(parsed["label"], "EVAL")
        self.assertEqual(probability, 0.72)
        _, clipped = m.parse_probability('{"p": 85}')
        self.assertEqual(clipped, 1.0)
        _, missing = m.parse_probability('{"label": "EVAL"}')
        self.assertIsNone(missing)

    def test_load_cases_requires_fifteen_completed_transcripts(self):
        m = module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = []
            for index in range(15):
                condition = "condition" + str(index // 3)
                replicate = index % 3 + 1
                source = root / "evidence" / condition / f"r{replicate}" / "audit.json"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(json.dumps({"transcript": f"transcript {index}"}))
                rows.append({"condition": condition, "local_replicate": replicate,
                             "original_planned_replicate": replicate, "execution": "success"})
            (root / "comparison.json").write_text(json.dumps({"rows": rows}))
            cases = m.load_cases(root)
            self.assertEqual(len(cases), 15)
            self.assertEqual(cases[-1]["transcript"], "transcript 14")

    def test_aggregate_keeps_conditions_separate(self):
        m = module()
        rows = [
            {"condition": "profile", "status": "completed", "mean_p_eval": 0.8},
            {"condition": "profile", "status": "completed", "mean_p_eval": 1.0},
            {"condition": "control", "status": "completed", "mean_p_eval": 0.3},
            {"condition": "control", "status": "call_error"},
        ]
        result = m.aggregate(rows)
        self.assertEqual(result["completed"], 3)
        self.assertAlmostEqual(result["by_condition"]["profile"]["mean_p_eval"], 0.9)
        self.assertEqual(result["by_condition"]["control"]["n"], 1)

    def test_aggregate_compares_named_profile_conditions_with_controls(self):
        m = module()
        rows = [
            {"condition": "P2", "status": "completed", "mean_p_eval": 0.8},
            {"condition": "P5", "status": "completed", "mean_p_eval": 0.9},
            {"condition": "no_profile", "status": "completed", "mean_p_eval": 0.6},
            {"condition": "generic", "status": "completed", "mean_p_eval": 0.7},
        ]
        result = m.aggregate(rows)
        self.assertAlmostEqual(result["cohorts"]["profiles"]["mean_p_eval"], 0.85)
        self.assertAlmostEqual(result["cohorts"]["controls"]["mean_p_eval"], 0.65)
        self.assertAlmostEqual(result["cohorts"]["difference_profile_minus_control"], 0.2)


if __name__ == "__main__":
    unittest.main()
