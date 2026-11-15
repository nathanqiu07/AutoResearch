"""Synthetic, label-free integration fixtures for evaluator custody and scoring."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from autoresearch.taste.overnight import evaluation as ev


def doc(identity, text=None, **updates):
    text = text or ("Evidence " + identity + " " + "careful measurements inform choices " * 12)
    out = dict(document_id=identity, researcher_id="researcher", content=text,
               content_sha256=hashlib.sha256(text.encode()).hexdigest(),
               observed_content_sha256="a" * 64, canonical_url="https://example.org/" + identity,
               version_evidence="Snapshot revision 1", author="researcher",
               contribution="sole author", fetch_status="complete", permitted_spans=[{"start":0,"end":len(text),"text":text,"speaker":"researcher"}],
               source_review={"disposition":"approved_atemporal","reviewer":"role04", "grouping_reviewed":True,"attribution_basis":"synthetic fixture"},
               document_group=identity, project_group=identity, duplicate_group=identity)
    out.update(updates)
    return out


def target(identity="t1", group="g1", tier="A", chosen=0):
    return dict(item_id=identity, researcher_id="researcher", group_id=group, tier=tier,
                context="Choose a study", options=["Measure carefully", "Use a proxy"],
                chosen_index=chosen)


def prediction(identity="t1", choice="a", probabilities=None, **updates):
    out = dict(item_id=identity, status="complete", prediction=dict(choice=choice,
               confidence=0.8, probabilities=probabilities if probabilities is not None else [0.8, 0.2],
               calibrated=False))
    out.update(updates)
    return out


def target_bundle_fixture(items):
    docs = {}
    checked = []
    for item in items:
        item = copy.deepcopy(item)
        group = item["group_id"]
        docs.setdefault(group, doc(group, "Measure carefully rather than Use a proxy. " + group))
        source = docs[group]
        item.update(document_id=group, option_order_id="order0", speaker="researcher", attribution_verified=True,
                    alternative_provenance=["source", "source"], evidence_review="accepted", constraints="synthetic", alternatives_available=True,
                    evidence_span={"start":0,"end":len(source["content"]),"text":source["content"]})
        checked.append(item)
    manifest = ev.freeze_split(list(docs.values()), {key:"dev" for key in docs})
    for item in checked:
        item["group_id"] = manifest["document_groups"][item["document_id"]]
    bundle = ev.prepare_target_bundle(checked, list(docs.values()), manifest, stage="dev")
    return bundle


def score_fixture(items, rows):
    bundle = target_bundle_fixture(items)
    inputs = {i["item_id"]:ev.prediction_input(i) for i in bundle["items"]}
    rows = copy.deepcopy(rows)
    for row in rows:
        row.setdefault("item_sha256", ev.canonical_hash(inputs.get(row["item_id"], {})))
        row.setdefault("items_sha256",bundle["items_sha256"])
        row.setdefault("job_id","fixture-job")
        row.setdefault("manifest_sha256","fixture-manifest")
    return ev.score_predictions(bundle, rows, expected_target_bundle_sha256=bundle["target_bundle_sha256"],
                                expected_job_id="fixture-job", expected_manifest_sha256="fixture-manifest")


def job_packet(bundle, identities, **updates):
    by_id = {t["item_id"]: ev.prediction_input(t) for t in bundle["items"]}
    inputs = [by_id[i] for i in identities]
    manifest = dict(schema_version="overnight-job-v1", campaign_id="fixture", stage="dev", kind="predict",
                    method_id="lexical_retrieval", source_manifest_hash="approved-fit-hash",
                    contract_sha256="contract", code_sha="code", personalization_cap=2048, replicate_id=0,
                    extractor={"model":"none"}, consumer={"model":"fixture"},
                    profile_hash=ev.canonical_hash(identities), items_hash=ev.canonical_hash(inputs),
                    option_order_schedule=[{"item_id":i["item_id"],"option_order_id":i["option_order_id"]} for i in inputs])
    manifest.update(updates)
    manifest["job_id"] = ev.canonical_hash(manifest)
    rows = [prediction(i["item_id"], item_sha256=ev.canonical_hash(i), items_sha256=manifest["items_hash"],
                       job_id=manifest["job_id"], manifest_sha256=ev.canonical_hash(manifest)) for i in inputs]
    return {"manifest":manifest,"items":inputs,"predictions":rows}


def rebind_packet(packet):
    manifest = packet["manifest"]
    manifest["job_id"] = ev.canonical_hash({k:v for k,v in manifest.items() if k not in ("job_id","lease","created_at","updated_at")})
    for row,item in zip(packet["predictions"],packet["items"]):
        row.update(job_id=manifest["job_id"],manifest_sha256=ev.canonical_hash(manifest),
                   items_sha256=manifest["items_hash"],item_sha256=ev.canonical_hash(item))


def subset_score(bundle, packets, **updates):
    kwargs = dict(expected_target_bundle_sha256=bundle["target_bundle_sha256"],
                  expected_source_manifest_hash="approved-fit-hash",
                  expected_items_sha256=ev.canonical_hash([i for p in packets for i in p["items"]]),
                  expected_manifest_hashes={p["manifest"]["job_id"]:ev.canonical_hash(p["manifest"]) for p in packets})
    kwargs.update(updates)
    return ev.score_manifest_jobs(bundle, packets, **kwargs)


class ManifestSubsetScoringTests(unittest.TestCase):
    def setUp(self):
        self.bundle = target_bundle_fixture([target("t1"), target("t2"), target("t3")])

    def test_subset_and_per_item_jobs_agree_without_rewriting_provenance(self):
        together = [job_packet(self.bundle, ["t1","t2"])]
        separate = [job_packet(self.bundle, ["t1"]), job_packet(self.bundle, ["t2"])]
        original = copy.deepcopy(separate)
        a, b = subset_score(self.bundle,together), subset_score(self.bundle,separate)
        self.assertEqual(a["accuracy"],1)
        self.assertEqual(b["n_items"],2)
        self.assertEqual(b["target_bundle_sha256"],self.bundle["target_bundle_sha256"])
        self.assertEqual(separate,original)
        self.assertEqual(b["per_item"][0]["job_id"],separate[0]["manifest"]["job_id"])
        self.assertEqual(b["per_item"][0]["items_sha256"],separate[0]["manifest"]["items_hash"])
        self.assertEqual(b["job_provenance"][0]["manifest"],separate[0]["manifest"])
        self.assertEqual(ev.paired_comparison(a,b)["difference"],0)

    def test_interleaved_jobs_preserve_job_order_and_frozen_aggregate_order(self):
        packets = [job_packet(self.bundle,["t1","t3"]),job_packet(self.bundle,["t2"])]
        original = copy.deepcopy(packets)
        report = subset_score(self.bundle,packets,expected_item_ids=["t1","t2","t3"],
                              expected_items_sha256=self.bundle["items_sha256"])
        self.assertEqual([r["item_id"] for r in report["per_item"]],["t1","t2","t3"])
        self.assertEqual(packets,original)
        self.assertEqual(report["per_item"][2]["job_id"],packets[0]["manifest"]["job_id"])
        self.assertEqual(report["per_item"][2]["items_sha256"],packets[0]["manifest"]["items_hash"])

    def test_explicit_aggregate_order_cannot_hide_missing_duplicate_or_changed_items(self):
        packets = [job_packet(self.bundle,["t1","t3"]),job_packet(self.bundle,["t2"])]
        for order in (["t1","t2"],["t1","t1","t2","t3"],["t1","t2","unknown"],["t3","t2","t1"]):
            with self.assertRaises(ValueError):
                subset_score(self.bundle,packets,expected_item_ids=order,
                             expected_items_sha256=self.bundle["items_sha256"])

    def test_missing_predictions_keep_planned_denominator(self):
        packets = [job_packet(self.bundle,["t1"]),job_packet(self.bundle,["t2"])]
        packets[1]["predictions"] = []
        report = subset_score(self.bundle,packets)
        self.assertEqual(report["n_items"],2)
        self.assertEqual(report["accuracy"],0.5)
        self.assertEqual(report["missing_item_ids"],["t2"])

    def test_altered_input_extra_field_and_order_rejected_even_if_rehashed(self):
        for field,value in [("context","changed"),("options",["Use a proxy","Measure carefully"]),
                            ("option_order_id","changed"),("answer","hidden")]:
            packet = job_packet(self.bundle,["t1"])
            packet["items"][0][field] = value
            packet["manifest"]["items_hash"] = ev.canonical_hash(packet["items"])
            rebind_packet(packet)
            with self.assertRaises(ValueError):
                subset_score(self.bundle,[packet])

    def test_duplicate_jobs_items_and_rows_rejected(self):
        p = job_packet(self.bundle,["t1"])
        for packets in ([p,p], [p,job_packet(self.bundle,["t1","t2"])],
                        [dict(p,predictions=p["predictions"]*2)]):
            with self.assertRaises(ValueError):
                subset_score(self.bundle,packets)

    def test_wrong_source_stage_or_mixed_arm_rejected(self):
        for updates in ({"source_manifest_hash":"unapproved"},{"stage":"confirmation"},{"kind":"build"}):
            with self.assertRaises(ValueError):
                subset_score(self.bundle,[job_packet(self.bundle,["t1"],**updates)])
        for updates in ({"method_id":"P1"},{"consumer":{"model":"other"}},{"replicate_id":1}):
            with self.assertRaises(ValueError):
                subset_score(self.bundle,[job_packet(self.bundle,["t1"]),job_packet(self.bundle,["t2"],**updates)])

    def test_wrong_manifest_and_row_bindings_rejected(self):
        packet = job_packet(self.bundle,["t1"])
        pins = {packet["manifest"]["job_id"]:ev.canonical_hash(packet["manifest"])}
        changed = copy.deepcopy(packet)
        changed["manifest"]["profile_hash"]="changed"
        with self.assertRaises(ValueError):
            subset_score(self.bundle,[changed],expected_manifest_hashes=pins)
        for field in ("job_id","manifest_sha256","items_sha256","item_sha256"):
            changed = copy.deepcopy(packet)
            changed["predictions"][0][field]="wrong"
            with self.assertRaises(ValueError):
                subset_score(self.bundle,[changed])
        with self.assertRaises(ValueError):
            subset_score(self.bundle,[packet],expected_manifest_hashes={})

    def test_schedule_and_private_split_remain_pinned(self):
        packet = job_packet(self.bundle,["t1","t2"])
        with self.assertRaises(ValueError):
            subset_score(self.bundle,[packet],expected_items_sha256="different-subset")
        changed = copy.deepcopy(self.bundle)
        changed["split_manifest_sha256"]="different-split"
        with self.assertRaises(ValueError):
            subset_score(changed,[packet])
        packet["manifest"]["option_order_schedule"].reverse()
        rebind_packet(packet)
        with self.assertRaises(ValueError):
            subset_score(self.bundle,[packet])


class SourceBoundaryTests(unittest.TestCase):
    def test_crosspost_project_and_revision_are_one_connected_component(self):
        docs = [doc("a", "Alpha distinct writing.", project_group="p"),
                doc("b", "Beta other writing.", project_group="p", crosspost_ids=["c"]),
                doc("c", "Gamma separate text."), doc("d", "Unrelated.")]
        groups = ev.group_documents(docs)
        self.assertEqual(groups["a"], groups["c"])
        self.assertNotEqual(groups["a"], groups["d"])
        with self.assertRaisesRegex(ValueError, "crosses"):
            ev.freeze_split(docs, {"a": "fit", "b": "fit", "c": "dev", "d": "confirmation"})

    def test_near_duplicate_and_exact_content_link_across_urls(self):
        text = " ".join("word%d" % i for i in range(100))
        docs = [doc("a", text), doc("b", text.replace("word50", "changed")), doc("c", text)]
        groups = ev.group_documents(docs)
        self.assertEqual(len(set(groups.values())), 1)

    def test_unreviewed_source_or_unverified_span_is_not_released(self):
        d = doc("a")
        del d["source_review"]
        self.assertEqual(ev.review_document(d)["status"], "quarantined")
        d = doc("a")
        d["permitted_spans"][0]["text"] = "fabricated"
        self.assertEqual(ev.review_document(d)["status"], "quarantined")

    def test_missing_version_is_quarantined_not_released(self):
        docs = [doc("a", version_evidence="")]
        self.assertEqual(ev.review_document(docs[0])["status"], "quarantined")
        with self.assertRaisesRegex(ValueError, "quarantined"):
            ev.freeze_split(docs, {"a": "fit"})
        ev.freeze_split(docs, {"a": "quarantine"})

    def test_bundle_excludes_answer_bearing_metadata_and_hidden_documents(self):
        docs = [doc("fit", "A unique fitting source.", chosen="secret", answer="hidden",
                    version_evidence={"observed_revision": "a" * 64, "response_headers": {"Set-Cookie": "SECRET_COOKIE"}, "answer": "SECRET_LABEL"}),
                doc("hidden", "An entirely separate target.", title="ANSWER TITLE", reason="ANSWER REASON")]
        manifest = ev.freeze_split(docs, {"fit": "fit", "hidden": "confirmation"})
        bundle = ev.approved_bundle(docs, manifest)
        serialized = json.dumps(bundle)
        self.assertNotIn("ANSWER", serialized)
        self.assertNotIn("SECRET", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("hidden\"", serialized)  # held-out IDs are opaque hashes
        self.assertEqual([d["document_id"] for d in bundle["documents"]], ["fit"])
        self.assertEqual(bundle["heldout"]["confirmation"]["count"], 1)

    def test_changed_or_extra_source_cannot_reuse_split(self):
        docs = [doc("a", "A unique fitting source.")]
        manifest = ev.freeze_split(docs, {"a": "fit"})
        with self.assertRaises(ValueError):
            ev.approved_bundle(docs + [doc("extra")], manifest)
        changed = copy.deepcopy(docs)
        changed[0]["content"] += " tampered"
        with self.assertRaises(ValueError):
            ev.approved_bundle(changed, manifest)

    def test_changed_provenance_cannot_reuse_split(self):
        docs = [doc("a", "A unique fitting source.")]
        manifest = ev.freeze_split(docs, {"a": "fit"})
        docs[0]["author"] = "another speaker"
        with self.assertRaises(ValueError):
            ev.approved_bundle(docs, manifest)

    def test_prediction_input_is_strict_allowlist(self):
        item = target()
        item.update(answer="SECRET", title="SECRET", source_url="SECRET", option_order_id="order0")
        payload = ev.prediction_input(item)
        self.assertEqual(set(payload), {"item_id", "researcher_id", "context", "options", "option_order_id"})
        self.assertNotIn("SECRET", json.dumps(payload))

    def test_observed_choice_requires_available_alternatives(self):
        source=doc("source", "I used cases because no scalable evaluation could be devised.")
        item=target(tier="B")
        item.update(document_id="source",speaker="researcher",attribution_verified=True,
                    alternative_provenance=["source","source"],evidence_review="accepted",
                    constraints="time-limited",alternatives_available=False,
                    evidence_span={"start":0,"end":len(source["content"]),"text":source["content"]})
        self.assertFalse(ev.target_eligibility(item,source)["eligible"])

    def test_target_requires_real_source_alternatives_and_exact_span(self):
        source = doc("source", "I choose Measure carefully rather than Use a proxy.")
        item = target()
        item.update(document_id="source", speaker="researcher", attribution_verified=True,
                    alternative_provenance=["source", "source"], evidence_review="accepted",
                    evidence_span={"start": 0, "end": len(source["content"]), "text": source["content"]})
        self.assertTrue(ev.target_eligibility(item, source)["eligible"])
        item["alternative_provenance"][1] = "generated"
        self.assertFalse(ev.target_eligibility(item, source)["eligible"])
        item["alternative_provenance"][1] = "source"
        item["evidence_span"]["text"] = "invented quote"
        self.assertFalse(ev.target_eligibility(item, source)["eligible"])
        item["tier"] = "C"
        self.assertFalse(ev.target_eligibility(item, source)["eligible"])


class ScoringTests(unittest.TestCase):
    def test_missing_invalid_and_failed_arms_count_in_denominator(self):
        items = [target("t1"), target("t2"), target("t3"), target("t4")]
        rows = [prediction(), prediction("t2", status="failed", prediction=None),
                prediction("t3", probabilities=[float("nan"), 0.2])]
        report = score_fixture(items, rows)
        self.assertEqual(report["accuracy"], 0.25)
        self.assertEqual(report["failures"], 3)
        self.assertEqual(report["probability_coverage"], 0.25)
        self.assertAlmostEqual(report["brier_valid_only"], 0.04)
        self.assertEqual(report["missing_item_ids"], ["t4"])

    def test_malformed_prediction_object_counts_as_failure(self):
        report = score_fixture([target()], [prediction(prediction="malformed")])
        self.assertEqual(report["failures"], 1)
        self.assertEqual(report["accuracy"], 0)

    def test_result_input_order_and_job_bindings_are_required(self):
        for bad in ({"item_sha256":"wrong"}, {"items_sha256":"wrong"},
                    {"job_id":"wrong"}, {"manifest_sha256":"wrong"}):
            report = score_fixture([target()], [prediction(**bad)])
            self.assertEqual(report["accuracy"], 0)
            self.assertEqual(report["failures"], 1)

    def test_scoring_rejects_unvalidated_or_changed_target_bundle(self):
        with self.assertRaises(ValueError):
            ev.score_predictions({"items":[target()]}, [], expected_target_bundle_sha256="not-validated",
                                 expected_job_id="j", expected_manifest_sha256="m")

    def test_target_builder_rejects_wrong_source_stage_or_group(self):
        source = doc("g", "Measure carefully rather than Use a proxy.")
        split = ev.freeze_split([source], {"g":"fit"})
        item = target(group=split["document_groups"]["g"])
        item.update(document_id="g", option_order_id="order0", speaker="researcher", attribution_verified=True,
                    alternative_provenance=["source","source"], evidence_review="accepted",
                    evidence_span={"start":0,"end":len(source["content"]),"text":source["content"]})
        with self.assertRaisesRegex(ValueError,"stage"):
            ev.prepare_target_bundle([item],[source],split,stage="dev")
        split = ev.freeze_split([source], {"g":"dev"})
        item["group_id"]="forged-group"
        with self.assertRaisesRegex(ValueError,"group"):
            ev.prepare_target_bundle([item],[source],split,stage="dev")

    def test_extra_or_duplicate_prediction_refused(self):
        for rows in ([prediction(), prediction()], [prediction("unknown")]):
            with self.assertRaises(ValueError):
                score_fixture([target()], rows)

    def test_tiers_are_separate_and_inferred_labels_are_rejected(self):
        report = score_fixture([target(), target("t2", tier="B")], [prediction()])
        self.assertEqual(report["by_tier"]["A"]["accuracy"], 1)
        self.assertEqual(report["by_tier"]["B"]["accuracy"], 0)
        with self.assertRaises(ValueError):
            score_fixture([target(tier="C")], [prediction()])

    def test_paired_comparison_requires_identical_scheduled_items(self):
        a = score_fixture([target()], [prediction()])
        b = score_fixture([target("t2")], [prediction("t2")])
        with self.assertRaises(ValueError):
            ev.paired_comparison(a, b)
        result = ev.paired_comparison(a, a)
        self.assertEqual(result["difference"], 0)
        self.assertIsNone(result["ci95"])
        self.assertEqual(result["n_groups"], 1)

    def test_development_ready_without_confirmation_and_per_researcher(self):
        report = ev.feasibility_report([target()], {"researcher": {"fit": 1, "dev": 1, "confirmation": 0}})
        self.assertEqual(report["status"], "descriptive_pilot")
        self.assertFalse(report["confirmation_feasible"])
        self.assertEqual(report["per_researcher"]["researcher"]["status"], "dev_ready")
        report = ev.feasibility_report([target()], {"researcher": {"fit": 0, "dev": 1, "confirmation": 1}})
        self.assertEqual(report["status"], "unmeasured")

    def test_group_interval_and_empty_feasibility_are_explicit(self):
        items = [target(), target("t2", group="g2")]
        a = score_fixture(items, [prediction(), prediction("t2")])
        b = score_fixture(items, [])
        self.assertEqual(ev.paired_comparison(a, b)["ci95"], [1.0, 1.0])
        self.assertEqual(ev.feasibility_report([], {"fit": 0, "dev": 0, "confirmation": 0})["status"], "unmeasured")


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "store"
        self.store = ev.initialize_store(self.root)
        self.private = self.root / "private"
        self.manifest = dict(schema_version="confirmation-v1", canonical_dataset="fixture",
                             canonical_split="frozen-split", job_ids=["j1", "j2"],
                             identities=[{"kind": "target", "id": "t1"}, {"kind": "source_group", "id": "g1"}],
                             private_root=str(self.private.resolve()), metrics=["accuracy"], retry_policy="none")
        self.authority = dict(authorized=True, source="synthetic test only",
                              manifest_sha256=ev.canonical_hash(self.manifest))

    def reserve(self, manifest=None):
        manifest = manifest or self.manifest
        authority = dict(self.authority, manifest_sha256=ev.canonical_hash(manifest))
        return ev.reserve_confirmation(self.root, manifest, authority)

    def validate(self, receipt, **updates):
        kwargs = dict(job_id="j1", manifest_sha256=ev.canonical_hash(self.manifest),
                      private_root=self.private, expected_store_id=self.store["store_id"])
        kwargs.update(updates)
        return ev.validate_confirmation_receipt(self.root, receipt, **kwargs)

    def test_receipt_is_persisted_and_strictly_validated(self):
        receipt = self.reserve()
        self.assertEqual(self.validate(receipt), receipt)
        for kwargs in ({"job_id": "other"}, {"expected_store_id": "wrong"},
                       {"private_root": self.root.parent}, {"manifest_sha256": "wrong"}):
            with self.assertRaises(ValueError):
                self.validate(receipt, **kwargs)
        forged = dict(receipt, reservation_id="forged")
        with self.assertRaises(ValueError):
            self.validate(forged)

    def test_changed_manifest_split_or_partial_overlap_never_grants_reuse(self):
        self.reserve()
        for change in ({"canonical_split": "new-split"}, {"job_ids": ["new-job"]},
                       {"identities": [{"kind": "target", "id": "t1"}]}):
            with self.assertRaisesRegex(ValueError, "consumed"):
                self.reserve(dict(self.manifest, **change))

    def test_group_identity_prevents_renamed_target_reuse(self):
        self.reserve()
        changed = dict(self.manifest, identities=[{"kind": "target", "id": "renamed"},
                                                  {"kind": "source_group", "id": "g1"}])
        with self.assertRaisesRegex(ValueError, "consumed"):
            self.reserve(changed)

    def test_failed_overlap_transaction_does_not_consume_new_identity(self):
        self.reserve()
        overlap = dict(self.manifest, identities=[{"kind": "target", "id": "new"},
                                                  {"kind": "target", "id": "t1"}])
        with self.assertRaises(ValueError):
            self.reserve(overlap)
        self.reserve(dict(self.manifest, identities=[{"kind": "target", "id": "new"}]))

    def test_interrupted_or_failed_reservation_is_never_reset(self):
        receipt = self.reserve()
        ev.initialize_store(self.root)  # a second process/clone reconnects
        with self.assertRaises(ValueError):
            self.reserve()
        ev.record_confirmation_event(self.root, receipt["reservation_id"], "failed")
        with self.assertRaises(ValueError):
            self.validate(receipt)
        with self.assertRaises(ValueError):
            self.reserve()

    def test_missing_authority_and_escape_path_fail_before_reservation(self):
        with self.assertRaises(ValueError):
            ev.reserve_confirmation(self.root, self.manifest, dict(self.authority, authorized=False))
        self.private.rmdir()
        self.private.symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.reserve()

    def test_immutable_outputs_refuse_overwrite(self):
        path = self.root / "immutable.json"
        ev.write_immutable_json(path, {"x": 1})
        with self.assertRaises(FileExistsError):
            ev.write_immutable_json(path, {"x": 2})
        self.assertEqual(json.loads(path.read_text()), {"x": 1})


if __name__ == "__main__":
    unittest.main()
