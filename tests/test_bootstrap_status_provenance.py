import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OPEN = ROOT / "scripts/reconcile_open_prs.py"
COMPLETION = ROOT / ".github/workflows/supernova-bootstrap-completion-reconcile.yml"


def load_module():
    spec = importlib.util.spec_from_file_location("bootstrap_provenance_test", OPEN)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BootstrapStatusProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.head = "a" * 40
        self.base = "b" * 40
        self.pr = {
            "number": 77,
            "state": "open",
            "user": {"login": "Kitahl"},
            "head": {"sha": self.head, "repo": {"full_name": "Kitahl/Project-supernova-"}},
            "base": {"sha": self.base, "ref": "main"},
        }
        self.run_id = 12345
        self.status = {
            "context": "supernova/bootstrap-admission",
            "state": "success",
            "creator": {"login": "github-actions[bot]"},
            "target_url": f"https://github.com/Kitahl/Project-supernova-/actions/runs/{self.run_id}",
        }
        self.run = {
            "id": self.run_id,
            "workflow_id": 9001,
            "status": "completed",
            "conclusion": "success",
            "event": "pull_request_target",
            "repository": {"full_name": "Kitahl/Project-supernova-"},
            "display_title": f"Supernova Authority Bootstrap PR #77 HEAD={self.head} BASE={self.base}",
        }
        self.workflow = {"path": ".github/workflows/supernova-authority-bootstrap.yml"}

    def install_api(self, *, status=None, run=None, workflow=None, two_valid=False):
        status = self.status if status is None else status
        run = self.run if run is None else run
        workflow = self.workflow if workflow is None else workflow
        def fake(path, method="GET", data=None):
            if path.startswith("/commits/") and path.endswith("/pulls?per_page=20"):
                return [self.pr]
            if path.startswith("/commits/") and path.endswith("/statuses?per_page=100"):
                if two_valid:
                    other = dict(status)
                    other["target_url"] = "https://github.com/Kitahl/Project-supernova-/actions/runs/54321"
                    return [status, other]
                return [status]
            if path == f"/actions/runs/{self.run_id}":
                return run
            if path == "/actions/runs/54321":
                alt = dict(run); alt["id"] = 54321
                return alt
            if path == "/actions/workflows/9001":
                return workflow
            raise AssertionError(path)
        self.mod.api = fake

    def test_exact_designated_completed_run_passes(self):
        self.install_api()
        self.assertTrue(self.mod.trusted_bootstrap_success(self.head))

    def test_same_bot_context_from_wrong_workflow_fails(self):
        self.install_api(workflow={"path": ".github/workflows/other.yml"})
        self.assertFalse(self.mod.trusted_bootstrap_success(self.head))

    def test_wrong_event_or_incomplete_run_fails(self):
        bad = dict(self.run); bad["event"] = "push"
        self.install_api(run=bad)
        self.assertFalse(self.mod.trusted_bootstrap_success(self.head))
        bad = dict(self.run); bad["status"] = "in_progress"; bad["conclusion"] = None
        self.install_api(run=bad)
        self.assertFalse(self.mod.trusted_bootstrap_success(self.head))

    def test_wrong_head_or_base_binding_in_run_name_fails(self):
        bad = dict(self.run); bad["display_title"] = "Supernova Authority Bootstrap PR #77 HEAD=" + ("c" * 40) + " BASE=" + self.base
        self.install_api(run=bad)
        self.assertFalse(self.mod.trusted_bootstrap_success(self.head))

    def test_status_without_exact_run_url_fails(self):
        bad = dict(self.status); bad["target_url"] = None
        self.install_api(status=bad)
        self.assertFalse(self.mod.trusted_bootstrap_success(self.head))

    def test_ambiguous_multiple_valid_run_receipts_fail(self):
        self.install_api(two_valid=True)
        self.assertFalse(self.mod.trusted_bootstrap_success(self.head))

    def test_completion_reconciler_waits_for_workflow_run_completion(self):
        text = COMPLETION.read_text(encoding="utf-8")
        self.assertIn("workflow_run:", text)
        self.assertIn('workflows: ["Supernova Authority Bootstrap"]', text)
        self.assertIn("types: [completed]", text)
        self.assertIn("actions: read", text)
        self.assertIn("statuses: write", text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", text)
        self.assertIn("python scripts/reconcile_open_prs.py", text)


if __name__ == "__main__":
    unittest.main()
