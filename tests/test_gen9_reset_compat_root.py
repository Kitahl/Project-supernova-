import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EPOCH6_BLOB = "5a087dead0572390565bfe8bfb8f2ce69a80fc7c"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Gen9ResetCompatRootTests(unittest.TestCase):
    def test_root_epoch7_binds_epoch6_predecessor_and_preserves_gen9_compat(self):
        root = load("config/root_tcb_epoch_v25.json")
        marker = load("config/gen9_reset_compat_epoch_v25.json")
        self.assertEqual(root["schema_version"], "PS-ROOT-TCB-EPOCH-2.5-7")
        self.assertEqual(root["epoch"], 7)
        self.assertEqual(root["previous_epoch_blob"], EPOCH6_BLOB)
        self.assertEqual(root["gen9_reset_liveness_binding"], "CONTROL_AND_ASSIGNMENT_GIT_BLOB_IDENTITIES")
        self.assertEqual(marker["schema_version"], "PS-GEN9-RESET-COMPAT-EPOCH-2.5-1")
        self.assertEqual(marker["seed_one_shot_disposition"], "PERMANENTLY_INERT_AFTER_THIS_MARKER_IS_ACCEPTED")

    def test_root_predicate_uses_schema_valid_blob_identity_bindings(self):
        source = (ROOT / "scripts" / "reconcile_open_prs.py").read_text(encoding="utf-8")
        self.assertNotIn('"control_manifest_path":cp,"assignment_path":ap', source)
        for token in (
            "control_manifest_git_identity",
            "assignment_git_identity",
            'HEAD:"+cp',
            'HEAD:"+ap',
        ):
            self.assertIn(token, source)

    def test_closed_liveness_schema_is_not_weakened(self):
        schema = load("schemas/cohort_liveness_contract.schema.json")
        self.assertIs(schema["additionalProperties"], False)
        self.assertNotIn("control_manifest_path", schema["properties"])
        self.assertNotIn("assignment_path", schema["properties"])
        self.assertIn("control_manifest_git_identity", schema["properties"])
        self.assertIn("assignment_git_identity", schema["properties"])

    def test_compatibility_seed_remains_frozen_historical_evidence(self):
        seed = load("config/gen9_reset_compat_seed_v25.json")
        marker = load("config/gen9_reset_compat_epoch_v25.json")
        controls = set(load("config/countable_control_set_v25.json")["required_control_paths"])
        self.assertEqual(seed["one_shot_marker_path"], "config/gen9_reset_compat_epoch_v25.json")
        self.assertEqual(marker["seed_one_shot_disposition"], "PERMANENTLY_INERT_AFTER_THIS_MARKER_IS_ACCEPTED")
        for path in seed["seed_paths"] + [seed["one_shot_marker_path"], "tests/test_gen9_reset_compat_root.py"]:
            self.assertIn(path, controls)

    def test_admission_inventory_is_epoch7_and_retains_all_prior_root_assets(self):
        authority = load("config/admission_authority.json")
        self.assertEqual(authority["root_tcb_epoch"], 7)
        self.assertEqual(authority["gen9_reset_liveness_binding"], "CONTROL_AND_ASSIGNMENT_GIT_BLOB_IDENTITIES")
        helpers = set(authority["trusted_authority_helpers"])
        for path in (
            "config/gen9_reset_compat_seed_v25.json",
            "scripts/reconcile_gen9_reset_compat_seed.py",
            ".github/workflows/supernova-gen9-reset-compat-seed.yml",
            "config/gen9_reset_compat_epoch_v25.json",
            "config/root_epoch6_repair_seed_v25.json",
            "scripts/reconcile_root_epoch6_repair_seed.py",
            ".github/workflows/supernova-root-epoch6-repair-seed.yml",
            "config/root_epoch6_repair_epoch_v25.json",
            "config/root_epoch7_repair_seed_v25.json",
            "scripts/reconcile_root_epoch7_repair_seed.py",
            ".github/workflows/supernova-root-epoch7-repair-seed.yml",
            "config/root_epoch7_repair_epoch_v25.json",
        ):
            self.assertIn(path, helpers)


if __name__ == "__main__":
    unittest.main()
