from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "trainlab" / "rate_split.py"
SPEC = importlib.util.spec_from_file_location("formal_train_archive", SCRIPT)
archive = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(archive)


def h(value: int) -> str:
    return f"{value:064x}"


class FormalTrainArchiveTests(unittest.TestCase):
    def pilot(self):
        base = {
            "schema_version": "PS-FORMAL-TRAIN-ARCHIVE-1",
            "record_type": "PILOT_MANIFEST",
            "authority": "NONE_ENGINEERING_ONLY",
            "programme_stage": "STAGE_0_LOOP",
            "evidence_class": "TRAIN_TUNING",
            "activation_gate": {
                "requires_t0_qualified": True,
                "requires_sealed_train_pool": True,
                "execution_authorized_by_this_tranche": False,
            },
            "transition_contract": {
                "max_selected_parent_transitions": 4,
                "predeclared_stop_required": True,
            },
            "benchmark": {
                "repository": "example/minif2f-cleaned",
                "source_commit": "1" * 40,
                "snapshot_sha256": h(2),
                "toolchain_manifest_sha256": h(3),
            },
            "mutation": {
                "operator_id": "HOMOGENEOUS_PATCH_MUTATION_V1",
                "operator_config_sha256": h(4),
                "proposer_count": 3,
            },
            "budget_contract_sha256": h(5),
            "partitions": {
                "DIAG": [
                    {"instance_id": f"diag-{i:02d}", "statement_sha256": h(100 + i)}
                    for i in range(32)
                ],
                "SELECT": [
                    {"instance_id": f"select-{i:02d}", "statement_sha256": h(200 + i)}
                    for i in range(32)
                ],
            },
            "supernova_credit": dict(archive.ZERO_CREDIT),
        }
        return archive.bind_content_id(base, "pilot_id")

    def candidate(self, parent_id=None, patch=b"patch-a", tree=10):
        base = {
            "schema_version": "PS-FORMAL-TRAIN-ARCHIVE-1",
            "record_type": "CANDIDATE",
            "authority": "NONE_ENGINEERING_ONLY",
            "descriptor": {
                "parent_candidate_ids": [] if parent_id is None else [parent_id],
                "source_tree_sha256": h(tree),
                "source_patch_sha256": archive.sha256_bytes(patch),
                "mutation_operator_id": "HOMOGENEOUS_PATCH_MUTATION_V1",
                "mutation_operator_config_sha256": h(4),
                "runtime_contract": {
                    "execution_status": "NOT_AUTHORIZED_UNTIL_SANDBOX_QUALIFIED",
                    "network": "DENY",
                    "credential_access": "NONE",
                    "github_token": "NONE",
                    "environment_allowlist": [],
                },
            },
            "supernova_credit": dict(archive.ZERO_CREDIT),
        }
        return archive.bind_content_id(base, "candidate_id")

    def proposal(self, candidate, proposer="session-a", role="homogeneous-1"):
        parent = candidate["descriptor"]["parent_candidate_ids"][0]
        base = {
            "schema_version": "PS-FORMAL-TRAIN-ARCHIVE-1",
            "record_type": "PROPOSAL",
            "authority": "NONE_ENGINEERING_ONLY",
            "candidate_id": candidate["candidate_id"],
            "parent_candidate_id": parent,
            "selected_parent_transition_index": 1,
            "proposer_session_id": proposer,
            "proposer_role_label": role,
            "proposal_artifact_sha256": h(40),
            "mutation_operator_id": "HOMOGENEOUS_PATCH_MUTATION_V1",
            "mutation_operator_config_sha256": h(4),
            "supernova_credit": dict(archive.ZERO_CREDIT),
        }
        return archive.bind_content_id(base, "proposal_id")

    def evaluation(self, pilot, candidate, partition="SELECT", pass_count=16, cost=1):
        results = []
        for i, item in enumerate(pilot["partitions"][partition]):
            results.append(
                {
                    "instance_id": item["instance_id"],
                    "statement_sha256": item["statement_sha256"],
                    "outcome": "PASS" if i < pass_count else "FAIL",
                    "checker_output_sha256": h(300 + i),
                    "result_artifact_sha256": h(400 + i),
                }
            )
        costs = {field: 0 for field in archive.COST_FIELDS}
        costs["execution"] = cost
        costs["total"] = cost
        base = {
            "schema_version": "PS-FORMAL-TRAIN-ARCHIVE-1",
            "record_type": "EVALUATION",
            "authority": "NONE_ENGINEERING_ONLY",
            "pilot_id": pilot["pilot_id"],
            "candidate_id": candidate["candidate_id"],
            "partition": partition,
            "source_tree_sha256": candidate["descriptor"]["source_tree_sha256"],
            "benchmark_snapshot_sha256": pilot["benchmark"]["snapshot_sha256"],
            "environment_sha256": h(500),
            "results": results,
            "complete_cost_microunits": costs,
            "supernova_credit": dict(archive.ZERO_CREDIT),
        }
        return archive.bind_content_id(base, "evaluation_id")

    def test_pilot_is_exactly_32_diag_plus_32_select_and_zero_credit(self):
        pilot = self.pilot()
        self.assertEqual(archive.validate_pilot(pilot), [])
        self.assertEqual(set(pilot["partitions"]), {"DIAG", "SELECT"})
        self.assertEqual(pilot["supernova_credit"], archive.ZERO_CREDIT)

    def test_pilot_rejects_small_split_and_future_sealed_field(self):
        pilot = self.pilot()
        pilot["partitions"]["SELECT"].pop()
        pilot = archive.bind_content_id(pilot, "pilot_id")
        self.assertTrue(archive.validate_pilot(pilot))
        pilot = self.pilot()
        pilot["partitions"]["SEALED"] = []
        pilot = archive.bind_content_id(pilot, "pilot_id")
        self.assertTrue(archive.validate_pilot(pilot))

    def test_pilot_rejects_duplicate_instance_or_statement(self):
        pilot = self.pilot()
        pilot["partitions"]["SELECT"][0]["instance_id"] = "diag-00"
        pilot["partitions"]["SELECT"][1]["statement_sha256"] = pilot["partitions"]["DIAG"][1]["statement_sha256"]
        pilot = archive.bind_content_id(pilot, "pilot_id")
        errors = archive.validate_pilot(pilot)
        self.assertIn("pilot_instance_ids_not_unique", errors)
        self.assertIn("pilot_statement_hashes_not_unique", errors)

    def test_pilot_is_dormant_and_four_transition_bounded(self):
        pilot = self.pilot()
        self.assertTrue(pilot["activation_gate"]["requires_t0_qualified"])
        self.assertTrue(pilot["activation_gate"]["requires_sealed_train_pool"])
        self.assertFalse(pilot["activation_gate"]["execution_authorized_by_this_tranche"])
        self.assertEqual(pilot["transition_contract"]["max_selected_parent_transitions"], 4)
        pilot["activation_gate"]["execution_authorized_by_this_tranche"] = True
        pilot = archive.bind_content_id(pilot, "pilot_id")
        self.assertTrue(archive.validate_pilot(pilot))

    def test_fifth_selected_parent_transition_is_rejected(self):
        root = self.candidate(tree=1)
        candidate = self.candidate(root["candidate_id"], tree=2)
        proposal = self.proposal(candidate)
        proposal["selected_parent_transition_index"] = 5
        proposal = archive.bind_content_id(proposal, "proposal_id")
        self.assertTrue(archive.validate_proposal(proposal, candidate))

    def test_candidate_id_is_key_order_invariant(self):
        candidate = self.candidate()
        reordered = json.loads(json.dumps(candidate, sort_keys=True))
        self.assertEqual(candidate["candidate_id"], archive.content_id(reordered, "candidate_id"))

    def test_candidate_id_changes_with_parent_patch_or_tree(self):
        root = self.candidate(tree=1)
        a = self.candidate(root["candidate_id"], patch=b"a", tree=2)
        b = self.candidate(root["candidate_id"], patch=b"b", tree=2)
        c = self.candidate(h(999), patch=b"a", tree=2)
        d = self.candidate(root["candidate_id"], patch=b"a", tree=3)
        self.assertEqual(len({a["candidate_id"], b["candidate_id"], c["candidate_id"], d["candidate_id"]}), 4)

    def test_candidate_rejects_role_cohort_scheduler_and_credentials(self):
        for field in ("role_id", "cohort_id", "scheduler_task_id", "github_token"):
            with self.subTest(field=field):
                candidate = self.candidate()
                candidate[field] = "forbidden"
                candidate = archive.bind_content_id(candidate, "candidate_id")
                self.assertTrue(archive.validate_candidate(candidate))

    def test_candidate_rejects_wrong_patch_and_mutation_family(self):
        candidate = self.candidate(patch=b"right")
        self.assertIn("source_patch_sha256_mismatch", archive.validate_candidate(candidate, b"wrong"))
        candidate["descriptor"]["mutation_operator_id"] = "ROLE_SPECIALIZED_MUTATION"
        candidate = archive.bind_content_id(candidate, "candidate_id")
        self.assertTrue(archive.validate_candidate(candidate))

    def test_proposer_provenance_does_not_change_candidate_identity(self):
        root = self.candidate(tree=1)
        candidate = self.candidate(root["candidate_id"])
        p1 = self.proposal(candidate, proposer="one", role="label-one")
        p2 = self.proposal(candidate, proposer="two", role="label-two")
        self.assertNotEqual(p1["proposal_id"], p2["proposal_id"])
        self.assertEqual(p1["candidate_id"], p2["candidate_id"])
        self.assertEqual(archive.validate_proposal(p1, candidate), [])
        self.assertEqual(archive.validate_proposal(p2, candidate), [])

    def test_evaluation_must_cover_exact_partition_once(self):
        pilot = self.pilot()
        candidate = self.candidate()
        evaluation = self.evaluation(pilot, candidate)
        self.assertEqual(archive.validate_evaluation(evaluation, pilot, candidate), [])
        evaluation["results"][0] = copy.deepcopy(evaluation["results"][1])
        evaluation = archive.bind_content_id(evaluation, "evaluation_id")
        errors = archive.validate_evaluation(evaluation, pilot, candidate)
        self.assertIn("evaluation_instance_ids_not_unique", errors)
        self.assertIn("evaluation_partition_coverage_mismatch", errors)

    def test_evaluation_rejects_statement_source_snapshot_and_cost_drift(self):
        pilot = self.pilot()
        candidate = self.candidate()
        evaluation = self.evaluation(pilot, candidate)
        evaluation["results"][0]["statement_sha256"] = h(999)
        evaluation["source_tree_sha256"] = h(998)
        evaluation["benchmark_snapshot_sha256"] = h(997)
        evaluation["complete_cost_microunits"]["total"] += 1
        evaluation = archive.bind_content_id(evaluation, "evaluation_id")
        errors = archive.validate_evaluation(evaluation, pilot, candidate)
        self.assertTrue(any(x.startswith("evaluation_statement_sha256_mismatch") for x in errors))
        self.assertIn("evaluation_source_tree_sha256_mismatch", errors)
        self.assertIn("evaluation_benchmark_snapshot_sha256_mismatch", errors)
        self.assertIn("complete_cost_total_mismatch", errors)

    def test_integrity_is_score_blind_and_typed(self):
        pilot = self.pilot()
        candidate = self.candidate()
        low = self.evaluation(pilot, candidate, pass_count=0)
        high = self.evaluation(pilot, candidate, pass_count=32)
        low_i = archive.evidence_integrity(pilot, candidate, low)
        high_i = archive.evidence_integrity(pilot, candidate, high)
        self.assertEqual(low_i["status"], "ADMISSIBLE")
        self.assertEqual(high_i["status"], "ADMISSIBLE")
        self.assertFalse(low_i["score_fields_emitted"])
        self.assertNotIn("pass_count", low_i)

    def test_integrity_quarantines_tamper_and_marks_missing(self):
        pilot = self.pilot()
        candidate = self.candidate()
        evaluation = self.evaluation(pilot, candidate)
        evaluation["results"][0]["statement_sha256"] = h(999)
        evaluation = archive.bind_content_id(evaluation, "evaluation_id")
        integrity = archive.evidence_integrity(pilot, candidate, evaluation)
        self.assertEqual(integrity["status"], "QUARANTINED")
        missing = archive.evidence_integrity(pilot, candidate, None)
        self.assertEqual(missing["status"], "MISSING")
        self.assertEqual(missing["errors"], ["evaluation_missing"])

    def test_selector_is_permutation_invariant_and_train_only(self):
        pilot = self.pilot()
        a = self.candidate(tree=10)
        b = self.candidate(tree=11)
        ea = self.evaluation(pilot, a, pass_count=20, cost=10)
        eb = self.evaluation(pilot, b, pass_count=21, cost=10)
        ia = archive.evidence_integrity(pilot, a, ea)
        ib = archive.evidence_integrity(pilot, b, eb)
        seed = h(700)
        first = archive.select_deterministically(pilot, [a, b], [ea, eb], [ia, ib], seed)
        second = archive.select_deterministically(pilot, [b, a], [eb, ea], [ib, ia], seed)
        self.assertEqual(first, second)
        self.assertEqual(first["selected_candidate_id"], b["candidate_id"])
        self.assertFalse(first["scientific_claim"])
        self.assertFalse(first["assurance_transition_requested"])
        self.assertEqual(first["supernova_credit"], archive.ZERO_CREDIT)

    def test_selector_ignores_diag_and_quarantined_evidence(self):
        pilot = self.pilot()
        candidate = self.candidate()
        diag = self.evaluation(pilot, candidate, partition="DIAG", pass_count=32)
        diag_i = archive.evidence_integrity(pilot, candidate, diag)
        none = archive.select_deterministically(pilot, [candidate], [diag], [diag_i], h(701))
        self.assertEqual(none["outcome"], "NO_ADMISSIBLE_EVIDENCE")
        selected = self.evaluation(pilot, candidate, partition="SELECT", pass_count=32)
        selected_i = archive.evidence_integrity(pilot, candidate, selected)
        selected_i["status"] = "QUARANTINED"
        selected_i = archive.bind_content_id(selected_i, "integrity_id")
        none = archive.select_deterministically(pilot, [candidate], [selected], [selected_i], h(701))
        self.assertEqual(none["outcome"], "NO_ADMISSIBLE_EVIDENCE")

    def test_selector_tie_break_is_seeded_and_deterministic(self):
        pilot = self.pilot()
        a = self.candidate(tree=10)
        b = self.candidate(tree=11)
        ea = self.evaluation(pilot, a, pass_count=20, cost=10)
        eb = self.evaluation(pilot, b, pass_count=20, cost=10)
        ia = archive.evidence_integrity(pilot, a, ea)
        ib = archive.evidence_integrity(pilot, b, eb)
        one = archive.select_deterministically(pilot, [a, b], [ea, eb], [ia, ib], h(702))
        two = archive.select_deterministically(pilot, [a, b], [ea, eb], [ia, ib], h(702))
        self.assertEqual(one, two)
        self.assertEqual(sum(row["selection_probability"] for row in one["ranking"]), 1.0)

    def test_selection_schema_rejects_bil00_mm06_or_promotion_fields(self):
        pilot = self.pilot()
        selection = archive.select_deterministically(pilot, [], [], [], h(703))
        for field in ("bil00_id", "mm06_verdict", "promotion_status"):
            with self.subTest(field=field):
                changed = dict(selection)
                changed[field] = "forbidden"
                changed = archive.bind_content_id(changed, "selection_id")
                self.assertTrue(archive.validate_selection(changed))

    def test_content_addressed_store_is_idempotent_and_detects_corruption(self):
        pilot = self.pilot()
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            digest, path, created = archive.put_immutable(root, pilot)
            self.assertTrue(created)
            self.assertEqual(path.read_bytes(), archive.canonical_bytes(pilot) + b"\n")
            digest2, path2, created2 = archive.put_immutable(root, pilot)
            self.assertEqual((digest2, path2, created2), (digest, path, False))
            path.write_bytes(b"corrupt\n")
            with self.assertRaisesRegex(ValueError, "different bytes"):
                archive.put_immutable(root, pilot)

    def test_archive_root_must_be_outside_git_worktree(self):
        with self.assertRaisesRegex(ValueError, "outside the Git worktree"):
            archive.require_external_archive_root(ROOT, ROOT / "evolution-archive")

    def test_record_id_domains_do_not_substitute(self):
        pilot = self.pilot()
        root = self.candidate(tree=1)
        child = self.candidate(root["candidate_id"], tree=2)
        proposal = self.proposal(child)
        changed = dict(proposal)
        changed["proposal_id"] = child["candidate_id"]
        self.assertIn(
            "content_id_mismatch:proposal_id",
            archive.validate_proposal(changed, child),
        )
        self.assertNotEqual(
            archive.content_id(proposal, "proposal_id"),
            archive.content_id(proposal, "candidate_id"),
        )

    def test_archive_snapshot_binds_provenance_and_evidence(self):
        pilot = self.pilot()
        root = self.candidate(tree=1)
        child = self.candidate(root["candidate_id"], tree=2)
        p1 = self.proposal(child, proposer="one", role="homogeneous-1")
        p2 = self.proposal(child, proposer="two", role="homogeneous-1")
        evaluation = self.evaluation(pilot, child)
        integrity = archive.evidence_integrity(pilot, child, evaluation)
        selection = archive.select_deterministically(
            pilot, [child], [evaluation], [integrity], h(800)
        )
        groups = {
            "candidate_ids": [child["candidate_id"]],
            "proposal_ids": sorted([p1["proposal_id"], p2["proposal_id"]]),
            "evaluation_ids": [evaluation["evaluation_id"]],
            "integrity_ids": [integrity["integrity_id"]],
            "selection_ids": [selection["selection_id"]],
        }
        snapshot = archive.make_archive_snapshot(pilot["pilot_id"], None, groups)
        self.assertEqual(archive.validate_archive_snapshot(snapshot), [])
        self.assertEqual(snapshot["scientific_state_effect"], "NONE")
        self.assertFalse(snapshot["promotion_eligible"])
        changed_groups = copy.deepcopy(groups)
        changed_groups["proposal_ids"] = [p1["proposal_id"]]
        changed = archive.make_archive_snapshot(pilot["pilot_id"], None, changed_groups)
        self.assertNotEqual(snapshot["snapshot_id"], changed["snapshot_id"])
        self.assertNotEqual(
            snapshot["object_set_root_sha256"], changed["object_set_root_sha256"]
        )

    def test_archive_snapshot_rejects_unsorted_duplicate_or_wrong_root(self):
        groups = {key: [] for key in archive.SNAPSHOT_CATEGORIES}
        groups["candidate_ids"] = [h(2), h(1)]
        with self.assertRaisesRegex(ValueError, "sorted and unique"):
            archive.make_archive_snapshot(h(900), None, groups)
        groups["candidate_ids"] = [h(1)]
        snapshot = archive.make_archive_snapshot(h(900), None, groups)
        snapshot["object_set_root_sha256"] = h(999)
        snapshot = archive.bind_content_id(snapshot, "snapshot_id")
        self.assertIn(
            "archive_object_set_root_mismatch",
            archive.validate_archive_snapshot(snapshot),
        )

    def test_every_record_type_is_zero_authority(self):
        pilot = self.pilot()
        root = self.candidate(tree=1)
        child = self.candidate(root["candidate_id"], tree=2)
        proposal = self.proposal(child)
        evaluation = self.evaluation(pilot, child)
        integrity = archive.evidence_integrity(pilot, child, evaluation)
        selection = archive.select_deterministically(pilot, [child], [evaluation], [integrity], h(704))
        snapshot = archive.make_archive_snapshot(
            pilot["pilot_id"],
            None,
            {
                "candidate_ids": sorted([root["candidate_id"], child["candidate_id"]]),
                "proposal_ids": [proposal["proposal_id"]],
                "evaluation_ids": [evaluation["evaluation_id"]],
                "integrity_ids": [integrity["integrity_id"]],
                "selection_ids": [selection["selection_id"]],
            },
        )
        for record in (pilot, root, child, proposal, evaluation, integrity, selection, snapshot):
            with self.subTest(record_type=record["record_type"]):
                self.assertEqual(record["authority"], "NONE_ENGINEERING_ONLY")
                self.assertEqual(record["supernova_credit"], archive.ZERO_CREDIT)
                self.assertEqual(archive.schema_errors(record), [])


if __name__ == "__main__":
    unittest.main()
