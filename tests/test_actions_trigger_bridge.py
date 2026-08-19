import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMENT_WF = ROOT / ".github" / "workflows" / "supernova-comment-admission.yml"
TARGET_WF = ROOT / ".github" / "workflows" / "supernova-pr-target-admission.yml"


def uses_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.search(r"^\s*-\s+uses:\s*", line)]


class ActionsTriggerBridgeTests(unittest.TestCase):
    def test_comment_bridge_is_action_free(self):
        text = COMMENT_WF.read_text(encoding="utf-8")
        self.assertIn("issue_comment:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("/supernova-admit", text)
        self.assertIn("statuses: write", text)
        self.assertIn("scripts/reconcile_open_prs.py", text)
        self.assertIn("supernova/actions-comment-heartbeat", text)
        self.assertEqual(uses_lines(text), [])

    def test_pr_target_bridge_is_owner_same_repo_only(self):
        text = TARGET_WF.read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", text)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", text)
        self.assertIn("github.event.pull_request.user.login == github.repository_owner", text)
        self.assertIn("statuses: write", text)
        self.assertIn("supernova/actions-pr-target-heartbeat", text)
        self.assertIn("r.validate_pr", text)
        self.assertEqual(uses_lines(text), [])

    def test_bridges_do_not_mutate_canonical_state(self):
        for path in (COMMENT_WF, TARGET_WF):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("git push", text)
            self.assertNotIn("merge_pull", text)

    def test_statuses_permission_does_not_count_as_marketplace_action(self):
        self.assertIn("statuses: write", COMMENT_WF.read_text(encoding="utf-8"))
        self.assertEqual(uses_lines("permissions:\n  statuses: write\n"), [])


if __name__ == "__main__":
    unittest.main()
