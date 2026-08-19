import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "task_registry_v25.json"


class HourlyTaskRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_exactly_fifteen_lanes(self):
        tasks = self.registry["tasks"]
        self.assertEqual(len(tasks), 15)
        self.assertEqual(len({task["role_id"] for task in tasks}), 15)
        self.assertTrue(self.registry["no_sixteenth_lane"])
        self.assertEqual(self.registry["active_task_count"], 15)

    def test_every_local_hour_is_scheduled_once(self):
        self.assertEqual(self.registry["schedule_hours_local"], list(range(24)))
        self.assertEqual(self.registry["minimum_recurrence_per_task"], "PT1H")
        self.assertEqual(self.registry["schedule_mode"], "HOURLY_STAGGERED_FAN_IN")

    def test_staggered_fan_in_order(self):
        minute_by_role = {task["role_id"]: task["minute"] for task in self.registry["tasks"]}
        workers = ["MF01", "MF02", "MF03", "MF04", "MF05", "MM01", "MM02", "MM03", "MM04", "MM05", "MM07", "EXT01"]
        self.assertEqual([minute_by_role[role] for role in workers], list(range(5, 17)))
        self.assertEqual(minute_by_role["MM06"], 35)
        self.assertEqual(minute_by_role["MF06"], 45)
        self.assertEqual(minute_by_role["BIL00"], 58)

    def test_project_binding_is_fail_closed_and_github_canonical(self):
        binding = self.registry["project_binding"]
        self.assertEqual(binding["required_project_name"], "Project Supernova")
        self.assertTrue(binding["persistent_associated_chat_required"])
        self.assertFalse(binding["project_files_available_to_task"])
        self.assertEqual(binding["canonical_material_source"], "GITHUB_APPROVED_CONNECTOR_ONLY")
        self.assertIn("DO_NOT_CLAIM_PROJECT_LOCAL", binding["activation_rule"])

    def test_deep_research_remains_twice_daily(self):
        bil00 = next(task for task in self.registry["tasks"] if task["role_id"] == "BIL00")
        self.assertEqual(bil00["research_hours_local"], [0, 12])
        self.assertIn("all other hourly BIL00 runs", self.registry["research_rule"])


if __name__ == "__main__":
    unittest.main()
