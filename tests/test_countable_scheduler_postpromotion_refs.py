"""P1 regression: active countable validation must not reapply the preactivation G fence."""

import importlib.util
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


try:
    import jsonschema  # noqa: F401
except ModuleNotFoundError:
    jsonschema = types.ModuleType("jsonschema")

    class Draft202012Validator:
        def __init__(self, *args, **kwargs):
            pass

        @classmethod
        def check_schema(cls, *args, **kwargs):
            return None

        def iter_errors(self, *args, **kwargs):
            return []

    class FormatChecker:
        pass

    jsonschema.Draft202012Validator = Draft202012Validator
    jsonschema.FormatChecker = FormatChecker
    sys.modules["jsonschema"] = jsonschema


ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "postpromotion_scheduler_guard", ROOT / "scripts/scheduler_admission_guard.py"
)
GUARD = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(GUARD)

COHORT = "CAL-P1-PROMOTED"


def write_json(root: pathlib.Path, relative: str, value: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class CountableSchedulerPostpromotionRefTests(unittest.TestCase):
    def test_active_root11_countable_validation_allows_legitimate_postpromotion_ref_advance(self):
        """The G fence is a preactivation/create transaction, never an active-health check."""
        control = {
            "cohort_id": COHORT,
            "candidate_nonce": "root11-postpromotion-nonce",
            "generation_root_sha": "a" * 40,
            "scheduler_admission_required": True,
            "scheduler_manifest_path": f"scheduler/{COHORT}.json",
        }
        # These heads represent real production work after a successful promotion.
        advanced_production_heads = {"ps/work/CAL-P1-PROMOTED/MF01": "b" * 40}

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            write_json(root, f"scheduler/{COHORT}.json", {})
            write_json(root, f"scheduler_admission/{COHORT}.json", {})
            write_json(root, "state/CURRENT.json", {
                "active_cohort_id": COHORT,
                "active_staged_candidate_path": f"staging/{COHORT}.json",
            })
            write_json(root, f"staging/{COHORT}.json", {})

            def must_not_reapply_preactivation_fence(*args, **kwargs):
                raise AssertionError(
                    "active countable validation must accept post-promotion production heads: "
                    + repr(advanced_production_heads)
                )

            with patch.object(GUARD, "validate_scheduler_manifest", return_value=[]), \
                 patch.object(GUARD, "load_scheduler_admission_source", return_value=({}, [])), \
                 patch.object(GUARD, "validate_scheduler_admission", return_value=[]), \
                 patch.object(GUARD, "validate_production_ref_fence", side_effect=must_not_reapply_preactivation_fence):
                errors = GUARD.validate_countable_scheduler(root, control, {}, {}, require_admission=True)

        self.assertEqual(errors, [])

    def test_exact_g_fence_remains_inside_preactivation_create_transaction_not_countable_health(self):
        guard = (ROOT / "scripts/scheduler_admission_guard.py").read_text(encoding="utf-8")
        admission_start = guard.index("def validate_mm06_scheduler_admission")
        admission_end = guard.index("def validate_scheduler_admission", admission_start)
        countable_start = guard.index("def validate_countable_scheduler")
        countable_end = guard.index('if __name__ == "__main__"', countable_start)

        self.assertIn("validate_production_ref_fence(", guard[admission_start:admission_end])
        self.assertNotIn("validate_production_ref_fence(", guard[countable_start:countable_end])

        reconciler = (ROOT / "scripts/reconcile_preactivation_admission.py").read_text(encoding="utf-8")
        self.assertIn("production_ref_snapshot(manifest, str(generation_head))", reconciler)
        self.assertIn("production_ref_revalidation_errors(manifest, str(generation_head), production_snapshot)", reconciler)

        create_gate = (ROOT / "scripts/reconcile_open_prs.py").read_text(encoding="utf-8")
        self.assertIn("production_snapshot=_remote_inactive_production_snapshot(manifest,G)", create_gate)
        self.assertIn("_remote_inactive_production_snapshot(manifest,G)!=production_snapshot", create_gate)

        # Promotion may consume only that already-fenced, create-once receipt;
        # it must not manufacture a fresh receipt after production has started.
        transition = (ROOT / "scripts/transition_guard.py").read_text(encoding="utf-8")
        self.assertIn("root11 promotion must not introduce or modify scheduler admission", transition)
        self.assertIn("root11 scheduler admission must already exist in base unchanged", transition)


if __name__ == "__main__":
    unittest.main()
