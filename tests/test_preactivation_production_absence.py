"""P1: preactivation receipts cannot self-attest that production stayed at G."""

import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch


try:
    import jsonschema  # noqa: F401
except ModuleNotFoundError:
    jsonschema = types.ModuleType("jsonschema")

    class Draft202012Validator:
        def __init__(self, *args, **kwargs): pass
        @classmethod
        def check_schema(cls, *args, **kwargs): return None
        def iter_errors(self, *args, **kwargs): return []
    class FormatChecker: pass
    jsonschema.Draft202012Validator = Draft202012Validator
    jsonschema.FormatChecker = FormatChecker
    sys.modules["jsonschema"] = jsonschema


ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("production_absence_guard", ROOT / "scripts/scheduler_admission_guard.py")
GUARD = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(GUARD)

COHORT = "CAL-P1"
GENERATION = "a" * 40
MOVED = "b" * 40


def manifest():
    tasks = []
    for role in GUARD.ROLES:
        if role in GUARD.WORKERS:
            branch = f"ps/work/{COHORT}/{role}"
        elif role == "MM06":
            branch = f"ps/verify/{COHORT}"
        elif role == "MF06":
            branch = f"ps/integrate/{COHORT}"
        else:
            branch = f"ps/consolidate/{COHORT}"
        tasks.append({"role_id": role, "production_branch": branch})
    return {"cohort_id": COHORT, "generation_head_sha": GENERATION, "tasks": tasks}


def expected_refs():
    return {row["production_branch"] for row in manifest()["tasks"]} | {
        f"ps/verify/{COHORT}", f"ps/integrate/{COHORT}", f"ps/consolidate/{COHORT}",
    }


class PreactivationProductionAbsenceTests(unittest.TestCase):
    def fence(self, heads, callback=lambda: []):
        def fake_git(root, *args):
            ref = args[-1]
            prefix = "refs/remotes/origin/"
            if not ref.startswith(prefix):
                raise AssertionError(args)
            branch = ref[len(prefix):]
            return 0, heads[branch]
        with patch.object(GUARD, "_git", side_effect=fake_git):
            return GUARD.validate_production_ref_fence(pathlib.Path("/trusted"), manifest(), GENERATION, callback)

    def test_all_worker_verifier_integrator_and_consolidation_refs_must_equal_g(self):
        heads = {branch: GENERATION for branch in expected_refs()}
        self.assertEqual(self.fence(heads), [])

    def test_any_independent_production_ref_not_at_g_rejects_even_when_receipt_claims_absence(self):
        heads = {branch: GENERATION for branch in expected_refs()}
        moved_branch = f"ps/work/{COHORT}/MF01"
        heads[moved_branch] = MOVED
        errors = self.fence(heads)
        self.assertIn(f"production ref is not generation head: {moved_branch}", errors)

    def test_movement_between_pre_and_post_reads_rejects_admission(self):
        heads = {branch: GENERATION for branch in expected_refs()}
        moved_branch = f"ps/integrate/{COHORT}"

        def mutate_after_source_validation():
            heads[moved_branch] = MOVED
            return []

        errors = self.fence(heads, mutate_after_source_validation)
        self.assertIn(f"production ref moved during preactivation admission: {moved_branch}", errors)

    def test_mm06_validation_uses_the_fence_around_source_rederivation(self):
        text = (ROOT / "scripts/scheduler_admission_guard.py").read_text(encoding="utf-8")
        start = text.index("def validate_mm06_scheduler_admission")
        end = text.index("def validate_scheduler_admission", start)
        section = text[start:end]
        self.assertIn("validate_production_ref_fence(", section)
        self.assertIn("validate_preactivation_sources", section)


if __name__ == "__main__":
    unittest.main()
