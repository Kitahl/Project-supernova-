import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "preactivation_publication_state",
    ROOT / "scripts/preactivation_publication_state.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class PreactivationPublicationContractTests(unittest.TestCase):
    def classify(self, **changes):
        state = {
            "challenge_open": True,
            "receipt_commit_count": 1,
            "receipt_exact": True,
            "pr_count": 1,
            "pr_exact": True,
            "status_state": "success",
            "status_within_window": True,
        }
        state.update(changes)
        return MODULE.classify(**state)

    def test_registry_requires_commit_pr_and_exact_head_status_for_all_fifteen(self):
        registry = load("config/task_registry_v25.json")
        semantics = load("config/task_registry_semantics_v25.json")
        self.assertEqual(len(registry["tasks"]), 15)
        self.assertIn("EXACTLY_ONE_NON_DRAFT_PR", registry["preactivation_publication_rule"])
        self.assertIn("RECEIPT_COMMIT_ALONE_IS_NOT_SUCCESS", registry["preactivation_publication_rule"])
        self.assertIn("ONE_EXACT_NON_DRAFT_PR", semantics["preactivation_publication_rule"])
        self.assertEqual(tuple(registry["preactivation_outcomes"]), MODULE.OUTCOMES)
        self.assertEqual(tuple(semantics["preactivation_outcomes"]), MODULE.OUTCOMES)

    def test_trusted_workflow_requires_an_exact_internal_nondraft_pr_shape(self):
        workflow = (ROOT / ".github/workflows/supernova-preactivation-admission.yml").read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", workflow)
        self.assertIn("github.event.pull_request.draft == false", workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", workflow)
        self.assertIn("startsWith(github.event.pull_request.base.ref, 'ps/gen/')", workflow)
        self.assertIn("startsWith(github.event.pull_request.head.ref, 'ps/preactivate/')", workflow)

    def test_happy_path_is_admitted(self):
        self.assertEqual(self.classify()["state"], "ADMITTED")

    def test_waiting_and_missing_transitions_are_typed(self):
        waiting = self.classify(challenge_open=False, receipt_commit_count=0, receipt_exact=False, pr_count=0, pr_exact=False, status_state=None, status_within_window=None)
        self.assertEqual(waiting["state"], "WAITING_FOR_CHALLENGE")
        no_receipt = self.classify(receipt_commit_count=0, receipt_exact=False, pr_count=0, pr_exact=False, status_state=None, status_within_window=None)
        self.assertEqual(no_receipt["state"], "BLOCKED")
        self.assertEqual(no_receipt["next_action"], "CREATE_EXACT_RECEIPT_COMMIT")
        no_pr = self.classify(pr_count=0, pr_exact=False, status_state=None, status_within_window=None)
        self.assertEqual(no_pr["state"], "RECEIPT_COMMITTED_PR_MISSING")
        self.assertEqual(no_pr["next_action"], "OPEN_OR_REUSE_EXACT_PR_WITHOUT_NEW_COMMIT")
        pending = self.classify(status_state="pending", status_within_window=None)
        self.assertEqual(pending["state"], "PR_OPEN_STATUS_PENDING")

    def test_evidence_before_challenge_is_rejected(self):
        outcome = self.classify(challenge_open=False)
        self.assertEqual(outcome["state"], "REJECTED")
        self.assertIn("before", outcome["reason"])

    def test_invalid_or_duplicate_publication_is_rejected(self):
        cases = (
            {"receipt_commit_count": 2},
            {"receipt_exact": False},
            {"pr_count": 2},
            {"pr_exact": False},
            {"status_state": "failure"},
            {"status_state": "error"},
            {"status_state": "cancelled"},
            {"status_state": "success", "status_within_window": False},
        )
        for case in cases:
            with self.subTest(case=case):
                outcome = self.classify(**case)
                self.assertEqual(outcome["state"], "REJECTED")
                self.assertEqual(outcome["next_action"], "STOP_NO_CONSTRUCTIVE_REPAIR")

    def test_unknown_evidence_fails_closed_with_a_reason(self):
        for case in (
            {"status_state": "success", "status_within_window": None},
            {"status_state": "mystery", "status_within_window": None},
        ):
            with self.subTest(case=case):
                outcome = self.classify(**case)
                self.assertEqual(outcome["state"], "BLOCKED")
                self.assertTrue(outcome["reason"])
                self.assertTrue(outcome["next_action"])

    def test_negative_counts_are_invalid_input(self):
        with self.assertRaises(ValueError):
            self.classify(receipt_commit_count=-1)


if __name__ == "__main__":
    unittest.main()
