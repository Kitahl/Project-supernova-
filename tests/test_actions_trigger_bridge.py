import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "supernova-comment-admission.yml"


class ActionsCommentBridgeTests(unittest.TestCase):
    def test_bridge_is_actions_source_and_exact_reconciler(self):
        text = WF.read_text(encoding="utf-8")
        self.assertIn("issue_comment:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("/supernova-admit", text)
        self.assertIn("statuses: write", text)
        self.assertIn("python scripts/reconcile_open_prs.py", text)

    def test_actions_are_full_sha_pinned(self):
        text = WF.read_text(encoding="utf-8")
        self.assertIn("actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683", text)
        self.assertIn("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", text)
        self.assertNotIn("@v4", text)
        self.assertNotIn("@v5", text)

    def test_bridge_does_not_mutate_state(self):
        text = WF.read_text(encoding="utf-8")
        self.assertNotIn("git push", text)
        self.assertNotIn("state/CURRENT.json", text)
        self.assertNotIn("merge_pull", text)


if __name__ == "__main__":
    unittest.main()
