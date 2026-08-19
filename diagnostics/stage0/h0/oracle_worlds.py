from __future__ import annotations

from dataclasses import dataclass, field
from math import inf
from typing import Any, Dict, Mapping, Tuple


@dataclass(frozen=True)
class Action:
    action_id: str
    next_state: str
    cost: int
    utility_delta: float = 0.0


@dataclass
class FiniteWorld:
    world_id: str
    start_state: str
    horizon: int
    budget: int
    semantic_version: str
    transitions: Mapping[str, Tuple[Action, ...]]
    terminal_utility: Mapping[str, float]
    expected_first_action_values: Mapping[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def actions(self, state: str) -> Tuple[Action, ...]:
        return tuple(self.transitions.get(state, ()))

    def stop_value(self, state: str) -> float:
        return float(self.terminal_utility.get(state, 0.0))

    def q_star(self, state: str, action: Action, horizon: int, budget: int) -> float:
        if action.cost > budget or horizon <= 0:
            return -inf
        return action.utility_delta + self.v_star(action.next_state, horizon - 1, budget - action.cost)

    def v_star(self, state: str, horizon: int, budget: int) -> float:
        cache: Dict[Tuple[str, int, int], float] = {}

        def solve(s: str, h: int, b: int) -> float:
            key = (s, h, b)
            if key in cache:
                return cache[key]
            best = self.stop_value(s)
            if h > 0 and b > 0:
                for action in self.actions(s):
                    if action.cost <= b:
                        best = max(best, action.utility_delta + solve(action.next_state, h - 1, b - action.cost))
            cache[key] = best
            return best

        return solve(state, horizon, budget)

    def first_action_values(self) -> Dict[str, float]:
        return {
            a.action_id: self.q_star(self.start_state, a, self.horizon, self.budget)
            for a in self.actions(self.start_state)
            if a.cost <= self.budget
        }

    def best_first_action(self) -> str | None:
        vals = self.first_action_values()
        if not vals:
            return None
        m = max(vals.values())
        winners = sorted(k for k, v in vals.items() if v == m)
        return winners[0] if len(winners) == 1 else None

    def verify_expected_oracle(self, tol: float = 1e-12) -> None:
        got = self.first_action_values()
        if set(got) != set(self.expected_first_action_values):
            raise AssertionError(f"{self.world_id}: action set mismatch {set(got)} != {set(self.expected_first_action_values)}")
        for action_id, expected in self.expected_first_action_values.items():
            actual = got[action_id]
            if abs(actual - expected) > tol:
                raise AssertionError(f"{self.world_id}:{action_id}: expected {expected}, got {actual}")


def A(action_id: str, next_state: str, cost: int, utility_delta: float = 0.0) -> Action:
    return Action(action_id, next_state, cost, utility_delta)


def build_worlds() -> Dict[str, FiniteWorld]:
    worlds: Dict[str, FiniteWorld] = {}
    worlds["ACYCLIC_ZERO_RHO"] = FiniteWorld(
        "ACYCLIC_ZERO_RHO", "s0", 3, 3, "v1",
        {"s0": (A("chain", "s1", 1), A("distract", "d", 1)), "s1": (A("chain_2", "s2", 1),), "s2": (A("chain_3", "goal", 1),)},
        {"goal": 10.0, "d": 2.0}, {"chain": 10.0, "distract": 2.0},
        {"pairwise_projection_spectral_radius": 0.0, "purpose": "valuable finite acyclic chain must survive spectral-zero case"},
    )
    worlds["CERTIFIED_DEAD"] = FiniteWorld(
        "CERTIFIED_DEAD", "s0", 2, 2, "v1",
        {"s0": (A("solve", "goal", 1), A("dead", "dead", 1))},
        {"goal": 5.0, "dead": 0.0}, {"solve": 5.0, "dead": 0.0}, {"certified_dead_actions": ["dead"]},
    )
    worlds["MULTI_PARENT"] = FiniteWorld(
        "MULTI_PARENT", "none", 3, 3, "v1",
        {"none": (A("make_p", "p", 1), A("make_q", "q", 1)), "p": (A("make_q_after_p", "pq", 1),), "q": (A("make_p_after_q", "pq", 1),), "pq": (A("consume_both", "goal", 1),)},
        {"goal": 12.0}, {"make_p": 12.0, "make_q": 12.0}, {"hyperedge": ["p", "q"], "consumer": "consume_both"},
    )
    worlds["EXPENSIVE_OPTIMAL"] = FiniteWorld(
        "EXPENSIVE_OPTIMAL", "s0", 1, 4, "v1", {"s0": (A("expensive", "good", 4), A("cheap", "cheap_goal", 1))},
        {"good": 20.0, "cheap_goal": 5.0}, {"expensive": 20.0, "cheap": 5.0}, {"purpose": "budgeted exact oracle keeps expensive optimum"},
    )
    worlds["MISLEADING_LOW_FIDELITY"] = FiniteWorld(
        "MISLEADING_LOW_FIDELITY", "s0", 1, 2, "v1", {"s0": (A("A", "A_goal", 2), A("B", "B_goal", 2))},
        {"A_goal": 11.0, "B_goal": 7.0}, {"A": 11.0, "B": 7.0}, {"low_fidelity_scores": {"A": 0.2, "B": 0.9}},
    )
    worlds["CORRELATED_CALIBRATED"] = FiniteWorld(
        "CORRELATED_CALIBRATED", "s0", 1, 1, "v1", {"s0": (A("A", "A_goal", 1), A("B", "B_goal", 1))},
        {"A_goal": 10.0, "B_goal": 8.0}, {"A": 10.0, "B": 8.0},
        {"calibrated_estimators": [{"source_id": "est1", "dependency_source_set": ["shared_train"]}, {"source_id": "est2", "dependency_source_set": ["shared_train"]}]},
    )
    worlds["INTERVAL_WIDENING"] = FiniteWorld(
        "INTERVAL_WIDENING", "s0", 1, 1, "v1", {"s0": (A("A", "A_goal", 1), A("B", "B_goal", 1))},
        {"A_goal": 9.0, "B_goal": 8.0}, {"A": 9.0, "B": 8.0}, {"calibrated_updates": {"A": [[8.5, 9.5], [8.0, 10.0]]}},
    )
    worlds["SEMANTIC_EXPIRY"] = FiniteWorld(
        "SEMANTIC_EXPIRY", "s0", 1, 1, "v2", {"s0": (A("A", "A_goal", 1), A("B", "B_goal", 1))},
        {"A_goal": 7.0, "B_goal": 6.0}, {"A": 7.0, "B": 6.0}, {"stale_bound_semantic_version": "v1"},
    )
    worlds["CONTRADICTORY_SOUND"] = FiniteWorld(
        "CONTRADICTORY_SOUND", "s0", 1, 1, "v1", {"s0": (A("A", "A_goal", 1), A("B", "B_goal", 1))},
        {"A_goal": 4.0, "B_goal": 3.0}, {"A": 4.0, "B": 3.0}, {"contradictory_sound_bounds_for_A": [[3.5, 4.5], [5.0, 6.0]]},
    )
    worlds["UNEQUAL_HEURISTIC_ALLOCATION"] = FiniteWorld(
        "UNEQUAL_HEURISTIC_ALLOCATION", "s0", 1, 1, "v1", {"s0": (A("A", "A_goal", 1), A("B", "B_goal", 1), A("C", "C_goal", 1))},
        {"A_goal": 10.0, "B_goal": 9.0, "C_goal": 8.0}, {"A": 10.0, "B": 9.0, "C": 8.0}, {"heuristic_scores": {"A": 1.0, "B": 2.0, "C": 100.0}},
    )
    return worlds


def qualification_oracle_receipt() -> Dict[str, Any]:
    worlds = build_worlds()
    out: Dict[str, Any] = {"worlds": {}, "violations": []}
    for world_id, world in worlds.items():
        try:
            world.verify_expected_oracle()
            out["worlds"][world_id] = {"status": "PASS", "first_action_values": world.first_action_values(), "best_first_action": world.best_first_action(), "horizon": world.horizon, "budget": world.budget, "semantic_version": world.semantic_version}
        except Exception as exc:
            out["worlds"][world_id] = {"status": "FAIL", "error": str(exc)}
            out["violations"].append({"world": world_id, "error": str(exc)})
    out["status"] = "PASS" if not out["violations"] else "FAIL"
    return out
