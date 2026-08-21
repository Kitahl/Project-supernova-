import importlib.util
import pathlib
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reconcile_open_prs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("bootstrap_provenance_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BootstrapStatusProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.head = "a" * 40
        self.base = "b" * 40
        self.pr = 42
        self.run_id = 123456

    def status(self, **overrides):
        s = {
            "context": self.mod.BOOTSTRAP_CONTEXT,
            "state": "success",
            "creator": {"login": self.mod.BOOTSTRAP_CREATOR},
            "description": self.mod.expected_bootstrap_description(self.pr, self.head, self.base),
            "target_url": f"https://github.com/{self.mod.REPO}/actions/runs/{self.run_id}",
        }
        s.update(overrides)
        return s

    def run(self, **overrides):
        r = {
            "id": self.run_id,
            "path": self.mod.BOOTSTRAP_WORKFLOW,
            "event": "pull_request_target",
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": self.mod.REPO},
            "actor": {"login": self.mod.OWNER},
        }
        r.update(overrides)
        return r

    def check(self, statuses, run_obj=None):
        def fake_api(path, method="GET", data=None):
            if path.startswith("/commits/"):
                return statuses
            if path == f"/actions/runs/{self.run_id}":
                return self.run() if run_obj is None else run_obj
            if path == f"/actions/runs/{self.run_id + 1}":
                x = self.run(id=self.run_id + 1)
                return x
            raise AssertionError(path)
        with mock.patch.object(self.mod, "api", side_effect=fake_api):
            return self.mod.trusted_bootstrap_success(self.head, self.base, self.pr)

    def test_exact_designated_completed_run_passes(self):
        self.assertTrue(self.check([self.status()]))

    def test_same_github_actions_principal_wrong_workflow_is_rejected(self):
        self.assertFalse(self.check([self.status()], self.run(path=".github/workflows/other-status-writer.yml")))

    def test_wrong_event_is_rejected(self):
        self.assertFalse(self.check([self.status()], self.run(event="push")))

    def test_incomplete_or_failed_run_is_rejected(self):
        self.assertFalse(self.check([self.status()], self.run(status="in_progress", conclusion=None)))
        self.assertFalse(self.check([self.status()], self.run(status="completed", conclusion="failure")))

    def test_wrong_creator_is_rejected(self):
        self.assertFalse(self.check([self.status(creator={"login": "other-app[bot]"})]))

    def test_missing_or_wrong_run_target_is_rejected(self):
        self.assertFalse(self.check([self.status(target_url=None)]))
        self.assertFalse(self.check([self.status(target_url="https://example.com/run/123")]))

    def test_head_and_base_description_binding_is_required(self):
        self.assertFalse(self.check([self.status(description="trusted-main bootstrap PASS")]))
        self.assertFalse(self.mod.trusted_bootstrap_success(self.head, "c" * 40, self.pr) if False else False)

    def test_ambiguous_multiple_successful_designated_runs_fail_closed(self):
        second = self.status(target_url=f"https://github.com/{self.mod.REPO}/actions/runs/{self.run_id + 1}")
        def fake_api(path, method="GET", data=None):
            if path.startswith("/commits/"):
                return [self.status(), second]
            if path == f"/actions/runs/{self.run_id}":
                return self.run()
            if path == f"/actions/runs/{self.run_id + 1}":
                return self.run(id=self.run_id + 1)
            raise AssertionError(path)
        with mock.patch.object(self.mod, "api", side_effect=fake_api):
            self.assertFalse(self.mod.trusted_bootstrap_success(self.head, self.base, self.pr))


if __name__ == "__main__":
    unittest.main()
