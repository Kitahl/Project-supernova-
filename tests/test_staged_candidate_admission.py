import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"


def pointer():
    cohort = "CAL-R11-TEST"
    return {
        "schema_version": "PS-STAGED-CANDIDATE-2.5-1", "protocol_version": "2.5",
        "task_network_plan_id": PLAN, "status": "STAGED", "stage_base_head": "a" * 40,
        "active_state_path": "state/CURRENT.json", "active_state_git_identity": "b" * 40,
        "active_cohort_id": "CAL-BR-012-v25-4ca0dec6", "active_generation_seq": 12,
        "candidate_nonce": "c" * 64, "candidate_cohort_id": cohort, "candidate_generation_seq": 13,
        "generation_branch": f"ps/gen/{cohort}", "generation_root_sha": "a" * 40,
        "generation_head_sha": "d" * 40,
        "control_path": f"control/{cohort}.json", "control_git_identity": "e" * 40,
        "assignment_path": f"assignments/{cohort}.json", "assignment_git_identity": "f" * 40,
        "liveness_path": f"liveness/{cohort}.json", "liveness_git_identity": "1" * 40,
        "scheduler_manifest_path": f"scheduler/{cohort}.json", "scheduler_manifest_git_identity": "2" * 40,
        "scheduler_admission_path": f"scheduler_admission/{cohort}.json",
        "calibration_countable": True, "calibration_credit": 0, "fresh_allowed": False,
    }


class StagedCandidateAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((ROOT / "schemas/staged_candidate.schema.json").read_text())

    def errors(self, value):
        errors = []
        for key in self.schema["required"]:
            if key not in value:
                errors.append("missing " + key)
        if set(value) - set(self.schema["properties"]):
            errors.append("unexpected property")
        for key in ("stage_base_head", "generation_root_sha", "generation_head_sha"):
            if key in value and (not isinstance(value[key], str) or len(value[key]) != 40 or any(c not in "0123456789abcdef" for c in value[key])):
                errors.append("invalid " + key)
        nonce = value.get("candidate_nonce")
        if not isinstance(nonce, str) or len(nonce) != 64 or any(c not in "0123456789abcdef" for c in nonce):
            errors.append("invalid candidate_nonce")
        return errors

    def test_valid_pointer_is_closed_and_binds_all_preexisting_objects(self):
        value = pointer()
        self.assertEqual(self.errors(value), [])
        self.assertFalse(self.schema["additionalProperties"])
        self.assertNotIn("staged_candidate_git_identity", self.schema["properties"])

    def test_stale_or_wrong_commit_and_nonce_shapes_fail_schema(self):
        for key, value in (("stage_base_head", "bad"), ("generation_root_sha", "g" * 40),
                           ("generation_head_sha", "h" * 40), ("candidate_nonce", "short")):
            candidate = pointer(); candidate[key] = value
            with self.subTest(key=key):
                self.assertTrue(self.errors(candidate))

    def test_pointer_schema_forbids_a_sixteenth_task_or_admission_copy_contents(self):
        candidate = pointer()
        candidate["tasks"] = [{"role_id": "MM08"}]
        self.assertTrue(self.errors(candidate))
        candidate = pointer()
        candidate["source_preactivation_admission_commit_sha"] = "0" * 40
        self.assertTrue(self.errors(candidate))

    def test_pointer_contract_requires_follow_on_not_same_pr_admission(self):
        epoch = json.loads((ROOT / "config/root_epoch11_stageability_repair_epoch_v25.json").read_text())
        self.assertEqual(epoch["stage_pointer_transaction"], "POINTER_ONLY_PR_AFTER_G")
        self.assertEqual(epoch["scheduler_admission_transaction"], "CREATE_ONCE_ENVELOPE_AFTER_POINTER_MERGE")
        self.assertEqual(epoch["promotion_transaction"], "LATER_CAS_WITH_ADMISSION_ALREADY_IN_BASE_AND_UNCHANGED_PLUS_BYTE_IDENTICAL_PER_COHORT_POINTER_ARCHIVE")


if __name__ == "__main__":
    unittest.main()
