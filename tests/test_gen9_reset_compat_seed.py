import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class Gen9ResetCompatSeedContract(unittest.TestCase):
    def test_seed_is_narrow_and_one_shot(self):
        p=json.loads((ROOT/"config/gen9_reset_compat_seed_v25.json").read_text())
        self.assertEqual(p["head_prefix_required"],"reset-compat/")
        self.assertEqual(p["required_current_root_tcb_epoch"],3)
        self.assertEqual(p["one_shot_marker_path"],"config/gen9_reset_compat_epoch_v25.json")
        self.assertEqual(set(p["allowed_root_candidate_paths"]),set(p["required_root_candidate_paths"]))
        self.assertNotIn("state/CURRENT.json",p["allowed_root_candidate_paths"])
        self.assertTrue(all(x not in p["allowed_root_candidate_paths"] for x in p["seed_paths"]))

    def test_privileged_job_executes_accepted_main_seed_only(self):
        text=(ROOT/".github/workflows/supernova-gen9-reset-compat-seed.yml").read_text()
        self.assertIn("pull_request_target:",text)
        self.assertIn("persist-credentials: false",text)
        self.assertIn("GITHUB_TOKEN: ''",text)
        self.assertIn("cd trusted && python3 scripts/reconcile_gen9_reset_compat_seed.py",text)
        self.assertNotIn("cd trusted && python3 ../",text)

    def test_seed_script_forbids_state_and_self_modification(self):
        text=(ROOT/"scripts/reconcile_gen9_reset_compat_seed.py").read_text()
        self.assertIn("seed self-modification forbidden",text)
        self.assertIn("state changed in root repair candidate",text)
        self.assertIn("candidate diff is not exactly the authorized root repair set",text)
        self.assertIn("unsatisfiable liveness path predicate still present",text)

if __name__=="__main__":
    unittest.main()
