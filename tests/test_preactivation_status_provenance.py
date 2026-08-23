import importlib.util
import pathlib
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PreactivationStatusProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module("preactivation_status_provenance", "scripts/reconcile_preactivation_admission.py")
        self.commit = "a" * 40
        self.generation = "b" * 40
        self.main = "c" * 40
        self.cohort = "CAL-BR-013-test"
        self.role = "MF01"
        self.branch = f"ps/preactivate/{self.cohort}/{self.role}"
        self.pr = {
            "number": 7,
            "head": {"sha": self.commit},
            "base": {"sha": self.generation},
        }
        description = self.mod.binding_description(7, self.role, self.commit, self.generation, self.branch, self.main)
        self.row = {
            "id": 99,
            "context": self.mod.CONTEXT,
            "state": "success",
            "creator": {"login": "github-actions[bot]"},
            "description": description,
            "target_url": f"https://github.com/{self.mod.REPO}/actions/runs/123",
            "created_at": "2030-01-01T00:05:00Z",
        }
        self.run = {
            "path": self.mod.WORKFLOW,
            "event": "pull_request_target",
            "status": "completed",
            "conclusion": "success",
            "head_sha": self.commit,
            "head_branch": self.branch,
            "repository": {"full_name": self.mod.REPO},
            "actor": {"login": self.mod.OWNER},
        }
        self.manifest = {
            "max_attempt_duration_seconds": 600,
            "scheduler_jitter_budget_seconds": 60,
            "tasks": [{"role_id": self.role, "challenge_occurrences_utc": ["2030-01-01T00:00:00Z"]}],
        }
        self.receipt = {"challenge_occurrence_utc": "2030-01-01T00:00:00Z"}

    def observe(self, created_at="2030-01-01T00:05:00Z", cutoff="2030-01-01T00:10:00Z"):
        self.row["created_at"] = created_at

        def fake_api(path, *args, **kwargs):
            if path.startswith("/pulls?state=all"):
                return [self.pr]
            if path == f"/commits/{self.commit}/statuses?per_page=100":
                return [self.row]
            if path == "/actions/runs/123":
                return self.run
            if path == "/pulls/7":
                return self.pr
            raise AssertionError(path)

        def fake_load_ref(ref, path):
            if path == f"scheduler/{self.cohort}.json":
                return self.manifest
            if path == f"preactivation/{self.cohort}/{self.role}.json":
                return self.receipt
            raise AssertionError((ref, path))

        def fake_blob(ref, path):
            if (ref, path) in ((self.main, "state/STAGED.json"), ("HEAD", "state/STAGED.json")):
                return "d" * 40
            return None

        with mock.patch.object(self.mod, "api", side_effect=fake_api), \
             mock.patch.object(self.mod, "load_ref", side_effect=fake_load_ref), \
             mock.patch.object(self.mod, "blob_at", side_effect=fake_blob), \
             mock.patch.object(self.mod, "git_main_head", return_value="e" * 40), \
             mock.patch.object(self.mod, "git", return_value=(0, "")):
            return self.mod.source_status_observation(
                self.commit, self.role, self.cohort, self.generation, cutoff
            )

    def test_exact_status_inside_signed_challenge_window_is_accepted(self):
        self.assertEqual(self.observe(), self.row)

    def test_status_before_claimed_challenge_is_rejected(self):
        self.assertIsNone(self.observe("2029-12-31T23:59:59Z"))

    def test_status_after_attempt_plus_jitter_is_rejected(self):
        self.assertIsNone(self.observe("2030-01-01T00:11:01Z", "2030-01-01T00:20:00Z"))

    def test_status_after_admission_cutoff_is_rejected(self):
        self.assertIsNone(self.observe("2030-01-01T00:05:01Z", "2030-01-01T00:05:00Z"))

    def test_pull_request_target_run_must_bind_candidate_head_and_ref(self):
        self.run["head_sha"] = self.main
        self.run["head_branch"] = "main"
        self.assertIsNone(self.observe())


class OpenMainPrPaginationTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module("open_pr_pagination", "scripts/reconcile_open_prs.py")

    def test_inventory_reads_until_short_page(self):
        def fake_api(path):
            page = int(path.rsplit("=", 1)[1])
            if page == 1:
                return [{"number": value} for value in range(1, 101)]
            if page == 2:
                return [{"number": 101}]
            raise AssertionError(path)
        with mock.patch.object(self.mod, "api", side_effect=fake_api):
            rows, errors = self.mod.open_main_prs()
        self.assertEqual(len(rows), 101)
        self.assertEqual(errors, [])

    def test_bounded_scan_fails_closed_instead_of_truncating_silently(self):
        with mock.patch.object(self.mod, "api", return_value=[{"number": value} for value in range(100)]):
            rows, errors = self.mod.open_main_prs()
        self.assertEqual(len(rows), 100)
        self.assertEqual(errors, ["open main PR inventory exceeds bounded exhaustive scan"])


if __name__ == "__main__":
    unittest.main()
