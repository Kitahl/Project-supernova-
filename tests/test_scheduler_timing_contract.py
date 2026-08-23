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
