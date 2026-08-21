import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "parent_lineage_guard.py"
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
OLD_FOUNDRY = "a9f220078a0c087a1c80a4bc6255951225734f7e73b50660138c20372257a0e8"
OLD_MASTERMIND = "e54f98cc9a1d527fda6626a01d6e8bf67ba71cc728b75263f3e88459436a9812"
NEW_FOUNDRY = "5bfe4bf2cc7e8c4cb9751b831803e28eb45cebe22c0085310c8f00459caf994e"
NEW_MASTERMIND = "026a4d845ac021baa9f90c7c48c1f77f19f57065d257e45824025f5f467a9d0d"
RUNTIME_ID = "9d0a88cc9001295b5e4c0f4163e83c0fd64ce04521e34230ad3539af14f3dfaf"
RUNTIME_PLAN = "f0031a07c1cfb23a8183e393b3ef26c92cd7cfa7b64e00af4466b52d90dc02d8"


def load_module():
    spec = importlib.util.spec_from_file_location("parent_lineage_guard_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RuntimeUpdateLineageTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "schemas").mkdir(parents=True)
        (self.root / "config").mkdir(parents=True)
        (self.root / "runtime" / "updates").mkdir(parents=True)
        shutil.copy2(ROOT / "schemas" / "runtime_update.schema.json", self.root / "schemas" / "runtime_update.schema.json")

        # This test models a synthetic substrate transition. Its epoch fixture must
        # describe the synthetic post-transition state, not whichever Foundry release
        # happens to be active in the repository when the regression is run.
        epoch = json.loads((ROOT / "config" / "substrate_epoch_v25.json").read_text(encoding="utf-8"))
        epoch["math_foundry"]["source_archive_sha256"] = NEW_FOUNDRY
        epoch["mastermind"]["sha256"] = NEW_MASTERMIND
        (self.root / "config" / "substrate_epoch_v25.json").write_text(
            json.dumps(epoch, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        self.parent = self.runtime_state(OLD_FOUNDRY, OLD_MASTERMIND)
        self.current = self.runtime_state(NEW_FOUNDRY, NEW_MASTERMIND)
        self.current["runtime_update_receipt_path"] = "runtime/updates/GEN7-SUBSTRATE.json"

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def runtime_state(foundry, mastermind):
        return {
            "task_network_plan_id": PLAN,
            "base_runtime_state_id": RUNTIME_ID,
            "runtime_state_id": RUNTIME_ID,
            "foundry_sha256": foundry,
            "mastermind_sha256": mastermind,
            "actual_runtime_plan_id": RUNTIME_PLAN,
            "canonical_bus_repo": "Kitahl/Project-supernova-",
            "private_vault_repo": "Kitahl/thoma",
        }

    def receipt(self):
        before = {k: self.parent.get(k) for k in self.mod.RUNTIME}
        after = {k: self.current.get(k) for k in self.mod.RUNTIME}
        return {
            "task_network_plan_id": PLAN,
            "runtime_update_id": "GEN7-REPLAY-SUBSTRATE-BINDING",
            "runtime_before": RUNTIME_ID,
            "runtime_after": RUNTIME_ID,
            "artifact_hashes": {
                "foundry_sha256": NEW_FOUNDRY,
                "mastermind_sha256": NEW_MASTERMIND,
                "substrate_epoch_path": "config/substrate_epoch_v25.json",
                "substrate_epoch_git_identity": self.mod.git_blob_sha(self.root / "config" / "substrate_epoch_v25.json"),
            },
            "validator_results": [
                {"validator": "candidate7-clean-archive-replay", "status": "PASS"},
                {"validator": "mastermind-4.4.10-package-qualification", "status": "PASS"},
            ],
            "lineage_identity": "GEN6_TO_GEN7_SAME_RUNTIME_REPLAY_SUBSTRATE",
            "accounting_identity": "ZERO_FRESH_ZERO_SCIENTIFIC_CREDIT",
            "before_after_diagnostics": {
                "update_class": "REPLAY_CALIBRATION_SUBSTRATE_BINDING",
                "runtime_bound_before": before,
                "runtime_bound_after": after,
            },
            "fresh_prospective_evidence_refs": [],
            "preservation_regression_checks": [
                {"check": "runtime_state_id_unchanged", "status": "PASS"},
                {"check": "fresh_evidence_zero", "status": "PASS"},
                {"check": "scientific_status_unchanged", "status": "PASS"},
            ],
            "independent_verification": {
                "status": "PASS",
                "qualification_class": "SOFTWARE_REPLAY_CALIBRATION_ONLY",
                "scientific_status_changed": False,
                "fresh_evidence_consumed": False,
            },
            "status": "VALIDATED",
        }

    def write_receipt(self, obj):
        path = self.root / self.current["runtime_update_receipt_path"]
        path.write_text(json.dumps(obj), encoding="utf-8")

    def errors(self):
        return self.mod.runtime_receipt_errors(self.root, self.parent, self.current, ["foundry_sha256", "mastermind_sha256"])

    def test_fixture_epoch_tracks_synthetic_candidate_not_live_release(self):
        epoch = json.loads((self.root / "config" / "substrate_epoch_v25.json").read_text(encoding="utf-8"))
        self.assertEqual(epoch["math_foundry"]["source_archive_sha256"], NEW_FOUNDRY)
        self.assertEqual(epoch["mastermind"]["sha256"], NEW_MASTERMIND)

    def test_valid_replay_substrate_receipt_passes(self):
        self.write_receipt(self.receipt()); self.assertEqual(self.errors(), [])

    def test_missing_receipt_fails(self):
        self.assertTrue(any("without runtime update receipt" in e for e in self.errors()))

    def test_malformed_receipt_fails(self):
        (self.root / self.current["runtime_update_receipt_path"]).write_text("{not-json", encoding="utf-8"); self.assertTrue(self.errors())

    def test_non_validated_status_fails(self):
        r=self.receipt(); r["status"]="INCOMPLETE"; self.write_receipt(r); self.assertTrue(any("status is not VALIDATED" in e for e in self.errors()))

    def test_rejected_status_fails(self):
        r=self.receipt(); r["status"]="REJECTED"; self.write_receipt(r); self.assertTrue(any("status is not VALIDATED" in e for e in self.errors()))

    def test_wrong_runtime_after_fails(self):
        r=self.receipt(); r["runtime_after"]="wrong-runtime"; self.write_receipt(r); self.assertTrue(any("runtime_after mismatch" in e for e in self.errors()))

    def test_wrong_before_binding_fails(self):
        r=self.receipt(); r["before_after_diagnostics"]["runtime_bound_before"]["foundry_sha256"]="0"*64; self.write_receipt(r); self.assertTrue(any("before binding mismatch: foundry_sha256" in e for e in self.errors()))

    def test_wrong_after_binding_fails(self):
        r=self.receipt(); r["before_after_diagnostics"]["runtime_bound_after"]["mastermind_sha256"]="0"*64; self.write_receipt(r); self.assertTrue(any("after binding mismatch: mastermind_sha256" in e for e in self.errors()))

    def test_wrong_artifact_hash_fails(self):
        r=self.receipt(); r["artifact_hashes"]["foundry_sha256"]="0"*64; self.write_receipt(r); self.assertTrue(any("Foundry hash mismatch" in e for e in self.errors()))

    def test_wrong_substrate_epoch_blob_fails(self):
        r=self.receipt(); r["artifact_hashes"]["substrate_epoch_git_identity"]="0"*40; self.write_receipt(r); self.assertTrue(any("substrate epoch blob mismatch" in e for e in self.errors()))

    def test_fresh_evidence_in_replay_binding_fails(self):
        r=self.receipt(); r["fresh_prospective_evidence_refs"]=["forbidden-fresh-ref"]; self.write_receipt(r); self.assertTrue(any("consumed fresh prospective evidence" in e for e in self.errors()))

    def test_failed_validator_row_fails(self):
        r=self.receipt(); r["validator_results"][0]["status"]="FAIL"; self.write_receipt(r); self.assertTrue(any("validator_results[0] is not PASS" in e for e in self.errors()))

    def test_wrong_independent_qualification_class_fails(self):
        r=self.receipt(); r["independent_verification"]["qualification_class"]="SCIENTIFIC_PROMOTION"; self.write_receipt(r); self.assertTrue(any("qualification class mismatch" in e for e in self.errors()))

    def test_path_traversal_is_rejected(self):
        self.current["runtime_update_receipt_path"]="../escape.json"; self.assertTrue(any("requires runtime/updates" in e for e in self.errors()))


if __name__ == "__main__": unittest.main()
