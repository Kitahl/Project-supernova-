import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
EPOCH2_ACTIVATION_PREDECESSOR = "98c5ed4685855446dbb7e8b3537c839a39adf2c4"
STRUCTURAL_PREDECESSOR = "ab5c19399bb5bf06fc92c670ebe0fa1d593b04a9"
GEN7_RESET_PREDECESSOR = "04340ffda9495588442f74c74f2bf39558557291"
NORMAL_CONTEXTS = (
    "supernova/static-control",
    "supernova/report-admission",
    "supernova/transition-admission",
)

def load_module(path):
    name = "seed_predecessor_" + pathlib.Path(path).stem
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def write_json(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value), encoding="utf-8")

def git_json(commit, path):
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(result.stdout)

def pr_for(module, head_ref):
    return {
        "head": {
            "sha": "b" * 40,
            "ref": head_ref,
            "repo": {"full_name": module.REPO},
        },
        "base": {"sha": "a" * 40, "ref": "main"},
        "user": {"login": module.OWNER},
    }

class SeedPredecessorGuardTests(unittest.TestCase):
    def test_history_derives_activation_schemas_and_both_exact_epoch2_predecessors(self):
        root = load_module("scripts/reconcile_root_rotation_seed.py")
        structural = load_module("scripts/reconcile_structural_status_rotation_seed.py")
        gen7 = load_module("scripts/reconcile_gen7_repair_reset_seed.py")
        self.assertEqual(
            git_json(EPOCH2_ACTIVATION_PREDECESSOR, "config/admission_authority.json")["schema_version"],
            root.ACTIVATION_AUTHORITY_SCHEMA,
        )
        self.assertEqual(
            git_json(EPOCH2_ACTIVATION_PREDECESSOR, "config/authority_bootstrap_v25.json")["schema_version"],
            root.ACTIVATION_BOOTSTRAP_SCHEMA,
        )
        absent = subprocess.run(
            ["git", "cat-file", "-e", f"{EPOCH2_ACTIVATION_PREDECESSOR}:config/root_tcb_epoch_v25.json"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(absent.returncode, 0)
        for commit, module in (
            (STRUCTURAL_PREDECESSOR, structural),
            (GEN7_RESET_PREDECESSOR, gen7),
        ):
            with self.subTest(commit=commit):
                observed = git_json(commit, module.ROOT_TCB_PATH)
                self.assertEqual(observed, module.EXPECTED_ROOT_EPOCH2_IDENTITY)

    def test_epoch2_classifier_rejects_partial_extra_malformed_and_every_identity_mutation(self):
        for path in (
            "scripts/reconcile_structural_status_rotation_seed.py",
            "scripts/reconcile_gen7_repair_reset_seed.py",
        ):
            module = load_module(path)
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                with mock.patch.object(module, "ROOT", root):
                    self.assertIsNone(module.accepted_predecessor_root_epoch())
                    write_json(root, module.ROOT_TCB_PATH, {"epoch": 2})
                    self.assertIsNone(module.accepted_predecessor_root_epoch())
                    write_json(root, module.ROOT_TCB_PATH, {**module.EXPECTED_ROOT_EPOCH2_IDENTITY, "extra": True})
                    self.assertIsNone(module.accepted_predecessor_root_epoch())
                    for key, value in module.EXPECTED_ROOT_EPOCH2_IDENTITY.items():
                        mutated = dict(module.EXPECTED_ROOT_EPOCH2_IDENTITY)
                        mutated[key] = (value + "-wrong") if isinstance(value, str) else 3
                        write_json(root, module.ROOT_TCB_PATH, mutated)
                        self.assertIsNone(module.accepted_predecessor_root_epoch(), key)
                    write_json(root, module.ROOT_TCB_PATH, module.EXPECTED_ROOT_EPOCH2_IDENTITY)
                    self.assertEqual(module.accepted_predecessor_root_epoch(), 2)
                    (root / module.ROOT_TCB_PATH).write_text("{", encoding="utf-8")
                    self.assertIsNone(module.accepted_predecessor_root_epoch())

    def test_activation_classifier_requires_no_marker_and_exact_v4_v2_schemas(self):
        module = load_module("scripts/reconcile_root_rotation_seed.py")
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            write_json(root, "config/admission_authority.json", {"schema_version": module.ACTIVATION_AUTHORITY_SCHEMA})
            write_json(root, "config/authority_bootstrap_v25.json", {"schema_version": module.ACTIVATION_BOOTSTRAP_SCHEMA})
            with mock.patch.object(module, "ROOT", root):
                self.assertEqual(module.accepted_predecessor_root_epoch(), 1)
                write_json(root, "config/admission_authority.json", {"schema_version": "PS-ADMISSION-AUTHORITY-2.5-3"})
                self.assertIsNone(module.accepted_predecessor_root_epoch())
                write_json(root, "config/admission_authority.json", {"schema_version": module.ACTIVATION_AUTHORITY_SCHEMA})
                write_json(root, "config/authority_bootstrap_v25.json", {"schema_version": "PS-AUTHORITY-BOOTSTRAP-2.5-1"})
                self.assertIsNone(module.accepted_predecessor_root_epoch())
                write_json(root, "config/authority_bootstrap_v25.json", {"schema_version": module.ACTIVATION_BOOTSTRAP_SCHEMA})
                write_json(root, module.ROOT_TCB_PATH, {"epoch": 2})
                self.assertIsNone(module.accepted_predecessor_root_epoch())

    def test_main_paths_fail_before_candidate_fetch_on_predecessor_mismatch(self):
        cases = (
            (
                "scripts/reconcile_root_rotation_seed.py",
                "root-rotation/test",
                {
                    "head_prefix_required": "root-rotation/",
                    "one_shot_marker_path": "config/root_tcb_epoch_v25.json",
                    "seed_context": "supernova/root-rotation-seed",
                },
            ),
            (
                "scripts/reconcile_structural_status_rotation_seed.py",
                "structural-rotation/test",
                {
                    "head_prefix_required": "structural-rotation/",
                    "one_shot_marker_path": "config/structural_status_rotation_epoch_v25.json",
                    "seed_context": "supernova/structural-status-rotation-seed",
                },
            ),
            (
                "scripts/reconcile_gen7_repair_reset_seed.py",
                "repair-reset/test",
                {
                    "head_prefix_required": "repair-reset/",
                    "one_shot_marker_path": "config/gen7_repair_reset_epoch_v25.json",
                    "seed_context": "supernova/gen7-repair-reset-seed",
                },
            ),
        )
        for path, head_ref, policy in cases:
            module = load_module(path)
            candidate = pr_for(module, head_ref)
            state = {
                "calibration_streak": 0,
                "fresh_allowed_globally": False,
            }
            if "structural_status" in path:
                state.update({
                    "active_cohort_id": module.GEN9_COHORT,
                    "generation_head_sha": module.GEN9_G,
                    "foundry_sha256": module.FOUNDRY,
                    "mastermind_sha256": module.MASTERMIND,
                    "runtime_state_id": module.RUNTIME,
                })
            if "gen7_repair" in path:
                policy.update({
                    "exact_invalidated_state_blob": "1" * 40,
                    "exact_invalidated_cohort": "cohort",
                    "exact_invalidated_generation_head": "2" * 40,
                })
                state.update({
                    "active_cohort_id": policy["exact_invalidated_cohort"],
                    "generation_head_sha": policy["exact_invalidated_generation_head"],
                })
            def fake_load(_root, requested):
                if requested.endswith("_seed_v25.json"):
                    return policy
                if requested == "state/CURRENT.json":
                    return state
                if requested == "config/root_tcb_epoch_v25.json":
                    return {"epoch": 2}
                if requested == "config/admission_authority.json":
                    return {"schema_version": "PS-WRONG"}
                if requested == "config/authority_bootstrap_v25.json":
                    return {"schema_version": module.ACTIVATION_BOOTSTRAP_SCHEMA}
                raise AssertionError(requested)
            def fake_run(command, cwd=None):
                if command == ["git", "rev-parse", "HEAD"]:
                    return 0, candidate["base"]["sha"] + "\n"
                if command == ["git", "rev-parse", "HEAD:state/CURRENT.json"]:
                    return 0, policy["exact_invalidated_state_blob"] + "\n"
                raise AssertionError("candidate work began: " + repr(command))
            env = {
                "PR_NUMBER": "1",
                "CANDIDATE_DIAGNOSTICS_RESULT": "success",
                "DIAGNOSED_HEAD_SHA": candidate["head"]["sha"],
                "DIAGNOSED_BASE_SHA": candidate["base"]["sha"],
            }
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                with (
                    mock.patch.object(module, "ROOT", pathlib.Path(directory)),
                    mock.patch.object(module, "api", return_value=candidate),
                    mock.patch.object(module, "load", side_effect=fake_load),
                    mock.patch.object(module, "run", side_effect=fake_run),
                    mock.patch.object(module, "fail", return_value=1) as failed,
                    mock.patch.dict(os.environ, env, clear=False),
                ):
                    if "structural_status" in path:
                        with mock.patch.object(module, "git_blob", return_value=module.GEN9_STATE_BLOB):
                            self.assertEqual(module.main(), 1)
                    else:
                        self.assertEqual(module.main(), 1)
                self.assertIn("predecessor root epoch", failed.call_args.args[1] if "root_rotation_seed.py" not in path else failed.call_args.args[1])
                self.assertEqual(failed.call_count, 1)

    def test_scripts_preserve_receipt_only_status_partition(self):
        for path in (
            "scripts/reconcile_root_rotation_seed.py",
            "scripts/reconcile_structural_status_rotation_seed.py",
            "scripts/reconcile_gen7_repair_reset_seed.py",
        ):
            source = (ROOT / path).read_text(encoding="utf-8")
            with self.subTest(path=path):
                for context in NORMAL_CONTEXTS:
                    self.assertNotIn(context, source)
                self.assertIn("accepted_predecessor_root_epoch()!=EXPECTED_PREDECESSOR_ROOT_EPOCH", source)

if __name__ == "__main__":
    unittest.main()
