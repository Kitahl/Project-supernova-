import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Gen9ResetCompatRootTests(unittest.TestCase):
    def test_root_epoch4_binds_seed_and_predecessor(self):
        root = load("config/root_tcb_epoch_v25.json")
        marker = load("config/gen9_reset_compat_epoch_v25.json")
        self.assertEqual(root["schema_version"], "PS-ROOT-TCB-EPOCH-2.5-4")
        self.assertEqual(root["epoch"], 4)
        self.assertEqual(root["previous_epoch_blob"], "ef79f664aee73862f685134253dbdd284a5f6986")
        self.assertEqual(root["gen9_reset_compat_seed_install_commit_sha"], marker["seed_install_commit_sha"])
        self.assertEqual(root["gen9_reset_liveness_binding"], "CONTROL_AND_ASSIGNMENT_GIT_BLOB_IDENTITIES")

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

    def test_compatibility_seed_becomes_frozen_and_one_shot(self):
        seed = load("config/gen9_reset_compat_seed_v25.json")
        marker = load("config/gen9_reset_compat_epoch_v25.json")
        controls = set(load("config/countable_control_set_v25.json")["required_control_paths"])
        self.assertEqual(seed["one_shot_marker_path"], "config/gen9_reset_compat_epoch_v25.json")
        self.assertEqual(marker["seed_one_shot_disposition"], "PERMANENTLY_INERT_AFTER_THIS_MARKER_IS_ACCEPTED")
        for path in seed["seed_paths"] + [seed["one_shot_marker_path"], "tests/test_gen9_reset_compat_root.py"]:
            self.assertIn(path, controls)

    def test_admission_inventory_is_epoch4_and_contains_seed(self):
        authority = load("config/admission_authority.json")
        self.assertEqual(authority["root_tcb_epoch"], 4)
        self.assertEqual(authority["gen9_reset_liveness_binding"], "CONTROL_AND_ASSIGNMENT_GIT_BLOB_IDENTITIES")
        helpers = set(authority["trusted_authority_helpers"])
        for path in (
            "config/gen9_reset_compat_seed_v25.json",
            "scripts/reconcile_gen9_reset_compat_seed.py",
            ".github/workflows/supernova-gen9-reset-compat-seed.yml",
            "config/gen9_reset_compat_epoch_v25.json",
        ):
            self.assertIn(path, helpers)


if __name__ == "__main__":
    unittest.main()
