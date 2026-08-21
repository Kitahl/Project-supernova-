import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SEED_INSTALL="1239e232e11f9710c472a6dded6121833d84ddcb"
PREV_ROOT_BLOB="ef79f664aee73862f685134253dbdd284a5f6986"

class Gen9ResetCompatRootTests(unittest.TestCase):
    def test_epoch4_binds_predecessor_and_independent_seed(self):
        root=json.loads((ROOT/"config/root_tcb_epoch_v25.json").read_text())
        self.assertEqual(root["schema_version"],"PS-ROOT-TCB-EPOCH-2.5-4")
        self.assertEqual(root["epoch"],4)
        self.assertEqual(root["previous_epoch_blob"],PREV_ROOT_BLOB)
        self.assertEqual(root["gen9_reset_compat_seed_install_commit_sha"],SEED_INSTALL)
        self.assertEqual(root["gen9_reset_compat_epoch_path"],"config/gen9_reset_compat_epoch_v25.json")

    def test_consumption_marker_binds_exact_accepted_seed_bytes(self):
        marker=json.loads((ROOT/"config/gen9_reset_compat_epoch_v25.json").read_text())
        self.assertEqual(marker["schema_version"],"PS-GEN9-RESET-COMPAT-EPOCH-2.5-1")
        self.assertEqual(marker["epoch"],1)
        self.assertEqual(marker["seed_install_commit_sha"],SEED_INSTALL)
        self.assertEqual(marker["seed_policy_blob"],"61d1f2458833ba167a8200e40625e32336c150fd")
        self.assertEqual(marker["seed_reconciler_blob"],"0d7ac818dcc36d8257726b361d8fb0d7079a9448")
        self.assertEqual(marker["seed_workflow_blob"],"372d2b559feff260bb65f73fecd898d60cd228f1")

    def test_admission_authority_inventories_seed_and_marker(self):
        adm=json.loads((ROOT/"config/admission_authority.json").read_text())
        self.assertEqual(adm["root_tcb_epoch"],4)
        helpers=set(adm["trusted_authority_helpers"])
        for path in ("config/gen9_reset_compat_seed_v25.json","scripts/reconcile_gen9_reset_compat_seed.py",".github/workflows/supernova-gen9-reset-compat-seed.yml","config/gen9_reset_compat_epoch_v25.json"):
            self.assertIn(path,helpers)
        self.assertEqual(adm["structural_status_writer_cardinality"],1)

    def test_countable_freeze_contains_complete_compatibility_repair(self):
        ctl=json.loads((ROOT/"config/countable_control_set_v25.json").read_text())
        self.assertEqual(ctl["schema_version"],"PS-COUNTABLE-CONTROL-SET-2.5-17")
        paths=set(ctl["required_control_paths"])
        for path in ("config/gen9_reset_compat_seed_v25.json","scripts/reconcile_gen9_reset_compat_seed.py",".github/workflows/supernova-gen9-reset-compat-seed.yml","tests/test_gen9_reset_compat_seed.py","config/gen9_reset_compat_epoch_v25.json","tests/test_gen9_reset_compat_root.py","scripts/reconcile_open_prs.py","tests/test_gen9_zero_credit_reset.py"):
            self.assertIn(path,paths)

    def test_reset_fix_uses_blob_identities_and_does_not_weaken_schema(self):
        source=(ROOT/"scripts/reconcile_open_prs.py").read_text()
        self.assertNotIn('"control_manifest_path":cp,"assignment_path":ap',source)
        self.assertIn('HEAD:"+cp',source)
        self.assertIn('HEAD:"+ap',source)
        self.assertIn('control_manifest_git_identity',source)
        self.assertIn('assignment_git_identity',source)
        schema=json.loads((ROOT/"schemas/cohort_liveness_contract.schema.json").read_text())
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("control_manifest_path",schema["properties"])
        self.assertNotIn("assignment_path",schema["properties"])

if __name__=="__main__":
    unittest.main()
