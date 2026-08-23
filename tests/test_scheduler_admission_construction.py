import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_guard_module():
    spec = importlib.util.spec_from_file_location("root11_scheduler_guard_construction", ROOT / "scripts/scheduler_admission_guard.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SchedulerAdmissionConstructionTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads((ROOT / "schemas/scheduler_admission.schema.json").read_text())
        self.copy = json.loads((ROOT / "schemas/scheduler_admission_copy.schema.json").read_text())
        self.manifest = json.loads((ROOT / "schemas/scheduler_manifest.schema.json").read_text())
        self.guard = (ROOT / "scripts/scheduler_admission_guard.py").read_text()

    def test_manifest_is_the_terminal_dag_node_not_a_self_hash(self):
        self.assertNotIn("generation_head_sha", self.manifest["properties"])
        self.assertIn("candidate_nonce", self.manifest["required"])
        self.assertIn("generation_root_sha", self.manifest["required"])
        for key in ("control_manifest_git_identity", "assignment_git_identity", "liveness_git_identity"):
            self.assertIn(key, self.manifest["required"])

    def test_mm06_source_has_no_self_containing_commit_or_blob(self):
        forbidden = {"source_preactivation_admission_commit_sha", "source_preactivation_admission_blob_sha",
                     "scheduler_admission_commit_sha", "scheduler_admission_blob_sha"}
        self.assertTrue(forbidden.isdisjoint(self.source["properties"]))
        self.assertIn("staged_candidate_git_identity", self.source["required"])
        self.assertEqual(self.source["properties"]["required_post_write_ci_context"]["const"], "supernova/preactivation-admission")

    def test_main_copy_is_a_distinct_create_once_source_envelope(self):
        self.assertEqual(self.copy["properties"]["creation_mode"]["const"], "CREATE_ONCE")
        self.assertIn("source_preactivation_admission_branch", self.copy["required"])
        self.assertIn("source_preactivation_admission_commit_sha", self.copy["required"])
        self.assertIn("source_preactivation_admission_blob_sha", self.copy["required"])
        self.assertEqual(self.copy["properties"]["source_preactivation_admission_branch"]["pattern"], "^ps/preactivate/[^/]+/MM06$")
        self.assertFalse(self.copy["additionalProperties"])
        self.assertEqual(self.source["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.copy["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_guard_cross_binds_pointer_manifest_mm06_and_copy_semantics(self):
        for token in (
            "validate_mm06_scheduler_admission",
            "MM06 scheduler admission/staged pointer mismatch",
            "scheduler admission copy/staged pointer mismatch",
            "scheduler admission copy/MM06 source semantic mismatch",
            "scheduler admission copy source schema mismatch",
            "staged_pointer_blob(root, staged)",
            "scheduler admission receipt missing; stage and promote must be distinct transactions",
        ):
            self.assertIn(token, self.guard)

    def test_promotion_guard_requires_admission_already_in_base_and_pointer_unchanged(self):
        text = (ROOT / "scripts/transition_guard.py").read_text()
        self.assertIn("root11 promotion must not introduce or modify scheduler admission", text)
        self.assertIn("root11 scheduler admission must already exist in base unchanged", text)
        self.assertIn("root11 promotion must preserve exact staged pointer blob", text)
        self.assertIn("root11 promotion CAS must differ from generation root", text)

    def test_pointer_only_admission_validates_observed_g_manifest_without_main_copy(self):
        guard = load_guard_module()
        observed = "a" * 40
        common = {
            "protocol_version": "2.5",
            "task_network_plan_id": guard.PLAN,
            "candidate_nonce": "root11-nonce",
            "cohort_id": "CAL-BR-013-v25-test",
            "generation_root_sha": "b" * 40,
        }
        manifest = dict(common)
        source = {
            **common,
            "schema_version": self.source["properties"]["schema_version"]["const"],
            "generation_head_sha": "c" * 40,
            "scheduler_manifest_git_identity": observed,
            "preactivation_results": [],
        }
        copy = {
            **common,
            "generation_head_sha": "c" * 40,
            "scheduler_manifest_git_identity": observed,
            "source_schema_version": source["schema_version"],
        }
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "schemas").mkdir()
            (root / "config").mkdir()
            for name in ("scheduler_admission.schema.json", "scheduler_admission_copy.schema.json", "preactivation_receipt.schema.json"):
                shutil.copyfile(ROOT / "schemas" / name, root / "schemas" / name)
            shutil.copyfile(ROOT / "config/scheduler_attestation_authority_v25.json", root / "config/scheduler_attestation_authority_v25.json")
            errors = guard.validate_scheduler_admission(
                root,
                manifest,
                copy,
                source=source,
                observed_manifest_blob=observed,
            )
        self.assertNotIn("independently observed scheduler manifest blob is unavailable", errors)
        self.assertNotIn("scheduler admission copy/manifest mismatch: scheduler_manifest_git_identity", errors)
        self.assertNotIn("scheduler admission copy is not bound to independently observed scheduler manifest blob", errors)


if __name__ == "__main__":
    unittest.main()
