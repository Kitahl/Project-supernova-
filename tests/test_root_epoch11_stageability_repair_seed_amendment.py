import ast
import collections
import importlib.util
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "root_epoch11_stageability_repair_seed_amendment_v25.json"
ORIGINAL_POLICY = ROOT / "config" / "root_epoch11_stageability_repair_seed_v25.json"
SCRIPT = ROOT / "scripts" / "reconcile_root_epoch11_stageability_repair_seed_amendment.py"
WORKFLOW = ROOT / ".github" / "workflows" / "supernova-root-epoch11-stageability-repair-seed-amendment.yml"


def load_amendment_module():
    spec = importlib.util.spec_from_file_location("root11_seed_amendment_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def apply_reviewed_candidate_transformations(root: pathlib.Path) -> set[str]:
    changed: set[str] = set()

    def replace(path: str, old: str, new: str, count: int = 1):
        target = root / path
        raw = target.read_bytes().replace(b"\r\n", b"\n")
        old_bytes = old.encode()
        new_bytes = new.encode()
        if raw.count(old_bytes) != count:
            raise AssertionError((path, raw.count(old_bytes), count, old))
        target.write_bytes(raw.replace(old_bytes, new_bytes))
        changed.add(path)

    am_config = "config/root_epoch11_stageability_repair_seed_amendment_v25.json"
    am_script = "scripts/reconcile_root_epoch11_stageability_repair_seed_amendment.py"
    am_workflow = ".github/workflows/supernova-root-epoch11-stageability-repair-seed-amendment.yml"
    am_test = "tests/test_root_epoch11_stageability_repair_seed_amendment.py"

    replace("config/root_epoch11_stageability_repair_epoch_v25.json", "PS-ROOT-EPOCH11-STAGEABILITY-REPAIR-2.5-1", "PS-ROOT-EPOCH11-STAGEABILITY-REPAIR-EPOCH-2.5-1")
    replace("schemas/assignment.schema.json", '  },\n  "required": ["task_network_plan_id",', '  },\n  "allOf": [\n    {\n      "if": {"required": ["candidate_nonce"]},\n      "then": {"required": ["generation_root_sha"]}\n    }\n  ],\n  "required": ["task_network_plan_id",')
    replace("schemas/assignment.schema.json", ', "generation_branch", "generation_root_sha", "workers",', ', "generation_branch", "workers",')
    replace("schemas/cohort_liveness_contract.schema.json", '    "generation_seq",\n    "generation_root_sha",\n    "control_manifest_id",', '    "generation_seq",\n    "control_manifest_id",')
    replace("schemas/cohort_liveness_contract.schema.json", '    }\n  }\n}\n', '    }\n  },\n  "allOf": [\n    {\n      "if": {"required": ["candidate_nonce"]},\n      "then": {"required": ["generation_root_sha"]}\n    }\n  ]\n}\n')
    replace("scripts/transition_guard.py", '  if rc_archive or archive_blob!=s.get("active_staged_candidate_git_identity"):e.append("root11 archived staged pointer blob mismatch")\n  generation_root=staged.get("generation_root_sha")', '  if rc_archive or archive_blob!=s.get("active_staged_candidate_git_identity"):e.append("root11 archived staged pointer blob mismatch")\n  if staged.get("generation_head_sha")!=s.get("generation_head_sha"):e.append("root11 active state generation head differs from archived staged pointer")\n  generation_root=staged.get("generation_root_sha")')
    replace("tests/test_scheduler_admission_construction.py", '        self.assertIn("root11 promotion CAS must differ from generation root", text)\n', '        self.assertIn("root11 promotion CAS must differ from generation root", text)\n        self.assertIn(\'staged.get("generation_head_sha")!=s.get("generation_head_sha")\', text)\n        self.assertIn("root11 active state generation head differs from archived staged pointer", text)\n')
    replace("scripts/scheduler_admission_guard.py", '    observed_manifest_blob: str | None = None,\n    require_inactive_production_fence: bool = False,\n) -> list[str]:\n    errors = schema_errors(root, "schemas/scheduler_admission.schema.json", admission)', '    observed_manifest_blob: str | None = None,\n    require_inactive_production_fence: bool = False,\n    expected_generation_head: str | None = None,\n) -> list[str]:\n    errors = schema_errors(root, "schemas/scheduler_admission.schema.json", admission)\n    actual_candidate_head = expected_generation_head\n    if actual_candidate_head is None or admission.get("generation_head_sha") != actual_candidate_head:\n        errors.append("MM06 scheduler admission generation head does not match independently supplied expected generation head")')
    replace("scripts/scheduler_admission_guard.py", '    observed_manifest_blob: str | None = None,\n    require_inactive_production_fence: bool = False,\n) -> list[str]:\n    """Validate the create-once main envelope; it is intentionally not the MM06 source bytes."""\n    errors = schema_errors(root, "schemas/scheduler_admission_copy.schema.json", admission)', '    observed_manifest_blob: str | None = None,\n    require_inactive_production_fence: bool = False,\n    expected_generation_head: str | None = None,\n) -> list[str]:\n    """Validate the create-once main envelope; it is intentionally not the MM06 source bytes."""\n    errors = schema_errors(root, "schemas/scheduler_admission_copy.schema.json", admission)\n    actual_candidate_head = expected_generation_head\n    if actual_candidate_head is None or admission.get("generation_head_sha") != actual_candidate_head:\n        errors.append("scheduler admission copy generation head does not match independently supplied expected generation head")')
    replace("scripts/scheduler_admission_guard.py", '            require_inactive_production_fence=require_inactive_production_fence,\n        ))', '            require_inactive_production_fence=require_inactive_production_fence,\n            expected_generation_head=expected_generation_head,\n        ))')
    replace("scripts/scheduler_admission_guard.py", '            errors.extend(validate_scheduler_admission(root, manifest, admission, staged=staged, source=source, observed_manifest_blob=git_blob_sha(path)))', '            errors.extend(validate_scheduler_admission(root, manifest, admission, staged=staged, source=source, observed_manifest_blob=git_blob_sha(path), expected_generation_head=staged.get("generation_head_sha") if staged else None))')
    replace("scripts/reconcile_open_prs.py", 'validate_scheduler_admission(root,manifest,admission,staged=pointer,source=source,observed_manifest_blob=manifest_blob.strip(),require_inactive_production_fence=True)', 'validate_scheduler_admission(root,manifest,admission,staged=pointer,source=source,observed_manifest_blob=manifest_blob.strip(),require_inactive_production_fence=True,expected_generation_head=pointer.get("generation_head_sha"))')
    replace("scripts/reconcile_open_prs.py", 'validate_scheduler_admission(root,manifest,admission,staged=archived,source=source,observed_manifest_blob=manifest_blob.strip(),require_inactive_production_fence=True)', 'validate_scheduler_admission(root,manifest,admission,staged=archived,source=source,observed_manifest_blob=manifest_blob.strip(),require_inactive_production_fence=True,expected_generation_head=archived.get("generation_head_sha"))')
    replace("scripts/reconcile_open_prs.py", 'validate_scheduler_admission(root,manifest,copy,staged=pointer,source=source,observed_manifest_blob=manifest_blob,require_inactive_production_fence=True)', 'validate_scheduler_admission(root,manifest,copy,staged=pointer,source=source,observed_manifest_blob=manifest_blob,require_inactive_production_fence=True,expected_generation_head=pointer.get("generation_head_sha"))')
    replace("tests/test_scheduler_admission_construction.py", '                observed_manifest_blob=observed,\n            )', '                observed_manifest_blob=observed,\n                expected_generation_head=source["generation_head_sha"],\n            )')
    replace("tests/test_scheduler_active_phase_validation.py", '                observed_manifest_blob=HEX,\n            )', '                observed_manifest_blob=HEX,\n                expected_generation_head=self.source["generation_head_sha"],\n            )')
    replace("tests/test_scheduler_active_phase_validation.py", '                observed_manifest_blob=HEX,\n                require_inactive_production_fence=True,\n            )', '                observed_manifest_blob=HEX,\n                require_inactive_production_fence=True,\n                expected_generation_head=self.source["generation_head_sha"],\n            )')
    replace("tests/test_scheduler_active_phase_validation.py", '        self.assertIn("_remote_inactive_production_snapshot(manifest,G)!=production_snapshot", source)\n', '        self.assertIn("_remote_inactive_production_snapshot(manifest,G)!=production_snapshot", source)\n        self.assertEqual(source.count("expected_generation_head="), 3)\n')
    replace("tests/test_scheduler_admission_negative.py", '    def test_schemas_are_closed_and_do_not_expose_raw_auth_fields(self):\n', '    def test_root_and_head_placeholder_or_non_sha_values_fail_schema(self):\n        for path, field in (("schemas/scheduler_manifest.schema.json", "generation_root_sha"), ("schemas/staged_candidate.schema.json", "generation_head_sha")):\n            schema=json.loads((ROOT/path).read_text())\n            validator=Draft202012Validator(schema["properties"][field])\n            for invalid in ("__PLACEHOLDER__", "not-a-git-sha", "0"*39):\n                with self.subTest(path=path, field=field, invalid=invalid):\n                    self.assertTrue(list(validator.iter_errors(invalid)))\n\n    def test_schemas_are_closed_and_do_not_expose_raw_auth_fields(self):\n')

    replace("config/countable_control_set_v25.json", '    "config/root_epoch11_stageability_repair_seed_v25.json",\n', '    "config/root_epoch11_stageability_repair_seed_v25.json",\n    "' + am_config + '",\n')
    replace("config/countable_control_set_v25.json", '    "scripts/reconcile_root_epoch11_stageability_repair_seed.py",\n', '    "scripts/reconcile_root_epoch11_stageability_repair_seed.py",\n    "' + am_script + '",\n')
    replace("config/countable_control_set_v25.json", '    "tests/test_root_epoch11_stageability_repair_seed.py",\n', '    "tests/test_root_epoch11_stageability_repair_seed.py",\n    "' + am_test + '",\n')
    replace("config/countable_control_set_v25.json", '    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",\n', '    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",\n    "' + am_workflow + '",\n')
    replace("config/admission_authority.json", '    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",\n', '    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",\n    "' + am_workflow + '",\n', 2)
    replace("config/admission_authority.json", '    "config/root_epoch11_stageability_repair_seed_v25.json",\n    "scripts/reconcile_root_epoch11_stageability_repair_seed.py",\n', '    "config/root_epoch11_stageability_repair_seed_v25.json",\n    "' + am_config + '",\n    "scripts/reconcile_root_epoch11_stageability_repair_seed.py",\n    "' + am_script + '",\n    "' + am_test + '",\n')
    replace("scripts/reconcile_authority_bootstrap.py", '    "config/root_epoch11_stageability_repair_seed_v25.json",\n    "scripts/reconcile_root_epoch11_stageability_repair_seed.py",\n    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",\n', '    "config/root_epoch11_stageability_repair_seed_v25.json",\n    "' + am_config + '",\n    "scripts/reconcile_root_epoch11_stageability_repair_seed.py",\n    "' + am_script + '",\n    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",\n    "' + am_workflow + '",\n    "' + am_test + '",\n')
    replace("scripts/reconcile_authority_bootstrap.py", '    "config/root_epoch11_stageability_repair_seed_v25.json","config/root_epoch11_stageability_repair_epoch_v25.json",\n', '    "config/root_epoch11_stageability_repair_seed_v25.json","' + am_config + '","config/root_epoch11_stageability_repair_epoch_v25.json",\n')
    replace("scripts/reconcile_authority_bootstrap.py", '    "scripts/reconcile_root_epoch11_stageability_repair_seed.py",\n    "schemas/scheduler_manifest.schema.json"', '    "scripts/reconcile_root_epoch11_stageability_repair_seed.py","' + am_script + '",\n    "schemas/scheduler_manifest.schema.json"')
    replace("scripts/reconcile_authority_bootstrap.py", '    "tests/test_root_epoch11_stageability_repair_seed.py","tests/test_root_epoch11_stageability_repair.py",\n', '    "tests/test_root_epoch11_stageability_repair_seed.py","' + am_test + '","tests/test_root_epoch11_stageability_repair.py",\n')
    replace("scripts/reconcile_authority_bootstrap.py", '    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",\n}', '    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml","' + am_workflow + '",\n}')
    replace("tests/test_bootstrap_root_tcb_and_head_binding.py", "'config/root_epoch11_stageability_repair_seed_v25.json','config/root_epoch11_stageability_repair_epoch_v25.json'", "'config/root_epoch11_stageability_repair_seed_v25.json','" + am_config + "','config/root_epoch11_stageability_repair_epoch_v25.json'", 2)
    replace("tests/test_bootstrap_root_tcb_and_head_binding.py", "'scripts/reconcile_root_epoch11_stageability_repair_seed.py'", "'scripts/reconcile_root_epoch11_stageability_repair_seed.py','" + am_script + "'", 2)
    replace("tests/test_bootstrap_root_tcb_and_head_binding.py", "'.github/workflows/supernova-root-epoch11-stageability-repair-seed.yml'", "'.github/workflows/supernova-root-epoch11-stageability-repair-seed.yml','" + am_workflow + "','" + am_test + "'", 2)
    needle = "  self.assertEqual(epoch['root_epoch11_stageability_repair_marker'],'config/root_epoch11_stageability_repair_epoch_v25.json')\n"
    replace("tests/test_bootstrap_root_tcb_and_head_binding.py", needle, needle + "  for key in ('root_epoch11_stageability_repair_seed_amendment_install_commit_sha','root_epoch11_stageability_repair_seed_amendment_policy_blob','root_epoch11_stageability_repair_seed_amendment_reconciler_blob','root_epoch11_stageability_repair_seed_amendment_workflow_blob'):\n   self.assertRegex(epoch[key],r'^[0-9a-f]{40}$')\n  authority_paths=set(admission['authoritative_status_workflows'])|set(admission['trusted_authority_helpers'])|set(admission['trusted_validator_entrypoints'])\n  for path in ('" + am_config + "','" + am_script + "','" + am_workflow + "','" + am_test + "'):\n   self.assertIn(path,authority_paths)\n")
    replace("tests/test_countable_control_freeze.py", '            "config/root_epoch11_stageability_repair_seed_v25.json",\n', '            "config/root_epoch11_stageability_repair_seed_v25.json",\n            "' + am_config + '",\n')
    replace("tests/test_countable_control_freeze.py", '            "scripts/reconcile_root_epoch11_stageability_repair_seed.py",\n', '            "scripts/reconcile_root_epoch11_stageability_repair_seed.py",\n            "' + am_script + '",\n')
    replace("tests/test_countable_control_freeze.py", '            ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",\n', '            ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",\n            "' + am_workflow + '",\n')
    replace("tests/test_countable_control_freeze.py", '            "tests/test_root_epoch10_scheduler_admission.py",\n', '            "' + am_test + '",\n            "tests/test_root_epoch10_scheduler_admission.py",\n')
    replace("tests/test_root_epoch6_repair.py", "'config/root_epoch11_stageability_repair_seed_v25.json','config/root_epoch11_stageability_repair_epoch_v25.json','scripts/reconcile_root_epoch11_stageability_repair_seed.py','.github/workflows/supernova-root-epoch11-stageability-repair-seed.yml'", "'config/root_epoch11_stageability_repair_seed_v25.json','" + am_config + "','config/root_epoch11_stageability_repair_epoch_v25.json','scripts/reconcile_root_epoch11_stageability_repair_seed.py','" + am_script + "','.github/workflows/supernova-root-epoch11-stageability-repair-seed.yml','" + am_workflow + "','" + am_test + "'")
    replace("tests/test_root_epoch9_integrity_repair.py", "            'config/root_epoch11_stageability_repair_seed_v25.json',\n            'config/root_epoch11_stageability_repair_epoch_v25.json',\n            'scripts/reconcile_root_epoch11_stageability_repair_seed.py',\n            '.github/workflows/supernova-root-epoch11-stageability-repair-seed.yml',\n", "            'config/root_epoch11_stageability_repair_seed_v25.json',\n            '" + am_config + "',\n            'config/root_epoch11_stageability_repair_epoch_v25.json',\n            'scripts/reconcile_root_epoch11_stageability_repair_seed.py',\n            '" + am_script + "',\n            '.github/workflows/supernova-root-epoch11-stageability-repair-seed.yml',\n            '" + am_workflow + "',\n            '" + am_test + "',\n")
    replace("tests/test_root_epoch11_stageability_repair.py", '        self.manifest = json.loads((ROOT / "schemas/scheduler_manifest.schema.json").read_text())\n', '        self.manifest = json.loads((ROOT / "schemas/scheduler_manifest.schema.json").read_text())\n        self.tcb = json.loads((ROOT / "config/root_tcb_epoch_v25.json").read_text())\n        self.authority = json.loads((ROOT / "config/admission_authority.json").read_text())\n')
    insert = '''    def test_seed_completeness_amendment_is_durable_root_authority(self):
        self.assertEqual(self.epoch["schema_version"], "PS-ROOT-EPOCH11-STAGEABILITY-REPAIR-EPOCH-2.5-1")
        for key in (
            "root_epoch11_stageability_repair_seed_amendment_install_commit_sha",
            "root_epoch11_stageability_repair_seed_amendment_policy_blob",
            "root_epoch11_stageability_repair_seed_amendment_reconciler_blob",
            "root_epoch11_stageability_repair_seed_amendment_workflow_blob",
        ):
            self.assertRegex(self.tcb[key], r"^[0-9a-f]{40}$")
        authority_paths = set(self.authority["authoritative_status_workflows"]) | set(self.authority["trusted_authority_helpers"]) | set(self.authority["trusted_validator_entrypoints"])
        for path in (
            "config/root_epoch11_stageability_repair_seed_amendment_v25.json",
            "scripts/reconcile_root_epoch11_stageability_repair_seed_amendment.py",
            ".github/workflows/supernova-root-epoch11-stageability-repair-seed-amendment.yml",
            "tests/test_root_epoch11_stageability_repair_seed_amendment.py",
        ):
            self.assertIn(path, authority_paths)

'''
    replace("tests/test_root_epoch11_stageability_repair.py", '    def test_epoch_declares_constructable_one_commit_four_path_dag(self):\n', insert + '    def test_epoch_declares_constructable_one_commit_four_path_dag(self):\n')
    seed_line = '  "root_epoch11_stageability_repair_seed_workflow_blob": "9fe418006115166a68c3a029e9c9387de5bdc194",\n'
    replace("config/root_tcb_epoch_v25.json", seed_line, seed_line + '  "root_epoch11_stageability_repair_seed_amendment_install_commit_sha": "__ROOT11_SEED_AMENDMENT_INSTALL_COMMIT__",\n  "root_epoch11_stageability_repair_seed_amendment_policy_blob": "__ROOT11_SEED_AMENDMENT_POLICY_BLOB__",\n  "root_epoch11_stageability_repair_seed_amendment_reconciler_blob": "__ROOT11_SEED_AMENDMENT_RECONCILER_BLOB__",\n  "root_epoch11_stageability_repair_seed_amendment_workflow_blob": "__ROOT11_SEED_AMENDMENT_WORKFLOW_BLOB__",\n')
    replace("config/root_tcb_epoch_v25.json", 'PLUS_EPOCH6_THROUGH_EPOCH11_INDEPENDENT_ONE_SHOT_SEEDS"', 'PLUS_EPOCH6_THROUGH_EPOCH11_INDEPENDENT_ONE_SHOT_SEEDS_PLUS_ROOT11_SEED_COMPLETENESS_AMENDMENT"')
    return changed


class RootEpoch11StageabilityRepairSeedAmendmentTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.original_policy = json.loads(ORIGINAL_POLICY.read_text(encoding="utf-8"))
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.module = load_amendment_module()

    def test_amendment_is_exact_four_path_one_shot_non_authorizing_correction(self):
        p = self.policy
        self.assertEqual(p["schema_version"], "PS-ROOT-EPOCH11-STAGEABILITY-REPAIR-SEED-AMENDMENT-2.5-1")
        self.assertEqual(p["required_amendment_base_main_sha"], "49748265ab8afff2f53b4fa306c2b96d9d7e798c")
        self.assertEqual(p["original_seed_install_commit_sha"], p["required_amendment_base_main_sha"])
        self.assertEqual(p["reviewed_candidate_source_commit_sha"], "023cc2a543105c1a84a09d90fe681c08b343a024")
        self.assertEqual(len(p["original_seed_paths"]), 4)
        self.assertEqual(len(p["amendment_paths"]), 4)
        self.assertEqual(p["seed_context"], "supernova/root-epoch11-stageability-repair-seed-amendment")
        self.assertEqual(p["candidate_path_count"], 69)
        self.assertEqual(len(p["expected_root_candidate_blobs"]), 68)
        self.assertEqual(p["expected_root_candidate_blobs"]["config/root_epoch11_stageability_repair_epoch_v25.json"], "d84984c12501c395614a812449f2d041a5649811")
        self.assertEqual(p["expected_root_candidate_blobs"]["config/admission_authority.json"], "420f94bdc66583cbf5f83147e7276fc926662d64")
        self.assertEqual(p["expected_root_candidate_blobs"]["scripts/reconcile_authority_bootstrap.py"], "e37ba1828a7ced4024378d76b413a1c78e274075")
        self.assertTrue(set(p["original_seed_paths"]).isdisjoint(p["amendment_paths"]))
        self.assertEqual(p["required_current_root_epoch"], 10)
        self.assertEqual(p["state_effect"], "NONE")
        self.assertEqual(p["runtime_effect"], "NONE")
        self.assertEqual(p["science_effect"], "NONE")
        self.assertTrue(p["implementation_authorization"].startswith("NOT_GRANTED"))
        self.assertIn("ALL_FOUR_AMENDMENT_PATHS", p["durable_provenance_rule"])
        self.assertEqual(p["failure_semantics"], "FAIL_CLOSED")
        self.assertTrue(p["candidate_bytes_in_privileged_phase"].startswith("DATA_ONLY"))
        for blob in p["original_seed_paths"].values():
            self.assertRegex(blob, r"^[0-9a-f]{40}$")

    def test_real_69_path_surface_has_an_explicit_executable_68_blob_map(self):
        p = self.policy
        required = set(self.original_policy["required_root_candidate_paths"])
        pins = p["expected_root_candidate_blobs"]
        self.assertEqual(len(required), p["candidate_path_count"])
        self.assertEqual(set(pins), required - {"config/root_tcb_epoch_v25.json"})
        seed = types.SimpleNamespace(
            ROOT_TCB_PATH="config/root_tcb_epoch_v25.json",
            HEX40=re.compile(r"^[0-9a-f]{40}$"),
            blob_at=lambda ref, path, cwd=None: pins.get(path),
        )
        self.assertEqual(
            self.module.exact_amended_nonroot_candidate(pathlib.Path("."), p, seed, self.original_policy),
            (True, ""),
        )
        self.assertEqual(pins["schemas/assignment.schema.json"], "1591e10c6f8fda0708749c93d28ae71cc5bb55d2")
        self.assertEqual(pins["schemas/cohort_liveness_contract.schema.json"], "3de70277daf7842e492e9c53a3e1140a19685123")
        self.assertEqual(pins["scripts/scheduler_admission_guard.py"], "6e43bcc73e32a85624762384c4e9738381b92cee")
        self.assertEqual(pins["scripts/transition_guard.py"], "ff363239712fd8250368db064a08d9c04c56ea23")
        deliberate = {
            "config/admission_authority.json",
            "config/countable_control_set_v25.json",
            "config/root_epoch11_stageability_repair_epoch_v25.json",
            "schemas/assignment.schema.json",
            "schemas/cohort_liveness_contract.schema.json",
            "scripts/reconcile_authority_bootstrap.py",
            "scripts/reconcile_open_prs.py",
            "scripts/scheduler_admission_guard.py",
            "scripts/transition_guard.py",
            "tests/test_bootstrap_root_tcb_and_head_binding.py",
            "tests/test_countable_control_freeze.py",
            "tests/test_root_epoch11_stageability_repair.py",
            "tests/test_root_epoch6_repair.py",
            "tests/test_root_epoch9_integrity_repair.py",
            "tests/test_scheduler_active_phase_validation.py",
            "tests/test_scheduler_admission_construction.py",
            "tests/test_scheduler_admission_negative.py",
        }
        original_pins = self.original_policy["expected_root_candidate_blobs"]
        self.assertEqual({path for path in pins if pins[path] != original_pins[path]}, deliberate)
        self.assertEqual(len(deliberate), 17)

    def test_real_reviewed_lf_candidate_transforms_to_exact_pins_and_zero_amended_errors(self):
        source = self.policy["reviewed_candidate_source_commit_sha"]
        current_pins = {}
        for path in self.policy["expected_root_candidate_blobs"]:
            result = subprocess.run(["git", "rev-parse", "HEAD:" + path], cwd=ROOT, capture_output=True, text=True)
            if result.returncode:
                break
            current_pins[path] = result.stdout.strip()
        if current_pins == self.policy["expected_root_candidate_blobs"]:
            seed_spec = importlib.util.spec_from_file_location(
                "root11_seed_live_candidate_fixture",
                ROOT / "scripts/reconcile_root_epoch11_stageability_repair_seed.py",
            )
            seed = importlib.util.module_from_spec(seed_spec)
            assert seed_spec.loader is not None
            seed_spec.loader.exec_module(seed)
            conflicts = seed.candidate_semantics(
                ROOT,
                self.policy["original_seed_install_commit_sha"],
                self.original_policy,
            )
            self.assertEqual(collections.Counter(conflicts), collections.Counter(self.policy["expected_frozen_semantic_conflicts"]))
            self.assertEqual(self.module.exact_amended_nonroot_candidate(ROOT, self.policy, seed, self.original_policy), (True, ""))
            self.assertEqual(self.module.corrected_candidate_semantics(ROOT, self.policy, seed, self.original_policy), (True, ""))
            return
        source_repo = ROOT
        candidates = (ROOT, ROOT.parent / "Project-supernova-root11-repair")
        source_tree = None
        for repo in candidates:
            probe = subprocess.run(["git", "cat-file", "-e", source + "^{commit}"], cwd=repo, capture_output=True, text=True)
            if probe.returncode == 0:
                source_repo = repo
                break
        else:
            sibling = ROOT.parent / "Project-supernova-root11-repair"
            if sibling.is_dir() and (sibling / "config/root_epoch11_stageability_repair_epoch_v25.json").is_file():
                source_tree = sibling
            elif os.environ.get("SUPERNOVA_REQUIRE_REAL_ROOT11_FIXTURE") == "1":
                self.fail("reviewed candidate commit must be present for the mandatory real integration fixture")
            else:
                self.skipTest("reviewed candidate commit is not present in this non-candidate checkout")
        with tempfile.TemporaryDirectory(prefix="root11-amendment-real-") as td:
            candidate = pathlib.Path(td) / "candidate"
            worktree_added = source_tree is None
            if source_tree is None:
                added = subprocess.run(["git", "worktree", "add", "--detach", str(candidate), source], cwd=source_repo, capture_output=True, text=True)
                self.assertEqual(added.returncode, 0, added.stderr)
            else:
                shutil.copytree(source_tree, candidate, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            try:
                changed = apply_reviewed_candidate_transformations(candidate)
                expected_changed = {
                    path for path, blob in self.policy["expected_root_candidate_blobs"].items()
                    if blob != self.original_policy["expected_root_candidate_blobs"][path]
                } | {"config/root_tcb_epoch_v25.json"}
                self.assertEqual(changed, expected_changed)

                seed_spec = importlib.util.spec_from_file_location(
                    "root11_seed_real_fixture",
                    ROOT / "scripts/reconcile_root_epoch11_stageability_repair_seed.py",
                )
                seed = importlib.util.module_from_spec(seed_spec)
                assert seed_spec.loader is not None
                seed_spec.loader.exec_module(seed)
                original_blob_at = seed.blob_at

                def canonical_fixture_blob(ref, path, cwd=seed.ROOT):
                    if pathlib.Path(cwd).resolve() == candidate.resolve():
                        if path in changed:
                            data = (candidate / path).read_bytes()
                            return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                        if source_tree is not None:
                            return self.original_policy["expected_root_candidate_blobs"].get(path)
                        result = subprocess.run(
                            ["git", "rev-parse", source + ":" + path],
                            cwd=source_repo,
                            capture_output=True,
                            text=True,
                        )
                        return result.stdout.strip() if result.returncode == 0 else None
                    if path in self.policy["original_seed_paths"]:
                        return self.policy["original_seed_paths"][path]
                    return original_blob_at(ref, path, cwd=cwd)

                with mock.patch.object(seed, "blob_at", side_effect=canonical_fixture_blob):
                    conflicts = seed.candidate_semantics(
                        candidate,
                        self.policy["original_seed_install_commit_sha"],
                        self.original_policy,
                    )
                    self.assertEqual(
                        collections.Counter(conflicts),
                        collections.Counter(self.policy["expected_frozen_semantic_conflicts"]),
                    )
                    self.assertEqual(
                        self.module.exact_amended_nonroot_candidate(candidate, self.policy, seed, self.original_policy),
                        (True, ""),
                    )
                    self.assertEqual(
                        self.module.corrected_candidate_semantics(candidate, self.policy, seed, self.original_policy),
                        (True, ""),
                    )
            finally:
                if worktree_added:
                    subprocess.run(["git", "worktree", "remove", "--force", str(candidate)], cwd=source_repo, capture_output=True, text=True)

    def test_known_defect_is_the_exact_observed_internal_schema_contradiction(self):
        defect = self.policy["known_defect"]
        self.assertEqual(defect["failure"], "root11 marker mismatch schema_version")
        self.assertEqual(defect["original_inconsistent_marker_blob"], "f099ceab51226681d51a9f5e954090fe4fc62ea6")
        self.assertEqual(defect["corrected_marker_blob"], "d84984c12501c395614a812449f2d041a5649811")
        self.assertEqual(
            defect["corrected_marker_blob"],
            self.policy["expected_root_candidate_blobs"][defect["marker_path"]],
        )
        self.assertEqual(defect["original_pinned_marker_schema_version"], "PS-ROOT-EPOCH11-STAGEABILITY-REPAIR-2.5-1")
        self.assertEqual(defect["corrected_marker_schema_version"], "PS-ROOT-EPOCH11-STAGEABILITY-REPAIR-EPOCH-2.5-1")
        original = (ROOT / "scripts" / "reconcile_root_epoch11_stageability_repair_seed.py").read_text(encoding="utf-8")
        self.assertIn(defect["corrected_marker_schema_version"], original)
        self.assertEqual(set(self.policy["root_tcb_dynamic_amendment_bindings"]), {
            "root_epoch11_stageability_repair_seed_amendment_install_commit_sha",
            "root_epoch11_stageability_repair_seed_amendment_policy_blob",
            "root_epoch11_stageability_repair_seed_amendment_reconciler_blob",
            "root_epoch11_stageability_repair_seed_amendment_workflow_blob",
        })
        self.assertRegex(self.policy["expected_normalized_root_tcb_sha256"], r"^[0-9a-f]{64}$")

    def _fake_seed(self, problems, marker_schema=None, marker_blob=None, missing_durable_path=None):
        defect = self.policy["known_defect"]
        marker = {"schema_version": marker_schema or defect["corrected_marker_schema_version"]}
        durable_paths = set(self.policy["amendment_paths"])
        if missing_durable_path:
            durable_paths.remove(missing_durable_path)
        bootstrap = "\n".join(repr(path) for path in durable_paths for _ in range(2))
        documents = {
            defect["marker_path"]: marker,
            "config/countable_control_set_v25.json": {"required_control_paths": sorted(durable_paths)},
            "config/admission_authority.json": {
                "trusted_validator_entrypoints": [],
                "authoritative_status_workflows": [],
                "trusted_authority_helpers": sorted(durable_paths),
            },
        }
        return types.SimpleNamespace(
            candidate_semantics=lambda tmp, trusted, policy: list(problems),
            blob_at=lambda ref, path, cwd=None: marker_blob or defect["corrected_marker_blob"],
            load=lambda root, path: json.loads(json.dumps(documents[path])),
            bootstrap_text=bootstrap,
        )

    def test_corrected_semantics_requires_exact_reviewed_conflict_multiset_and_exact_marker(self):
        seed = self._fake_seed(self.policy["expected_frozen_semantic_conflicts"])
        with mock.patch.object(pathlib.Path, "read_text", return_value=seed.bootstrap_text), \
             mock.patch.object(self.module, "stronger_rederived_contract_errors", return_value=[]), \
             mock.patch.object(self.module, "root11_schema_condition_errors", return_value=[]):
            ok, reason = self.module.corrected_candidate_semantics(pathlib.Path("."), self.policy, seed, {})
            self.assertTrue(ok, reason)

    def test_corrected_semantics_rejects_old_mismatch_any_other_failure_and_marker_drift(self):
        defect = self.policy["known_defect"]
        cases = (
            self._fake_seed(self.policy["expected_frozen_semantic_conflicts"] + [defect["failure"]]),
            self._fake_seed(["another failure"]),
            self._fake_seed(self.policy["expected_frozen_semantic_conflicts"], marker_blob="0" * 40),
            self._fake_seed(self.policy["expected_frozen_semantic_conflicts"], marker_schema="PS-WEAKENED"),
        )
        for seed in cases:
            with self.subTest(seed=seed):
                with mock.patch.object(pathlib.Path, "read_text", return_value=seed.bootstrap_text), \
                     mock.patch.object(self.module, "stronger_rederived_contract_errors", return_value=[]), \
                     mock.patch.object(self.module, "root11_schema_condition_errors", return_value=[]):
                    self.assertFalse(self.module.corrected_candidate_semantics(pathlib.Path("."), self.policy, seed, {})[0])

    def test_corrected_semantics_rejects_any_unrooted_amendment_path(self):
        seed = self._fake_seed(self.policy["expected_frozen_semantic_conflicts"], missing_durable_path=self.policy["amendment_paths"][3])
        with mock.patch.object(pathlib.Path, "read_text", return_value=seed.bootstrap_text), \
             mock.patch.object(self.module, "stronger_rederived_contract_errors", return_value=[]), \
             mock.patch.object(self.module, "root11_schema_condition_errors", return_value=[]):
            ok, reason = self.module.corrected_candidate_semantics(pathlib.Path("."), self.policy, seed, {})
        self.assertFalse(ok)
        self.assertIn("all four amendment paths", reason)

    def test_exact_candidate_preserves_first_seed_and_normalizes_only_amendment_bindings(self):
        p = json.loads(json.dumps(self.policy))
        original = self.original_policy
        root_tcb = {
            "epoch": 11,
            "root_epoch11_stageability_repair_seed_install_commit_sha": p["original_seed_install_commit_sha"],
            "root_epoch11_stageability_repair_seed_policy_blob": p["original_seed_paths"]["config/root_epoch11_stageability_repair_seed_v25.json"],
            "root_epoch11_stageability_repair_seed_reconciler_blob": p["original_seed_paths"]["scripts/reconcile_root_epoch11_stageability_repair_seed.py"],
            "root_epoch11_stageability_repair_seed_workflow_blob": p["original_seed_paths"][".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml"],
        }
        amendment_blobs = ["2" * 40, "3" * 40, "4" * 40]
        trusted = "5" * 40
        actual_dynamic = {
            "root_epoch11_stageability_repair_seed_amendment_install_commit_sha": trusted,
            "root_epoch11_stageability_repair_seed_amendment_policy_blob": amendment_blobs[0],
            "root_epoch11_stageability_repair_seed_amendment_reconciler_blob": amendment_blobs[1],
            "root_epoch11_stageability_repair_seed_amendment_workflow_blob": amendment_blobs[2],
        }
        root_tcb.update(actual_dynamic)
        normalized = dict(root_tcb)
        normalized.update(p["root_tcb_dynamic_amendment_bindings"])
        canonical = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()
        p["expected_normalized_root_tcb_sha256"] = canonical(normalized)
        blobs = {
            **p["expected_root_candidate_blobs"],
            p["amendment_paths"][0]: amendment_blobs[0],
            p["amendment_paths"][1]: amendment_blobs[1],
            p["amendment_paths"][2]: amendment_blobs[2],
        }
        seed = types.SimpleNamespace(
            ROOT_TCB_PATH="config/root_tcb_epoch_v25.json",
            HEX40=re.compile(r"^[0-9a-f]{40}$"),
            blob_at=lambda ref, path, cwd=None: blobs.get(path),
            load=lambda root, path: dict(root_tcb),
            canonical_sha256=canonical,
        )
        self.assertEqual(self.module.exact_amended_candidate(pathlib.Path("."), trusted, p, seed, original), (True, ""))
        drifted = dict(root_tcb)
        drifted["root_epoch11_stageability_repair_seed_install_commit_sha"] = "6" * 40
        seed.load = lambda root, path: dict(drifted)
        self.assertFalse(self.module.exact_amended_candidate(pathlib.Path("."), trusted, p, seed, original)[0])
        placeholder = dict(root_tcb)
        placeholder["root_epoch11_stageability_repair_seed_amendment_install_commit_sha"] = "__PLACEHOLDER__"
        seed.load = lambda root, path: dict(placeholder)
        self.assertFalse(self.module.exact_amended_candidate(pathlib.Path("."), trusted, p, seed, original)[0])

    def test_bound_result_posts_amendment_context_and_existing_three_while_decline_is_no_write(self):
        posts = []
        seed = types.SimpleNamespace(
            HEX40=re.compile(r"^[0-9a-f]{40}$"),
            post=lambda sha, context, state, description: posts.append((sha, context, state)),
        )
        sha = "a" * 40
        self.assertEqual(self.module.fail_bound(seed, sha, "known bound failure", self.policy), 1)
        self.assertEqual([row[1] for row in posts], [self.policy["seed_context"], *self.policy["required_status_contexts"]])
        self.assertTrue(all(row[2] == "failure" for row in posts))
        posts.clear()
        self.assertEqual(self.module.decline("stale head"), 1)
        self.assertEqual(posts, [])

    def _source_fixture(self):
        trusted = "a" * 40
        head = "b" * 40
        pr = {
            "number": 235,
            "head": {"sha": head, "ref": "root-rotation/epoch11-stageability-repair-v25"},
            "base": {"sha": trusted},
        }
        source = self.policy["source_workflow"]
        run = {
            "name": source["name"],
            "path": source["path"],
            "event": source["event"],
            "status": source["status"],
            "conclusion": source["conclusion"],
            "run_attempt": 2,
            "head_sha": head,
            "head_branch": pr["head"]["ref"],
            "pull_requests": [{"number": 235, "head": {"sha": head}, "base": {"sha": trusted}}],
        }
        jobs = {"jobs": [
            {"name": source["candidate_job"], "conclusion": source["candidate_job_conclusion"]},
            {"name": source["trusted_job"], "conclusion": source["trusted_job_conclusion"]},
        ]}
        return run, jobs, pr, trusted

    def test_source_run_binding_accepts_exact_completed_predecessor(self):
        run, jobs, pr, trusted = self._source_fixture()
        self.assertEqual(self.module.source_run_binding_errors(run, jobs, pr, trusted, self.policy, 2), [])

    def test_source_run_binding_matches_pull_request_target_rest_shape(self):
        run, jobs, pr, trusted = self._source_fixture()
        self.assertEqual(run["event"], "pull_request_target")
        self.assertEqual(run["head_sha"], pr["head"]["sha"])
        self.assertEqual(run["head_branch"], pr["head"]["ref"])
        self.assertEqual(run["pull_requests"][0]["base"]["sha"], trusted)
        self.assertEqual(pr["base"]["sha"], trusted)
        self.assertEqual(self.module.source_run_binding_errors(run, jobs, pr, trusted, self.policy, 2), [])

    def test_source_run_binding_rejects_stale_head_base_and_unproven_diagnostics(self):
        run, jobs, pr, trusted = self._source_fixture()
        run["pull_requests"][0]["head"]["sha"] = "c" * 40
        self.assertTrue(self.module.source_run_binding_errors(run, jobs, pr, trusted, self.policy, 2))
        run, jobs, pr, trusted = self._source_fixture()
        pr["base"]["sha"] = "c" * 40
        self.assertTrue(self.module.source_run_binding_errors(run, jobs, pr, trusted, self.policy, 2))
        run, jobs, pr, trusted = self._source_fixture()
        jobs["jobs"][0]["conclusion"] = "failure"
        self.assertTrue(self.module.source_run_binding_errors(run, jobs, pr, trusted, self.policy, 2))
        run, jobs, pr, trusted = self._source_fixture()
        run["head_sha"] = trusted
        self.assertTrue(self.module.source_run_binding_errors(run, jobs, pr, trusted, self.policy, 2))
        run, jobs, pr, trusted = self._source_fixture()
        run["head_branch"] = "main"
        self.assertTrue(self.module.source_run_binding_errors(run, jobs, pr, trusted, self.policy, 2))
        run, jobs, pr, trusted = self._source_fixture()
        run["run_attempt"] = 3
        self.assertTrue(self.module.source_run_binding_errors(run, jobs, pr, trusted, self.policy, 2))

    def test_attempt_specific_jobs_and_final_fence_refetch_run_and_jobs(self):
        calls = []
        seed = types.SimpleNamespace(api=lambda path: calls.append(path) or {"jobs": []})
        self.module.source_attempt_jobs(seed, 123, 4, self.policy)
        self.assertEqual(calls, ["/actions/runs/123/attempts/4/jobs?per_page=100"])
        self.assertGreaterEqual(self.script.count('seed.api(f"/actions/runs/{source_run_id}")'), 2)
        self.assertIn("final_jobs = source_attempt_jobs(seed, source_run_id, source_attempt, policy)", self.script)
        self.assertIn("source_run_binding_errors(final_source, final_jobs, final_pr, trusted, policy, source_attempt)", self.script)
        self.assertLess(self.script.index("wait_for_earlier_same_head_runs(seed, sha, amendment_run_id)"), self.script.index('final_source = seed.api(f"/actions/runs/{source_run_id}")'))
        self.assertLess(self.script.index("final_jobs = source_attempt_jobs"), self.script.index("source_run_binding_errors(final_source, final_jobs"))
        self.assertLess(self.script.index("source_run_binding_errors(final_source, final_jobs"), self.script.index('seed.post(sha, context, "success"'))

    def test_event_order_waits_for_every_earlier_same_head_run_and_rerun_rechecks(self):
        head = "b" * 40
        cutoff = "2026-08-23T12:00:00Z"
        rows = [
            {"id": 10, "event": "pull_request_target", "created_at": "2026-08-23T11:58:00Z", "status": "in_progress", "pull_requests": [{"head": {"sha": head}}]},
            {"id": 11, "event": "pull_request_target", "created_at": "2026-08-23T11:59:00Z", "status": "completed", "pull_requests": [{"head": {"sha": head}}]},
            {"id": 12, "event": "pull_request_target", "created_at": "2026-08-23T12:01:00Z", "status": "in_progress", "pull_requests": [{"head": {"sha": head}}]},
            {"id": 13, "event": "pull_request_target", "created_at": "2026-08-23T11:57:00Z", "status": "in_progress", "pull_requests": [{"head": {"sha": "c" * 40}}]},
        ]
        self.assertEqual(self.module.incomplete_earlier_same_head_runs(rows, head, cutoff), [10])
        rows[0]["status"] = "completed"
        self.assertEqual(self.module.incomplete_earlier_same_head_runs(rows, head, cutoff), [])

    def test_workflow_runs_only_after_original_fail_closed_and_never_executes_candidate_with_write_token(self):
        candidate, trusted = self.workflow.split("  trusted-seed-amendment:", 1)
        self.assertIn("workflow_run:", self.workflow)
        self.assertIn('workflows: ["Supernova Root Epoch11 Stageability Repair Seed"]', self.workflow)
        self.assertNotIn("pull_request_target:", self.workflow)
        self.assertNotIn("workflow_dispatch:", self.workflow)
        self.assertIn("types: [completed]", self.workflow)
        self.assertIn("pull_requests[0].number", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)
        self.assertNotIn("statuses: write", candidate)
        self.assertIn("persist-credentials: false", candidate)
        self.assertIn('GITHUB_TOKEN: ""', candidate)
        self.assertIn("needs: candidate-diagnostics", trusted)
        self.assertIn("if: always()", trusted)
        self.assertIn("actions: read", trusted)
        self.assertIn("statuses: write", trusted)
        self.assertIn("SOURCE_WORKFLOW_RUN_ID", trusted)
        self.assertIn("SOURCE_WORKFLOW_RUN_ATTEMPT", trusted)
        self.assertIn("github.event.workflow_run.run_attempt", candidate)
        self.assertIn("exact_amended_candidate", self.script)
        self.assertIn("corrected_candidate_semantics", self.script)
        self.assertIn("candidate does not descend from exact amendment install head", self.script)
        self.assertIn("wait_for_earlier_same_head_runs", self.script)
        self.assertIn("final_main", self.script)
        self.assertIn('[policy["seed_context"], *policy["required_status_contexts"]]', self.script)
        self.assertIn("return decline(source_errors[0])", self.script)
        self.assertIn('return fail_bound(seed, sha, "read-only candidate diagnostics did not succeed", policy)', self.script)
        self.assertLess(
            self.script.index("source_errors = source_run_binding_errors"),
            self.script.index('if diagnostics_result != "success"'),
        )

    def test_privileged_reconciler_never_executes_candidate_code(self):
        tree = ast.parse(self.script)
        trusted_runs = []
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            if not isinstance(call.func, ast.Attribute) or call.func.attr != "run":
                continue
            self.assertTrue(call.args, "trusted seed.run call must expose a literal command")
            command = call.args[0]
            self.assertIsInstance(command, ast.List, "dynamic subprocess command forbidden in privileged reconciler")
            self.assertTrue(command.elts)
            executable = command.elts[0]
            self.assertIsInstance(executable, ast.Constant)
            self.assertEqual(executable.value, "git", "only trusted Git data inspection is permitted")
            trusted_runs.append(call)
        self.assertGreater(len(trusted_runs), 0)
        for forbidden in (
            "scripts/validate_bus.py",
            "test_scheduler_admission_construction",
            '"unittest"',
            "candidate diagnostics failed:",
        ):
            self.assertNotIn(forbidden, self.script)
        candidate, trusted = self.workflow.split("  trusted-seed-amendment:", 1)
        self.assertIn("python scripts/validate_bus.py", candidate)
        self.assertIn("python -m unittest discover", candidate)
        self.assertNotIn("scripts/validate_bus.py", trusted)
        self.assertNotIn("unittest", trusted)


if __name__ == "__main__":
    unittest.main()
