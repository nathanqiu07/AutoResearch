"""Boundary tests: fresh development users, actual history conditioning, and complete reporting."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/gio_recovery/consumer_probe.py"


def module():
    spec = importlib.util.spec_from_file_location("consumer_probe", SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def manifest():
    return {"manifest_id": "fixture", "users": {
        user: {"partition": partition, "history": [f"{user}-h{i}" for i in range(7)],
               "val": [f"{user}-v0"], "test": [f"{user}-t{i}" for i in range(4)]}
        for user, partition in [("u0", "dev"), ("u1", "dev"), ("u2", "dev"),
                                ("u3", "dev"), ("used", "dev"), ("final", "test")]}}


def choice(user, i):
    return {"user_id": user, "context": "history " + str(i), "a_text": "short",
            "b_text": "long response", "chosen": "b", "example_id": f"{user}-h{i}",
            "group_id": user + "-history"}


class ConsumerProbeTests(unittest.TestCase):
    def test_module_exists(self):
        self.assertTrue(SCRIPT.exists(), "consumer probe has not been implemented")

    def test_selection_excludes_used_and_final_users_and_matches_full_history_counts(self):
        p = module()
        selected = p.select_panel(manifest(), {"used"}, users=4, targets=4)
        self.assertEqual(set(selected["users"]), {"u0", "u1", "u2", "u3"})
        for user, donor in selected["donors"].items():
            self.assertNotEqual(user, donor)
            self.assertEqual(len(manifest()["users"][user]["history"]),
                             len(manifest()["users"][donor]["history"]))
        self.assertEqual(sum(map(len, selected["targets"].values())), 16)

    def test_selection_fails_without_enough_count_matched_development_users(self):
        p = module()
        with self.assertRaises(ValueError):
            p.select_panel(manifest(), {"used", "u2", "u3"}, users=4, targets=4)

    def test_native_request_contains_all_history_and_no_target_answer(self):
        p = module()
        history = [choice("own", i) for i in range(7)]
        item = {"item_id": "target", "user_id": "own", "context": "new question",
                "options": ["one", "two"]}
        request = p.native_request(item, history)
        payload = json.loads(request["prompt"].split("INPUT_JSON:\n", 1)[1])
        self.assertEqual(len(payload["past_choices"]), 7)
        self.assertEqual(payload["options"], ["one", "two"])
        self.assertEqual(set(payload), {"context", "options", "principles", "persona", "past_choices"})
        self.assertNotIn("actual", payload)
        self.assertNotIn("chosen", payload)
        self.assertEqual(request["max_tokens"], 2048)

    def test_conditions_change_history_without_changing_target_or_native_instruction(self):
        p = module()
        item = {"item_id": "t", "user_id": "own", "context": "same context", "options": ["A", "B"]}
        values = [p.native_request(item, h) for h in
                  [[], [choice("own", 0)], [choice("wrong", 0)]]]
        payloads = [json.loads(x["prompt"].split("INPUT_JSON:\n", 1)[1]) for x in values]
        self.assertEqual([x["context"] for x in payloads], ["same context"] * 3)
        self.assertEqual([x["options"] for x in payloads], [["A", "B"]] * 3)
        self.assertEqual(payloads[0]["past_choices"], [])
        self.assertEqual(payloads[1]["past_choices"][0]["user_id"], "own")
        self.assertEqual(payloads[2]["past_choices"][0]["user_id"], "wrong")
        self.assertEqual(len({x["system"] for x in values}), 1)

    def test_probability_validation_uses_native_parser(self):
        p = module()
        request = p.native_request({"context": "x", "options": ["a", "b"]}, [])
        self.assertEqual(p.parse_response(request, '{"probabilities":[0.2,0.8]}')["choice"], "b")
        with self.assertRaises(ValueError):
            p.parse_response(request, '{"probabilities":[0.8,0.8]}')

    def test_failure_rows_remain_in_planned_user_macro_denominator(self):
        p = module()
        requests = [dict(cell_id=str(i), user_id=u, item_id=str(i), model="gpt-6-luna", arm="own",
                         options=["x", "longer"])
                    for i, u in enumerate(["one", "two", "two", "two"])]
        outcomes = [dict(cell_id="0", prediction={"choice": "b"}),
                    dict(cell_id="1", prediction={"choice": "b"})]
        labels = {str(i): "b" for i in range(4)}
        report = p.summarize(requests, outcomes, labels)
        value = report["conditions"]["gpt-6-luna:own"]
        self.assertEqual(value["planned"], 4)
        self.assertEqual(value["valid"], 2)
        self.assertEqual(value["missing_or_failed"], 2)
        self.assertAlmostEqual(value["user_macro_accuracy"], 2 / 3)
        self.assertEqual(report["length_baseline"]["targets"], 4)

    def test_length_baseline_deduplicates_conditions_and_declares_a_ties(self):
        p = module()
        requests = [dict(cell_id=arm, user_id="u", item_id="t", model="gpt-6-luna", arm=arm,
                         options=["aa", "bb"]) for arm in ["none", "own", "wrong"]]
        report = p.summarize(requests, [], {"t": "a"})
        self.assertEqual(report["length_baseline"]["targets"], 1)
        self.assertEqual(report["length_baseline"]["ties"], 1)
        self.assertEqual(report["length_baseline"]["user_macro_accuracy"], 1)

    def test_lease_requires_exact_plan_and_fresh_external_claim(self):
        p = module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet"
            packet.mkdir()
            plan = {"planned_calls": 12, "max_usd": 2, "runtime": p.runtime_identity(),
                    "deadline": "2099-01-01T00:00:00Z", "models": p.MODELS, "arms": p.ARMS}
            p.private_json(packet / "plan.json", plan)
            lease = {"state": "authorized", "lane": "05", "job_id": "fixture", "plan_sha256": "wrong",
                     "user_partition": "dev", "final": False, "models": p.MODELS, "arms": p.ARMS,
                     "max_calls": 12, "max_usd": 2, "max_seconds": 60,
                     "deadline": "2099-01-01T00:00:00Z", "claim_path": str(root / "claim.json")}
            with self.assertRaises(ValueError):
                p.validate_lease(packet / "plan.json", lease)
            lease["plan_sha256"] = p.file_sha(packet / "plan.json")
            p.validate_lease(packet / "plan.json", lease)
            p.private_json(root / "claim.json", {})
            with self.assertRaises(ValueError):
                p.validate_lease(packet / "plan.json", lease)

    def test_prepare_ignores_final_rows_and_full_execution_keeps_invalid_output(self):
        p = module()
        p.DEADLINE = "2099-01-01T00:00:00Z"  # Synthetic transport fixtures must outlive this one-day run.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            data = manifest()
            records = []
            for user in data["users"]:
                if data["users"][user]["partition"] != "dev":
                    continue
                for split, ids in [("history", data["users"][user]["history"]),
                                   ("val", data["users"][user]["val"]),
                                   ("test", data["users"][user]["test"])]:
                    for i, identity in enumerate(ids):
                        row = choice(user, i)
                        row.update(example_id=identity, group_id=user + "-" + split)
                        records.append({"user_split": "dev", "choice_split": split, "choice": row})
            # The preparer must not even parse a final-user row.
            source.write_text("\n".join(map(json.dumps, records)) +
                              '\n{"user_split":"test","deliberately_invalid_json":\n')
            p.private_json(root / "manifest.json", data)
            p.private_json(root / "used.json", {"users": {"used": {}}})
            packet = root / "packet"
            plan = p.prepare(source, root / "manifest.json", [root / "used.json"], packet,
                             p.file_sha(source), users=4, targets=4)
            self.assertEqual(plan["planned_calls"], 96)
            self.assertEqual(set(json.loads((packet / "selection.json").read_text())["users"]),
                             {"u0", "u1", "u2", "u3"})
            reqs = json.loads((packet / "requests.json").read_text())
            self.assertEqual({r["history_count"] for r in reqs if r["arm"] == "own"}, {7})
            self.assertFalse(any("actual" in r or "chosen" in r for r in reqs))
            policy = {"max_usd": plan["max_usd"], "deadline": p.DEADLINE, "max_inflight": 1}
            ledger = p.DollarLedger(root / "ledger.sqlite", **policy)
            lease = {"state": "authorized", "lane": "05", "job_id": "fixture", "plan_sha256": p.file_sha(packet / "plan.json"),
                     "user_partition": "dev", "final": False, "models": p.MODELS, "arms": p.ARMS,
                     "max_calls": 96, "max_usd": plan["max_usd"], "max_seconds": 60,
                     "deadline": p.DEADLINE, "claim_path": str(root / "claim.json"),
                     "ledger_path": str(root / "ledger.sqlite"), "ledger_policy": policy}
            p.private_json(root / "lease.json", lease)
            bodies = []

            class Response:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, size):
                    text = "invalid JSON" if len(bodies) == 1 else '{"probabilities":[0.2,0.8]}'
                    return json.dumps({"status": "completed", "usage": {"input_tokens": 20, "output_tokens": 10},
                                       "output": [{"type": "message", "role": "assistant", "status": "completed",
                                                   "content": [{"type": "output_text", "text": text}]}]}).encode()

            def transport(request, timeout):
                bodies.append(json.loads(request.data))
                return Response()

            with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-not-a-secret"}), \
                    patch("urllib.request.urlopen", side_effect=transport):
                report = p.execute(packet / "plan.json", root / "lease.json")
                with self.assertRaises(ValueError):
                    p.execute(packet / "plan.json", root / "lease.json")
            self.assertEqual(ledger.summary()["attempts"], 96)
            self.assertEqual(sum(v["planned"] for v in report["conditions"].values()), 96)
            self.assertEqual(sum(v["valid"] for v in report["conditions"].values()), 95)
            self.assertEqual(report["length_baseline"]["targets"], 16)
            self.assertEqual(bodies, [p.wire_body(r["model"], r["native_request"]) for r in reqs])

            # A transport failure retains its charge reservation and stops all later calls.
            unknown_packet = root / "unknown-packet"
            unknown_plan = p.prepare(source, root / "manifest.json", [root / "used.json"], unknown_packet,
                                     p.file_sha(source), users=2, targets=1)
            unknown_policy = {**policy, "max_usd": unknown_plan["max_usd"]}
            unknown_ledger = p.DollarLedger(root / "unknown-ledger.sqlite", **unknown_policy)
            unknown_lease = {**lease, "job_id": "unknown-fixture",
                             "plan_sha256": p.file_sha(unknown_packet / "plan.json"), "max_calls": 12,
                             "max_usd": unknown_plan["max_usd"], "claim_path": str(root / "unknown-claim.json"),
                             "ledger_path": str(root / "unknown-ledger.sqlite"), "ledger_policy": unknown_policy}
            p.private_json(root / "unknown-lease.json", unknown_lease)
            with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-not-a-secret"}), \
                    patch("urllib.request.urlopen", side_effect=TimeoutError):
                unknown_report = p.execute(unknown_packet / "plan.json", root / "unknown-lease.json")
            self.assertEqual(unknown_ledger.summary()["attempts"], 1)
            self.assertEqual(unknown_ledger.summary()["uncertain"], 1)
            self.assertGreater(unknown_ledger.summary()["reserved_usd"], 0)
            self.assertEqual(sum(v["planned"] for v in unknown_report["conditions"].values()), 12)
            self.assertEqual(sum(v["valid"] for v in unknown_report["conditions"].values()), 0)


if __name__ == "__main__":
    unittest.main()
