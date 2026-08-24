import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMENT_WF = ROOT / ".github" / "workflows" / "supernova-comment-admission.yml"
TARGET_WF = ROOT / ".github" / "workflows" / "supernova-pr-target-admission.yml"
SETUP_PYTHON = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
STATUS_APP_ACTION = "actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1"


def uses_lines(text: str) -> list[str]:
    result = []
    for line in text.splitlines():
        match = re.search(r"^\s*(?:-\s+)?uses:\s*(\S.*)$", line)
        if match:
            result.append("- uses: " + match.group(1).strip())
    return result


class ActionsTriggerBridgeTests(unittest.TestCase):
    def test_comment_bridge_uses_only_pinned_python_setup(self):
        text = COMMENT_WF.read_text(encoding="utf-8")
        self.assertIn("issue_comment:", text)
        self.assertIn("repository_dispatch:", text)
        self.assertIn("types: [supernova-comment-admission]", text)
        self.assertIn("/supernova-admit", text)
        self.assertIn("  structural-comment-heartbeat:", text)
        self.assertIn("  reconcile:", text)
        self.assertIn("statuses: write", text)
        self.assertIn("scripts/reconcile_open_prs.py", text)
        self.assertIn("supernova/actions-comment-heartbeat", text)
        self.assertIn("environment: supernova-protected-writer", text)
        self.assertIn("permission-statuses: write", text)
        self.assertIn("SUPERNOVA_STATUS_TOKEN: ${{ steps.status-token.outputs.token }}", text)
        self.assertEqual(text.count("scripts/reconcile_open_prs.py"), 1)
        self.assertIn("python-version: '3.13'", text)
        self.assertEqual(uses_lines(text), [
            f"- uses: {SETUP_PYTHON} # immutable SHA",
            f"- uses: {STATUS_APP_ACTION} # v3.2.0 immutable SHA",
        ])
        self.assertNotIn("actions/checkout@", text)

    def test_pr_target_bridge_is_owner_same_repo_only(self):
        text = TARGET_WF.read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", text)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", text)
        self.assertIn("github.event.pull_request.user.login == github.repository_owner", text)
        self.assertIn("  structural-pr-target-heartbeat:", text)
        self.assertIn("  reconcile:", text)
        self.assertIn("  structural-ruleset-attestation:", text)
        self.assertIn("statuses: write", text)
        self.assertIn("supernova/actions-pr-target-heartbeat", text)
        self.assertIn("types: [supernova-pr-target-admission]", text)
        self.assertIn("cd trusted && python scripts/reconcile_open_prs.py", text)
        self.assertIn("environment: supernova-protected-writer", text)
        self.assertIn("permission-statuses: write", text)
        self.assertIn("SUPERNOVA_STATUS_TOKEN: ${{ steps.status-token.outputs.token }}", text)
        self.assertEqual(text.count("scripts/reconcile_open_prs.py"), 1)
        self.assertIn("python-version: '3.13'", text)
        self.assertEqual(uses_lines(text), [
            f"- uses: {SETUP_PYTHON} # immutable SHA",
            f"- uses: {STATUS_APP_ACTION} # v3.2.0 immutable SHA",
            f"- uses: {SETUP_PYTHON} # immutable SHA",
            f"- uses: {SETUP_PYTHON} # immutable SHA",
        ])
        self.assertNotIn("actions/checkout@", text)

    def test_bridges_do_not_mutate_canonical_state(self):
        for path in (COMMENT_WF, TARGET_WF):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("git push", text)
            self.assertNotIn("merge_pull", text)

    def test_statuses_permission_does_not_count_as_marketplace_action(self):
        self.assertIn("statuses: write", COMMENT_WF.read_text(encoding="utf-8"))
        self.assertEqual(uses_lines("permissions:\n  statuses: write\n"), [])

    def test_branch_generation_writer_never_checks_out_or_executes_pr_head(self):
        text = (ROOT / ".github" / "workflows" / "supernova-branch-reconciler.yml").read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", text)
        self.assertIn("statuses: write", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", text)
        self.assertIn("github.event.pull_request.user.login == github.repository_owner", text)
        self.assertNotIn("ref: ${{ github.event.pull_request.head", text)
        self.assertNotIn("git checkout ${{ github.event.pull_request.head", text)


if __name__ == "__main__":
    unittest.main()
