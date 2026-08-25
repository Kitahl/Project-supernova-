import importlib.util
import os
import pathlib
import urllib.error
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/reconcile_branch_statuses.py"
SPEC = importlib.util.spec_from_file_location("branch_status_idempotence_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
branch_statuses = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(branch_statuses)

TRUSTED_MAIN = "1" * 40
STATUS_SHA = "a" * 40
RUN_ID = "123"
RUN_URL = f"https://github.com/{branch_statuses.REPO}/actions/runs/{RUN_ID}"


class BranchStatusIdempotenceTests(unittest.TestCase):
    def setUp(self):
        token = mock.patch.object(branch_statuses, "TOKEN", "test-token")
        token.start()
        self.addCleanup(token.stop)

    @staticmethod
    def _response():
        response = mock.MagicMock()
        response.read.return_value = b"{}"
        return response

    @staticmethod
    def _row(state="pending", description="awaiting immutable report: 12/12 lanes", integration_id=15368):
        return {
            "context": "supernova/branch-worker",
            "state": state,
            "description": description,
            "avatar_url": f"https://avatars.githubusercontent.com/in/{integration_id}?v=4",
            "target_url": RUN_URL,
        }

    @staticmethod
    def _run(**overrides):
        run = {
            "path": branch_statuses.BRANCH_RECONCILER_WORKFLOW,
            "event": "schedule",
            "status": "completed",
            "conclusion": "success",
            "head_sha": TRUSTED_MAIN,
            "repository": {"full_name": branch_statuses.REPO},
            "actor": {"login": branch_statuses.OWNER},
        }
        run.update(overrides)
        return run

    def _api_for(self, row, run=None):
        def fake(path):
            if path == f"/commits/{STATUS_SHA}/status?per_page=100":
                return {"statuses": [] if row is None else [row]}
            if path == f"/actions/runs/{RUN_ID}":
                return self._run() if run is None else run
            self.fail(f"unexpected API path: {path}")
        return fake

    def test_matching_current_main_workflow_status_skips_write(self):
        with mock.patch.object(branch_statuses, "api", side_effect=self._api_for(self._row())) as status_read, mock.patch.object(
            branch_statuses, "git", return_value=(0, TRUSTED_MAIN, "")
        ), mock.patch("urllib.request.urlopen") as urlopen:
            wrote = branch_statuses.post(
                STATUS_SHA,
                "supernova/branch-worker",
                "pending",
                "awaiting immutable report: 12/12 lanes",
            )
        self.assertFalse(wrote)
        self.assertEqual(status_read.call_count, 2)
        urlopen.assert_not_called()

    def test_wrong_integration_cannot_suppress_authoritative_write(self):
        with mock.patch.object(branch_statuses, "api", side_effect=self._api_for(self._row(integration_id=999))), mock.patch(
            "urllib.request.urlopen", return_value=self._response()
        ) as urlopen:
            wrote = branch_statuses.post(
                STATUS_SHA,
                "supernova/branch-worker",
                "pending",
                "awaiting immutable report: 12/12 lanes",
            )
        self.assertTrue(wrote)
        self.assertEqual(urlopen.call_count, 1)

    def test_wrong_workflow_or_stale_main_cannot_suppress_write(self):
        cases = (
            self._run(path=".github/workflows/not-the-branch-reconciler.yml"),
            self._run(head_sha="2" * 40),
        )
        for run in cases:
            with self.subTest(run=run), mock.patch.object(
                branch_statuses, "api", side_effect=self._api_for(self._row(), run)
            ), mock.patch.object(branch_statuses, "git", return_value=(0, TRUSTED_MAIN, "")), mock.patch(
                "urllib.request.urlopen", return_value=self._response()
            ) as urlopen:
                wrote = branch_statuses.post(
                    STATUS_SHA,
                    "supernova/branch-worker",
                    "pending",
                    "awaiting immutable report: 12/12 lanes",
                )
            self.assertTrue(wrote)
            self.assertEqual(urlopen.call_count, 1)

    def test_changed_state_or_description_writes_replacement(self):
        cases = (
            self._row(state="failure"),
            self._row(description="awaiting immutable report: 11/12 lanes"),
        )
        for row in cases:
            with self.subTest(row=row), mock.patch.object(
                branch_statuses, "api", side_effect=self._api_for(row)
            ), mock.patch("urllib.request.urlopen", return_value=self._response()) as urlopen:
                wrote = branch_statuses.post(
                    STATUS_SHA,
                    "supernova/branch-worker",
                    "pending",
                    "awaiting immutable report: 12/12 lanes",
                )
            self.assertTrue(wrote)
            self.assertEqual(urlopen.call_count, 1)

    def test_description_is_compared_after_transport_truncation(self):
        description = "x" * 150
        row = self._row(description="x" * 140)
        with mock.patch.object(branch_statuses, "api", side_effect=self._api_for(row)), mock.patch.object(
            branch_statuses, "git", return_value=(0, TRUSTED_MAIN, "")
        ), mock.patch("urllib.request.urlopen") as urlopen:
            wrote = branch_statuses.post(STATUS_SHA, "supernova/branch-worker", "pending", description)
        self.assertFalse(wrote)
        urlopen.assert_not_called()

    def test_status_read_failure_falls_back_to_existing_write_path(self):
        error = urllib.error.HTTPError("https://api.github.test", 500, "boom", {}, None)
        with mock.patch.object(branch_statuses, "api", side_effect=error), mock.patch(
            "urllib.request.urlopen", return_value=self._response()
        ) as urlopen:
            wrote = branch_statuses.post(STATUS_SHA, "supernova/branch-worker", "pending", "unchanged")
        self.assertTrue(wrote)
        self.assertEqual(urlopen.call_count, 1)

    def test_repeated_unchanged_status_never_approaches_github_ceiling(self):
        current = {"row": None}
        writes = 0

        def fake_api(path):
            if path == f"/commits/{STATUS_SHA}/status?per_page=100":
                return {"statuses": [] if current["row"] is None else [current["row"]]}
            if path == f"/actions/runs/{RUN_ID}":
                return self._run()
            self.fail(f"unexpected API path: {path}")

        def status_write(request, timeout):
            nonlocal writes
            self.assertEqual(timeout, 30)
            writes += 1
            if writes > 1000:
                raise urllib.error.HTTPError(request.full_url, 422, "status ceiling", {}, None)
            payload = branch_statuses.strict_json.loads(request.data.decode("utf-8"))
            current["row"] = {
                "context": payload["context"],
                "state": payload["state"],
                "description": payload["description"],
                "avatar_url": "https://avatars.githubusercontent.com/in/15368?v=4",
                "target_url": payload["target_url"],
            }
            return self._response()

        with mock.patch.object(branch_statuses, "api", side_effect=fake_api), mock.patch.object(
            branch_statuses, "git", return_value=(0, TRUSTED_MAIN, "")
        ), mock.patch("urllib.request.urlopen", side_effect=status_write), mock.patch.dict(
            os.environ, {"GITHUB_RUN_ID": RUN_ID}, clear=True
        ):
            outcomes = [
                branch_statuses.post(
                    STATUS_SHA,
                    "supernova/branch-worker",
                    "pending",
                    "awaiting immutable report: 12/12 lanes",
                )
                for _ in range(1001)
            ]
        self.assertEqual(writes, 1)
        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(outcomes.count(False), 1000)

    def test_twelve_empty_worker_lanes_collapse_to_one_aggregate_status(self):
        generation_head = "f" * 40
        workers = {f"W{i:02d}": f"ps/work/cohort/W{i:02d}" for i in range(1, 13)}
        state = {
            "transport_mode": "BRANCH_GITOPS",
            "active_cohort_id": "cohort",
            "generation_head_sha": generation_head,
            "generation_branch": "ps/gen/cohort",
            "worker_branches": workers,
            "verifier_branch": "ps/verify/cohort",
            "integrator_branch": "ps/integrate/cohort",
            "consolidation_branch": None,
        }

        def remote_head(_repo, branch):
            if branch == state["generation_branch"] or branch in workers.values():
                return generation_head
            return None

        with mock.patch.object(branch_statuses, "load", return_value=state), mock.patch.object(
            branch_statuses, "git", return_value=(0, "", "")
        ), mock.patch.object(branch_statuses, "remote_head", side_effect=remote_head), mock.patch.object(
            branch_statuses, "validate_branch", return_value=(True, "BRANCH VALIDATION PASS")
        ), mock.patch.object(branch_statuses, "post") as post:
            self.assertEqual(branch_statuses.main(), 0)

        worker_calls = [
            call
            for call in post.call_args_list
            if len(call.args) >= 2 and call.args[1] == "supernova/branch-worker"
        ]
        self.assertEqual(
            worker_calls,
            [
                mock.call(
                    generation_head,
                    "supernova/branch-worker",
                    "pending",
                    "awaiting immutable report: 12/12 lanes",
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
