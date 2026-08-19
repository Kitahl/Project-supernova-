import unittest

from diagnostics.stage0.h0.oracle_worlds import build_worlds, qualification_oracle_receipt
from diagnostics.stage0.h1.horizon_kernel import BoundContradiction, BoundRegistry, BoundScope, ComputationOption, EvidenceKind, HorizonBound


class H0OracleTests(unittest.TestCase):
    def test_all_exact_oracles_match_frozen_expected_values(self):
        receipt = qualification_oracle_receipt()
        self.assertEqual(receipt["status"], "PASS", receipt)

    def test_zero_rho_chain_is_valuable(self):
        w = build_worlds()["ACYCLIC_ZERO_RHO"]
        self.assertEqual(w.metadata["pairwise_projection_spectral_radius"], 0.0)
        self.assertEqual(w.first_action_values()["chain"], 10.0)
        self.assertGreater(w.first_action_values()["chain"], w.first_action_values()["distract"])

    def test_mult_parent_fixture_requires_full_horizon(self):
        w = build_worlds()["MULTI_PARENT"]
        self.assertEqual(w.v_star(w.start_state, 2, 2), 0.0)
        self.assertEqual(w.v_star(w.start_state, 3, 3), 12.0)


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

    def test_metalevel_cost_is_charged(self):
        reg = BoundRegistry()
        trace = reg.heuristic_select(state_id="s", horizon=1, budget=3, semantic_version="v1", options=[ComputationOption("p1", "A", 0.25, 2.0)])
        trace.actual_cost = 0.4
        self.assertAlmostEqual(reg.total_metalevel_cost(), 0.4)

if __name__ == "__main__":
    unittest.main()
