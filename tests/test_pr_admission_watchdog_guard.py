import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DISPATCHER = ROOT / "scripts" / "dispatch_missing_pr_admission.py"
ADMISSION_WF = ROOT / ".github" / "workflows" / "supernova-v25-admission.yml"
RECONCILER_WF = ROOT / ".github" / "workflows" / "supernova-rest-branch-reconciler.yml"


def load_dispatcher():
    spec = importlib.util.spec_from_file_location("dispatch_missing_pr_admission", DISPATCHER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrAdmissionWatchdogGuardTests(unittest.TestCase):
    def test_only_zero_context_heads_are_dispatch_candidates(self):
        mod = load_dispatcher()
        self.assertEqual(mod.admission_context_state([]), "MISSING_ALL")
        self.assertEqual(
            mod.admission_context_state([{"context": "supernova/static-control", "state": "success"}]),
            "PARTIAL",
        )
        complete = [{"context": c, "state": "success"} for c in mod.REQUIRED_CONTEXTS]
        self.assertEqual(mod.admission_context_state(complete), "COMPLETE")

    def test_recent_marker_suppresses_duplicate_dispatch(self):
        mod = load_dispatcher()
        now = dt.datetime(2026, 8, 19, 9, 0, tzinfo=dt.timezone.utc)
        statuses = [{
            "context": mod.MARKER_CONTEXT,
            "state": "success",
            "created_at": "2026-08-19T08:50:00Z",
        }]
        self.assertTrue(mod.marker_is_recent(statuses, now=now))
        self.assertFalse(mod.marker_is_recent(statuses, now=now + dt.timedelta(hours=1)))

    def test_authoritative_dispatch_requires_exact_pr_context(self):
        text = ADMISSION_WF.read_text(encoding="utf-8")
        self.assertIn("pr_number:", text)
        self.assertIn("required: true", text)
        self.assertIn("dispatch target PR must be open", text)
        self.assertIn("dispatch target PR base must be main", text)
        self.assertIn("fallback admits same-repository PRs only", text)
        self.assertIn("ref: ${{ steps.ctx.outputs.head_sha }}", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("TARGET_SHA: ${{ steps.ctx.outputs.head_sha }}", text)

    def test_watchdog_runs_even_if_another_reconciler_fails(self):
        text = RECONCILER_WF.read_text(encoding="utf-8")
        self.assertIn("actions: write", text)
        self.assertIn("pull-requests: read", text)
        self.assertIn("dispatch_missing_pr_admission.py", text)
        self.assertIn("python3 /tmp/reconcile_branch_rest.py || rc=1", text)
        self.assertIn("python3 /tmp/reconcile_v25_admission.py || rc=1", text)
        self.assertIn("python3 /tmp/dispatch_missing_pr_admission.py || rc=1", text)


if __name__ == "__main__":
    unittest.main()
