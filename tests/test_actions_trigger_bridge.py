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
        self.assertIn("scripts/reconcile_open_prs.py", text)
        self.assertIn("supernova/actions-comment-heartbeat", text)

    def test_bridge_has_no_marketplace_action_dependency(self):
        text = WF.read_text(encoding="utf-8")
        self.assertNotIn("uses:", text)
        self.assertIn("git clone --filter=blob:none", text)
        self.assertIn("python3 -m pip install", text)

    def test_bridge_does_not_mutate_state(self):
        text = WF.read_text(encoding="utf-8")
        self.assertNotIn("git push", text)
        self.assertNotIn("state/CURRENT.json", text)
        self.assertNotIn("merge_pull", text)


if __name__ == "__main__":
    unittest.main()
