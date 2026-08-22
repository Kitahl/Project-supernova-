import math
import unittest

from diagnostics.stage0.h0.oracle_worlds import build_worlds, qualification_oracle_receipt
from diagnostics.stage0.h1.horizon_kernel import BoundContradiction, BoundError, BoundRegistry, BoundScope, ComputationOption, EvidenceKind, HorizonBound


class H0OracleTests(unittest.TestCase):
    def test_all_exact_oracles_match_frozen_expected_values(self):
        receipt = qualification_oracle_receipt()
        self.assertEqual(receipt["status"], "PASS", receipt)
        self.assertEqual(len(receipt["worlds"]), 10)

    def test_zero_rho_chain_is_valuable(self):
        w = build_worlds()["ACYCLIC_ZERO_RHO"]
        self.assertEqual(w.metadata["pairwise_projection_spectral_radius"], 0.0)
        self.assertEqual(w.first_action_values()["chain"], 10.0)
        self.assertGreater(w.first_action_values()["chain"], w.first_action_values()["distract"])

    def test_mult_parent_fixture_requires_full_horizon(self):
        w = build_worlds()["MULTI_PARENT"]
        self.assertEqual(w.v_star(w.start_state, 2, 2), 0.0)
        self.assertEqual(w.v_star(w.start_state, 3, 3), 12.0)

    def test_expensive_optimal_beats_cheap_distractor_under_exact_budget(self):
        w = build_worlds()["EXPENSIVE_OPTIMAL"]
        values = w.first_action_values()
        self.assertEqual(values["expensive"], 20.0)
        self.assertEqual(values["cheap"], 5.0)
        self.assertEqual(w.best_first_action(), "expensive")


class H1SoundKernelTests(unittest.TestCase):
    def test_exact_sound_bounds_never_miss_oracle_and_certified_stop_is_correct(self):
        checked = 0
        for w in build_worlds().values():
            values = w.first_action_values()
            reg = BoundRegistry()
            for action_id, q in values.items():
                scope = BoundScope(w.start_state, action_id, w.horizon, w.budget, w.semantic_version)
                reg.register(HorizonBound(scope, q, q, EvidenceKind.SOUND, (f"exact:{w.world_id}:{action_id}",)))
                lo, hi = reg.sound_interval(scope)
                self.assertLessEqual(lo, q)
                self.assertGreaterEqual(hi, q)
                checked += 1
            winner = reg.certified_stop(state_id=w.start_state, action_ids=tuple(values), horizon=w.horizon, budget=w.budget, semantic_version=w.semantic_version)
            expected = w.best_first_action()
            self.assertEqual(winner, expected)
        self.assertGreaterEqual(checked, 20)

    def test_contradictory_sound_bounds_raise(self):
        w = build_worlds()["CONTRADICTORY_SOUND"]
        reg = BoundRegistry()
        s = BoundScope(w.start_state, "A", w.horizon, w.budget, w.semantic_version)
        reg.register(HorizonBound(s, 3.5, 4.5, EvidenceKind.SOUND, ("sound1",)))
        with self.assertRaises(BoundContradiction):
            reg.register(HorizonBound(s, 5.0, 6.0, EvidenceKind.SOUND, ("sound2",)))

    def test_calibrated_only_cannot_certify_sound_stop(self):
        w = build_worlds()["CORRELATED_CALIBRATED"]
        reg = BoundRegistry()
        for action_id, q in w.first_action_values().items():
            reg.register(HorizonBound(BoundScope(w.start_state, action_id, w.horizon, w.budget, w.semantic_version), q - 0.5, q + 0.5, EvidenceKind.ANYTIME_CALIBRATED, (f"cal:{action_id}",), ("shared_train",), 0.05))
        self.assertIsNone(reg.certified_stop(state_id=w.start_state, action_ids=("A", "B"), horizon=w.horizon, budget=w.budget, semantic_version=w.semantic_version))

    def test_overlapping_calibrated_sources_not_independent_by_default(self):
        reg = BoundRegistry(); s = BoundScope("s", "A", 1, 1, "v1")
        a = HorizonBound(s, 0, 2, EvidenceKind.ANYTIME_CALIBRATED, ("a",), ("shared",), 0.05)
        b = HorizonBound(s, 0.5, 1.5, EvidenceKind.FIXED_SAMPLE_CALIBRATED, ("b",), ("shared",), 0.05)
        self.assertTrue(reg.calibrated_sources_overlap(a, b))
        self.assertFalse(reg.calibrated_pair_jointly_certified(a, b))

    def test_joint_calibration_id_is_explicit(self):
        reg = BoundRegistry(); s = BoundScope("s", "A", 1, 1, "v1")
        a = HorizonBound(s, 0, 2, EvidenceKind.ANYTIME_CALIBRATED, ("a",), ("shared",), 0.05, "joint-1")
        b = HorizonBound(s, 0.5, 1.5, EvidenceKind.FIXED_SAMPLE_CALIBRATED, ("b",), ("shared",), 0.05, "joint-1")
        self.assertTrue(reg.calibrated_pair_jointly_certified(a, b))

    def test_interval_widening_is_legal_but_noncertifying_in_sound_only_h1(self):
        w = build_worlds()["INTERVAL_WIDENING"]
        reg = BoundRegistry()
        scope = BoundScope(w.start_state, "A", w.horizon, w.budget, w.semantic_version)
        updates = w.metadata["calibrated_updates"]["A"]
        reg.register(HorizonBound(scope, updates[0][0], updates[0][1], EvidenceKind.ANYTIME_CALIBRATED, ("cal-a-1",), ("shared",), 0.05))
        reg.register(HorizonBound(scope, updates[1][0], updates[1][1], EvidenceKind.ANYTIME_CALIBRATED, ("cal-a-2",), ("shared",), 0.05))
        self.assertGreater(updates[1][1] - updates[1][0], updates[0][1] - updates[0][0])
        self.assertIsNone(reg.sound_interval(scope))
        self.assertIsNone(reg.certified_stop(state_id=w.start_state, action_ids=("A", "B"), horizon=w.horizon, budget=w.budget, semantic_version=w.semantic_version))

    def test_stale_semantic_version_does_not_certify_current_scope(self):
        w = build_worlds()["SEMANTIC_EXPIRY"]
        reg = BoundRegistry()
        for action_id, q in w.first_action_values().items():
            reg.register(HorizonBound(BoundScope(w.start_state, action_id, w.horizon, w.budget, "v1"), q, q, EvidenceKind.SOUND, (f"stale:{action_id}",)))
        self.assertIsNone(reg.certified_stop(state_id=w.start_state, action_ids=("A", "B"), horizon=w.horizon, budget=w.budget, semantic_version="v2"))

    def test_heuristic_allocation_never_narrows_certifying_interval(self):
        w = build_worlds()["UNEQUAL_HEURISTIC_ALLOCATION"]
        reg = BoundRegistry()
        options = [ComputationOption(f"probe-{a}", a, 1.0, score) for a, score in w.metadata["heuristic_scores"].items()]
        trace = reg.heuristic_select(state_id=w.start_state, horizon=w.horizon, budget=w.budget, semantic_version=w.semantic_version, options=options)
        self.assertEqual(trace.selected_computation_id, "probe-C")
        self.assertIsNone(reg.certified_stop(state_id=w.start_state, action_ids=("A", "B", "C"), horizon=w.horizon, budget=w.budget, semantic_version=w.semantic_version))

    def test_registered_heuristic_bound_does_not_change_sound_interval(self):
        reg = BoundRegistry(); scope = BoundScope("s", "A", 1, 1, "v1")
        reg.register(HorizonBound(scope, 0.0, 10.0, EvidenceKind.SOUND, ("sound",)))
        before = reg.sound_interval(scope)
        reg.register(HorizonBound(scope, 4.9, 5.1, EvidenceKind.HEURISTIC_ONLY, ("heuristic",)))
        self.assertEqual(reg.sound_interval(scope), before)

    def test_metalevel_cost_is_charged(self):
        reg = BoundRegistry()
        trace = reg.heuristic_select(state_id="s", horizon=1, budget=3, semantic_version="v1", options=[ComputationOption("p1", "A", 0.25, 2.0)])
        trace.actual_cost = 0.4
        self.assertAlmostEqual(reg.total_metalevel_cost(), 0.4)

    def test_nonfinite_reversed_and_negative_cost_inputs_fail_closed(self):
        s = BoundScope("s", "A", 1, 1, "v1")
        with self.assertRaises(BoundError):
            HorizonBound(s, 2.0, 1.0, EvidenceKind.SOUND, ("x",))
        with self.assertRaises(BoundError):
            HorizonBound(s, math.nan, 1.0, EvidenceKind.SOUND, ("x",))
        with self.assertRaises(BoundError):
            ComputationOption("p", "A", -0.1, 1.0)

    def test_certified_stop_uses_strict_margin(self):
        reg = BoundRegistry()
        for action_id, value in (("A", 2.0), ("B", 1.0)):
            reg.register(HorizonBound(BoundScope("s", action_id, 1, 1, "v1"), value, value, EvidenceKind.SOUND, (action_id,)))
        self.assertEqual(reg.certified_stop(state_id="s", action_ids=("A", "B"), horizon=1, budget=1, semantic_version="v1", delta=0.5), "A")
        self.assertIsNone(reg.certified_stop(state_id="s", action_ids=("A", "B"), horizon=1, budget=1, semantic_version="v1", delta=1.0))


if __name__ == "__main__":
    unittest.main()
