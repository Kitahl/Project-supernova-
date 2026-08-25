import importlib.util
import pathlib
import sys
import types
import unittest


try:
    import jsonschema  # noqa: F401
except ModuleNotFoundError:
    jsonschema = types.ModuleType("jsonschema")

    class Draft202012Validator:
        def __init__(self, *args, **kwargs): pass
        @classmethod
        def check_schema(cls, *args, **kwargs): return None
        def iter_errors(self, *args, **kwargs): return []
    class FormatChecker: pass
    jsonschema.Draft202012Validator = Draft202012Validator
    jsonschema.FormatChecker = FormatChecker
    sys.modules["jsonschema"] = jsonschema


ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("scheduler_timing_guard", ROOT / "scripts/scheduler_admission_guard.py")
GUARD = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(GUARD)

SCHEDULE = "TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE=05"


class SchedulerTimingContractTests(unittest.TestCase):
    def test_exact_grammar_and_registry_minute_are_required(self):
        self.assertEqual(GUARD.canonical_hourly_minute(SCHEDULE, 5), 5)
        for value in ("TZID=America/Vancouver:hourly", "FREQ=HOURLY;BYMINUTE=05;TZID=America/Vancouver",
                      "TZID=America/Los_Angeles;FREQ=HOURLY;BYMINUTE=05", "TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE=5"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): GUARD.canonical_hourly_minute(value, 5)
        with self.assertRaises(ValueError): GUARD.canonical_hourly_minute(SCHEDULE, 6)

    def test_first_second_are_derived_from_not_before_not_trusted(self):
        first, second = GUARD.derive_hourly_occurrences(SCHEDULE, 5, "2026-01-15T08:04:30Z")
        self.assertEqual(first.isoformat(), "2026-01-15T08:05:00+00:00")
        self.assertEqual(second.isoformat(), "2026-01-15T09:05:00+00:00")
        self.assertEqual(GUARD.validate_canonical_hourly_timing(
            SCHEDULE, 5, 3600, "2026-01-15T08:05:00Z", "2026-01-15T09:05:00Z",
            ["2026-01-15T07:05:00Z"], "2026-01-15T08:04:30Z", "2026-01-15T08:04:00Z"), [])

    def test_fan_in_countable_occurrences_follow_worker_deadline_without_rescheduling(self):
        minutes = {
            "MF01": 5, "MF02": 6, "MF03": 7, "MF04": 8, "MF05": 9,
            "MM01": 10, "MM02": 11, "MM03": 12, "MM04": 13, "MM05": 14,
            "MM07": 15, "EXT01": 16, "MM06": 35, "MF06": 45, "BIL00": 58,
        }
        tasks = {
            role: {"normalized_schedule": f"TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE={minute:02d}"}
            for role, minute in minutes.items()
        }
        registry = {role: {"minute": minute} for role, minute in minutes.items()}
        lanes = {
            role: {"deadline_utc": "2026-01-15T09:27:00Z"}
            for role in GUARD.WORKERS
        }
        occurrences, floors = GUARD.derive_countable_occurrences(
            tasks, registry, lanes, "2026-01-15T08:04:30Z"
        )
        self.assertEqual(occurrences["EXT01"][0].isoformat(), "2026-01-15T08:16:00+00:00")
        self.assertEqual(occurrences["MM06"][0].isoformat(), "2026-01-15T09:35:00+00:00")
        self.assertEqual(occurrences["MF06"][0].isoformat(), "2026-01-15T09:45:00+00:00")
        self.assertEqual(occurrences["BIL00"][0].isoformat(), "2026-01-15T09:58:00+00:00")
        self.assertEqual(floors["MM06"], "2026-01-15T09:27:00.000001Z")

    def test_phase_aware_timing_validation_rejects_the_early_mm06_wake(self):
        schedule = "TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE=35"
        args = (
            schedule, 35, 3600,
            "2026-01-15T09:35:00Z", "2026-01-15T10:35:00Z",
            ["2026-01-15T07:35:00Z"],
            "2026-01-15T08:04:30Z", "2026-01-15T08:04:00Z",
            "2026-01-15T09:27:00.000001Z",
        )
        self.assertEqual(GUARD.validate_canonical_hourly_timing(*args), [])
        early = list(args)
        early[3] = "2026-01-15T08:35:00Z"
        early[4] = "2026-01-15T09:35:00Z"
        errors = GUARD.validate_canonical_hourly_timing(*early)
        self.assertIn(
            "normalized first production occurrence differs from canonical schedule derivation",
            errors,
        )

    def test_downstream_occurrence_at_exact_deadline_is_not_postdeadline(self):
        tasks = {
            role: {"normalized_schedule": "TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE=35"}
            for role in GUARD.ROLES
        }
        registry = {role: {"minute": 35} for role in GUARD.ROLES}
        lanes = {
            role: {"deadline_utc": "2026-01-15T09:35:00Z"}
            for role in GUARD.WORKERS
        }
        occurrences, _ = GUARD.derive_countable_occurrences(
            tasks, registry, lanes, "2026-01-15T08:04:30Z"
        )
        self.assertEqual(occurrences["MM06"][0].isoformat(), "2026-01-15T10:35:00+00:00")

    def test_phase_derivation_requires_exact_worker_lane_inventory(self):
        tasks = {
            role: {"normalized_schedule": "TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE=35"}
            for role in GUARD.ROLES
        }
        registry = {role: {"minute": 35} for role in GUARD.ROLES}
        lanes = {
            role: {"deadline_utc": "2026-01-15T09:35:00Z"}
            for role in GUARD.WORKERS
            if role != "EXT01"
        }
        with self.assertRaisesRegex(ValueError, "exact canonical 12"):
            GUARD.derive_countable_occurrences(
                tasks, registry, lanes, "2026-01-15T08:04:30Z"
            )

    def test_cadence_first_before_not_before_and_challenge_cutoff_fail_closed(self):
        errors = GUARD.validate_canonical_hourly_timing(
            SCHEDULE, 5, 7200, "2026-01-15T08:05:00Z", "2026-01-15T10:05:00Z",
            ["2026-01-15T07:05:00Z"], "2026-01-15T08:04:30Z", "2026-01-15T08:04:45Z")
        self.assertEqual(errors, ["scheduler cadence must equal exactly 3600 seconds"])
        errors = GUARD.validate_canonical_hourly_timing(
            SCHEDULE, 5, 3600, "2026-01-15T07:05:00Z", "2026-01-15T08:05:00Z",
            ["2026-01-15T08:05:00Z"], "2026-01-15T08:04:30Z", "2026-01-15T08:04:00Z")
        self.assertIn("normalized first production occurrence precedes production_not_before", errors)
        self.assertIn("preactivation challenge occurs after admission_cutoff", errors)
        self.assertIn("preactivation challenge is not strictly before production_not_before", errors)

    def test_noncanonical_challenge_and_non_utc_offset_fail_closed(self):
        errors = GUARD.validate_canonical_hourly_timing(
            SCHEDULE, 5, 3600, "2026-01-15T08:05:00Z", "2026-01-15T09:05:00Z",
            ["2026-01-15T07:06:00Z", "2026-01-15T07:05:00-08:00"],
            "2026-01-15T08:04:30Z", "2026-01-15T08:04:00Z")
        self.assertTrue(any("does not align" in error for error in errors))
        self.assertTrue(any("explicit UTC Z instant" in error for error in errors))

    def test_spring_forward_offset_transition_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "DST offset transition"):
            GUARD.derive_hourly_occurrences(SCHEDULE, 5, "2026-03-08T09:04:00Z")

    def test_fall_back_ambiguous_wall_time_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "ambiguous Vancouver DST wall time"):
            GUARD.derive_hourly_occurrences(SCHEDULE, 5, "2024-11-03T08:04:00Z")


if __name__ == "__main__":
    unittest.main()
