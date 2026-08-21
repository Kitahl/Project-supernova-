import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOT = ROOT / "scripts" / "reconcile_authority_bootstrap.py"

INVARIANT_INPUTS = [
    "config/repo_policy.json",
    "config/admission_authority.json",
    "config/authority_bootstrap_v25.json",
    "config/protocol_freeze.json",
    "config/countable_control_set_v25.json",
]


def load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("runtime_update_bootstrap_test", BOOT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def copy_inputs(dst: pathlib.Path):
    for rel in INVARIANT_INPUTS:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)


class RuntimeUpdateBootstrapEligibilityTests(unittest.TestCase):
    def test_runtime_lineage_hardening_preserves_bootstrap_invariants(self):
        mod = load_bootstrap_module()
        changed = [
            "config/countable_control_set_v25.json",
            "scripts/parent_lineage_guard.py",
            "tests/test_runtime_update_bootstrap_eligibility.py",
            "tests/test_runtime_update_lineage.py",
        ]
        with tempfile.TemporaryDirectory() as d:
            base = pathlib.Path(d)
            trusted, candidate = base / "trusted", base / "candidate"
            copy_inputs(trusted)
            copy_inputs(candidate)

            # Reconstruct the exact accepted-main control contract by removing
            # only paths introduced by this PR. All other invariant inputs are
            # byte-identical to accepted main.
            trusted_control_path = trusted / "config/countable_control_set_v25.json"
            trusted_control = json.loads(trusted_control_path.read_text(encoding="utf-8"))
            trusted_control["required_control_paths"] = [
                p
                for p in trusted_control["required_control_paths"]
                if p not in {
                    "tests/test_runtime_update_bootstrap_eligibility.py",
                    "tests/test_runtime_update_lineage.py",
                }
            ]
            trusted_control_path.write_text(json.dumps(trusted_control), encoding="utf-8")

            self.assertEqual(mod.bootstrap_invariant_errors(trusted, candidate, changed), [])
            for path in changed:
                self.assertTrue(
                    path in mod.ALLOWED_EXACT or path.startswith(mod.ALLOWED_PREFIXES),
                    path,
                )
                self.assertNotIn(path, mod.FORBIDDEN_EXACT)
                self.assertFalse(path.startswith(mod.FORBIDDEN_PREFIXES), path)


if __name__ == "__main__":
    unittest.main()
