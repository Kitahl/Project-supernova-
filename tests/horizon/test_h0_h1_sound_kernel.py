from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "horizon_sound_kernel.py"
SPEC = importlib.util.spec_from_file_location("horizon_sound_kernel", SCRIPT)
kernel = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(kernel)

FIXTURES = ROOT / "diagnostics" / "stage0" / "h0" / "worlds_v1.json"


def load_worlds():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))["worlds"]


def make_book(world):
    scope = kernel.HorizonScope(
        state_id=world["state_id"],
        horizon=world["horizon"],
        budget=world["budget"],
        semantic_version=world["semantic_version"],
    )
    book = kernel.SoundBoundBook(scope=scope, actions=tuple(world["q_star"].keys()))
    return scope, book


class H0H1SoundKernelTests(unittest.TestCase):
    def test_fixture_contract_is_synthetic_zero_authority(self):
        doc = json.loads(FIXTURES.read_text(encoding="utf-8"))
        self.assertEqual(doc["authority"], "NONE_SYNTHETIC_QUALIFICATION_ONLY")
        self.assertFalse(doc["fresh_evidence"])
        self.assertEqual(doc["scientific_credit"], 0)
        self.assertEqual(doc["protocol_version"], "2.5")
        self.assertEqual(doc["specification_revision"], 4)
        self.assertGreaterEqual(len(doc["worlds"]), 10)

    def test_every_noncontradictory_h0_sound_bound_contains_exact_q_star(self):
        for world in load_worlds():
            if world.get("expected_error") == "BOUND_CONTRADICTION":
                continue
            for action, qstar in world["q_star"].items():
                for lower, upper in world["sound_bounds"][action]:
                    with self.subTest(world=world["world_id"], action=action, interval=(lower, upper)):
                        self.assertLessEqual(lower, qstar)
                        self.assertGreaterEqual(upper, qstar)

    def test_expected_h0_certified_winners_and_nonstops(self):
        for world in load_worlds():
            if world.get("expected_error"):
                continue
            scope, book = make_book(world)
            for action, intervals in world["sound_bounds"].items():
                for idx, (lower, upper) in enumerate(intervals):
                    book.register(kernel.HorizonBound(
                        scope=scope,
                        action_id=action,
                        lower=lower,
                        upper=upper,
                        evidence_kind=kernel.EvidenceKind.SOUND,
                        source_id=f"{world['world_id']}:{action}:{idx}",
                        provenance_ref=f"fixture:{world['world_id']}",
                    ))
            self.assertEqual(
                book.certified_winner(),
                world.get("expected_certified_winner"),
                world["world_id"],
            )

    def test_contradictory_sound_evidence_fails_at_registration(self):
        world = next(w for w in load_worlds() if w["world_id"] == "H0-CONTRADICTORY-SOUND")
        scope, book = make_book(world)
        first, second = world["sound_bounds"]["a"]
        book.register(kernel.HorizonBound(scope, "a", first[0], first[1], kernel.EvidenceKind.SOUND, "a:first", "fixture"))
        with self.assertRaisesRegex(kernel.BoundContradiction, "BOUND_CONTRADICTION"):
            book.register(kernel.HorizonBound(scope, "a", second[0], second[1], kernel.EvidenceKind.SOUND, "a:second", "fixture"))

    def test_heuristic_only_cannot_narrow_certifying_interval(self):
        world = next(w for w in load_worlds() if w["world_id"] == "H0-UNEQUAL-HEURISTIC-ALLOCATION")
        scope, book = make_book(world)
        book.register(kernel.HorizonBound(scope, "a", 4.0, 6.0, kernel.EvidenceKind.SOUND, "sound", "fixture"))
        before = book.sound_interval("a")
        book.register(kernel.HorizonBound(scope, "a", 4.99, 5.01, kernel.EvidenceKind.HEURISTIC_ONLY, "heuristic", "fixture"))
        after = book.sound_interval("a")
        self.assertEqual(before, after)
        self.assertEqual(len(book.diagnostic_bounds("a")), 2)

    def test_calibrated_evidence_is_retained_but_noncertifying_in_h1_sound_scope(self):
        world = next(w for w in load_worlds() if w["world_id"] == "H0-CORRELATED-CALIBRATED")
        scope, book = make_book(world)
        book.register(kernel.HorizonBound(scope, "a", 5.0, 7.0, kernel.EvidenceKind.SOUND, "sound", "fixture"))
        book.register(kernel.HorizonBound(scope, "a", 5.95, 6.05, kernel.EvidenceKind.ANYTIME_CALIBRATED, "cal-1", "fixture"))
        book.register(kernel.HorizonBound(scope, "a", 5.96, 6.04, kernel.EvidenceKind.ANYTIME_CALIBRATED, "cal-2", "fixture"))
        self.assertEqual(book.sound_interval("a").lower, 5.0)
        self.assertEqual(book.sound_interval("a").upper, 7.0)
        self.assertFalse(world["properties"]["independence_claim"])

    def test_stale_semantic_bound_rejected(self):
        world = next(w for w in load_worlds() if w["world_id"] == "H0-SEMANTIC-EXPIRY")
        scope, book = make_book(world)
        stale = kernel.HorizonScope(scope.state_id, scope.horizon, scope.budget, world["properties"]["stale_semantic_version"])
        with self.assertRaises(kernel.ScopeMismatch):
            book.register(kernel.HorizonBound(stale, "new_semantics", 5.5, 6.5, kernel.EvidenceKind.SOUND, "stale", "fixture"))

    def test_missing_sound_bound_fails_closed(self):
        scope = kernel.HorizonScope("s", 1, 1, "lambda")
        book = kernel.SoundBoundBook(scope=scope, actions=("a", "b"))
        book.register(kernel.HorizonBound(scope, "a", 0.0, 1.0, kernel.EvidenceKind.SOUND, "a", "fixture"))
        with self.assertRaises(kernel.MissingSoundBound):
            book.certified_winner()

    def test_invalid_nonfinite_and_reversed_bounds_rejected(self):
        scope = kernel.HorizonScope("s", 1, 1, "lambda")
        with self.assertRaises(kernel.HorizonKernelError):
            kernel.HorizonBound(scope, "a", 2.0, 1.0, kernel.EvidenceKind.SOUND, "x", "p")
        with self.assertRaises(kernel.HorizonKernelError):
            kernel.HorizonBound(scope, "a", float("nan"), 1.0, kernel.EvidenceKind.SOUND, "x", "p")

    def test_strict_delta_stop_is_not_non_strict(self):
        scope = kernel.HorizonScope("s", 1, 1, "lambda")
        book = kernel.SoundBoundBook(scope=scope, actions=("a", "b"))
        book.register(kernel.HorizonBound(scope, "a", 2.0, 2.0, kernel.EvidenceKind.SOUND, "a", "p"))
        book.register(kernel.HorizonBound(scope, "b", 1.0, 1.0, kernel.EvidenceKind.SOUND, "b", "p"))
        self.assertTrue(book.certified_stop("a", delta=0.5))
        self.assertFalse(book.certified_stop("a", delta=1.0))

    def test_computation_selection_trace_is_scope_and_cost_checked(self):
        scope = kernel.HorizonScope("s", 1, 3, "lambda")
        trace = kernel.ComputationSelectionTrace(
            scope=scope,
            candidate_computations=("exact-search", "probe"),
            selected_computation="probe",
            rejected_computations=("exact-search",),
            complete_cost=1.25,
            rationale="lower complete cost",
        )
        book = kernel.SoundBoundBook(scope=scope, actions=("a",))
        book.record_computation_selection(trace)
        self.assertEqual(book.traces, (trace,))
        with self.assertRaises(kernel.HorizonKernelError):
            kernel.ComputationSelectionTrace(scope, ("x", "y"), "x", (), 0.0, "bad rejected set")


if __name__ == "__main__":
    unittest.main()
