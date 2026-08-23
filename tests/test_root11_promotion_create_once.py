import copy
import unittest
from unittest.mock import patch

from scripts import reconcile_open_prs as MOD


BASE = "b" * 40
ROOT = "a" * 40
COHORT = "CAL-BR-014-v25-create-once"
CREATED = (
    f"control/{COHORT}.json",
    f"assignments/{COHORT}.json",
    f"liveness/{COHORT}.json",
    f"scheduler/{COHORT}.json",
    "superseded/CAL-BR-013-v25-parent.json",
    "history/CAL-BR-013-v25-parent/CONSOLIDATION.json",
    f"staging/{COHORT}.json",
)


def name_status(overrides=None):
    statuses = {"state/CURRENT.json": "M", **{path: "A" for path in CREATED}}
    statuses.update(overrides or {})
    return "".join(f"{status}\t{path}\n" for path, status in statuses.items())


def run_with_diff(diff, existing=None):
    existing = set(existing or [])

    def fake_run(command, repo, env=None):
        if command[:3] == ["git", "cat-file", "-e"]:
            return (0, "") if command[3] in existing else (1, "missing")
        if command[:4] == ["git", "diff", "--name-status", "--no-renames"]:
            return 0, diff
        raise AssertionError(command)

    return fake_run


class Root11PromotionCreateOnceTests(unittest.TestCase):
    def test_promotion_accepts_exact_modify_state_and_add_only_evidence_surface(self):
        with patch.object(MOD, "run", side_effect=run_with_diff(name_status())) as mocked:
            self.assertTrue(MOD._root11_promotion_paths_are_create_once("repo", BASE, ROOT, CREATED))
        probes = [entry.args[0][3] for entry in mocked.call_args_list if entry.args[0][:3] == ["git", "cat-file", "-e"]]
        for path in CREATED:
            self.assertIn(f"{ROOT}:{path}", probes)
            self.assertIn(f"{BASE}:{path}", probes)

    def test_promotion_rejects_artifact_existing_at_root_or_later_base(self):
        control = CREATED[0]
        for label, ref in (("root", ROOT), ("base", BASE)):
            with self.subTest(label=label), patch.object(
                MOD,
                "run",
                side_effect=run_with_diff(name_status(), {f"{ref}:{control}"}),
            ):
                self.assertFalse(MOD._root11_promotion_paths_are_create_once("repo", BASE, ROOT, CREATED))

    def test_promotion_rejects_overwrite_rename_or_non_add_archive(self):
        mutations = {
            "control overwrite": name_status({CREATED[0]: "M"}),
            "archive overwrite": name_status({CREATED[-1]: "M"}),
            "state added": name_status({"state/CURRENT.json": "A"}),
            "rename record": name_status() + f"R100\told.json\t{CREATED[0]}\n",
        }
        for label, diff in mutations.items():
            with self.subTest(label=label), patch.object(MOD, "run", side_effect=run_with_diff(diff)):
                self.assertFalse(MOD._root11_promotion_paths_are_create_once("repo", BASE, ROOT, CREATED))

    def test_countable_control_contract_requires_whole_object_and_ordered_paths(self):
        accepted = {
            "schema_version": "PS-COUNTABLE-CONTROL-SET-2.5-26",
            "purpose": "trusted accepted-main contract",
            "required_control_paths": ["PROTOCOL.md", "scripts/validate_bus.py"],
            "canonical_scheduled_task_count": 15,
        }
        control = {"required_control_paths": list(accepted["required_control_paths"])}
        self.assertTrue(MOD._root11_countable_control_contract_matches(
            control, copy.deepcopy(accepted), accepted, copy.deepcopy(accepted)
        ))
        non_path_mutation = copy.deepcopy(accepted)
        non_path_mutation["canonical_scheduled_task_count"] = 16
        self.assertFalse(MOD._root11_countable_control_contract_matches(
            control, non_path_mutation, accepted, copy.deepcopy(accepted)
        ))
        reordered = copy.deepcopy(accepted)
        reordered["required_control_paths"].reverse()
        self.assertFalse(MOD._root11_countable_control_contract_matches(
            control, copy.deepcopy(accepted), accepted, reordered
        ))
        reordered_control = {"required_control_paths": list(reversed(accepted["required_control_paths"]))}
        self.assertFalse(MOD._root11_countable_control_contract_matches(
            reordered_control, copy.deepcopy(accepted), accepted, copy.deepcopy(accepted)
        ))


if __name__ == "__main__":
    unittest.main()
