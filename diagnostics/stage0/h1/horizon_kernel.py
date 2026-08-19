from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


class EvidenceKind(str, Enum):
    SOUND = "SOUND"
    ANYTIME_CALIBRATED = "ANYTIME_CALIBRATED"
    FIXED_SAMPLE_CALIBRATED = "FIXED_SAMPLE_CALIBRATED"
    HEURISTIC_ONLY = "HEURISTIC_ONLY"


class BoundError(ValueError):
    pass


class BoundContradiction(BoundError):
    pass


@dataclass(frozen=True)
class BoundScope:
    state_id: str
    action_id: str
    horizon: int
    budget: int
    semantic_version: str

    def __post_init__(self) -> None:
        if not self.state_id or not self.action_id or not self.semantic_version:
            raise BoundError("state/action/semantic_version must be non-empty")
        if self.horizon < 0:
            raise BoundError("horizon must be non-negative")
        if self.budget < 0:
            raise BoundError("budget must be non-negative")


@dataclass(frozen=True)
class HorizonBound:
    scope: BoundScope
    lower: float
    upper: float
    evidence_kind: EvidenceKind
    source_ids: Tuple[str, ...]
    dependency_source_set: Tuple[str, ...] = ()
    risk_alpha: Optional[float] = None
    joint_calibration_id: Optional[str] = None
    calibration_version: Optional[str] = None
    complete_computation_cost: float = 0.0
    provenance_receipt: Optional[str] = None

    def __post_init__(self) -> None:
        if not (isfinite(self.lower) and isfinite(self.upper)):
            raise BoundError("bounds must be finite")
        if self.lower > self.upper:
            raise BoundError("lower > upper")
        if not self.source_ids:
            raise BoundError("source_ids must be non-empty")
        if self.complete_computation_cost < 0:
            raise BoundError("negative computation cost")
        calibrated = self.evidence_kind in {EvidenceKind.ANYTIME_CALIBRATED, EvidenceKind.FIXED_SAMPLE_CALIBRATED}
        if calibrated:
            if self.risk_alpha is None or not (0.0 < self.risk_alpha < 1.0):
                raise BoundError("calibrated evidence requires 0 < risk_alpha < 1")
        elif self.risk_alpha is not None:
            raise BoundError("risk_alpha is only valid for calibrated evidence")


@dataclass(frozen=True)
class ComputationOption:
    computation_id: str
    candidate_action_id: str
    predicted_cost: float
    heuristic_score: Optional[float] = None

    def __post_init__(self) -> None:
        if self.predicted_cost < 0:
            raise BoundError("negative predicted computation cost")


@dataclass
class ComputationSelectionTrace:
    state_id: str
    horizon: int
    budget: int
    semantic_version: str
    options: Tuple[ComputationOption, ...]
    selected_computation_id: Optional[str]
    rejected_computation_ids: Tuple[str, ...]
    selector_version: str
    expected_bound_effect: Mapping[str, Tuple[float, float]] = field(default_factory=dict)
    realized_bound_effect: Mapping[str, Tuple[float, float]] = field(default_factory=dict)
    actual_cost: float = 0.0
    cumulative_effort_by_candidate: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        ids = {o.computation_id for o in self.options}
        if self.selected_computation_id is not None and self.selected_computation_id not in ids:
            raise BoundError("selected computation not in options")
        if any(x not in ids for x in self.rejected_computation_ids):
            raise BoundError("rejected computation not in options")
        if self.actual_cost < 0:
            raise BoundError("negative actual cost")


class BoundRegistry:
    """Revision-4 H1 kernel. Certified decision authority is SOUND-only."""

    def __init__(self) -> None:
        self._bounds: Dict[BoundScope, List[HorizonBound]] = {}
        self._selection_traces: List[ComputationSelectionTrace] = []

    def bounds(self, scope: BoundScope) -> Tuple[HorizonBound, ...]:
        return tuple(self._bounds.get(scope, ()))

    def register(self, bound: HorizonBound) -> None:
        current = list(self._bounds.get(bound.scope, ()))
        if bound.evidence_kind == EvidenceKind.SOUND:
            sound = [b for b in current if b.evidence_kind == EvidenceKind.SOUND]
            if sound:
                lo = max([b.lower for b in sound] + [bound.lower])
                hi = min([b.upper for b in sound] + [bound.upper])
                if lo > hi:
                    raise BoundContradiction(f"SOUND intersection empty for {bound.scope.action_id}: {lo} > {hi}")
        current.append(bound)
        self._bounds[bound.scope] = current

    def sound_interval(self, scope: BoundScope) -> Optional[Tuple[float, float]]:
        sound = [b for b in self._bounds.get(scope, ()) if b.evidence_kind == EvidenceKind.SOUND]
        if not sound:
            return None
        lo = max(b.lower for b in sound)
        hi = min(b.upper for b in sound)
        if lo > hi:
            raise BoundContradiction(f"stored SOUND contradiction for {scope}")
        return lo, hi

    def calibrated_sources_overlap(self, a: HorizonBound, b: HorizonBound) -> bool:
        return bool(set(a.dependency_source_set) & set(b.dependency_source_set))

    def calibrated_pair_jointly_certified(self, a: HorizonBound, b: HorizonBound) -> bool:
        calibrated = {EvidenceKind.ANYTIME_CALIBRATED, EvidenceKind.FIXED_SAMPLE_CALIBRATED}
        if a.evidence_kind not in calibrated or b.evidence_kind not in calibrated:
            return False
        return bool(a.joint_calibration_id and a.joint_calibration_id == b.joint_calibration_id)

    def certified_stop(self, *, state_id: str, action_ids: Sequence[str], horizon: int, budget: int, semantic_version: str, delta: float = 0.0) -> Optional[str]:
        if delta < 0:
            raise BoundError("delta must be non-negative")
        intervals: Dict[str, Tuple[float, float]] = {}
        for action_id in action_ids:
            scope = BoundScope(state_id, action_id, horizon, budget, semantic_version)
            interval = self.sound_interval(scope)
            if interval is None:
                return None
            intervals[action_id] = interval
        winners: List[str] = []
        for action_id, (lo, _hi) in intervals.items():
            rival_upper = max((intervals[b][1] for b in action_ids if b != action_id), default=float("-inf"))
            if lo > rival_upper + delta:
                winners.append(action_id)
        if len(winners) > 1:
            raise BoundContradiction(f"multiple certified winners: {winners}")
        return winners[0] if winners else None

    def record_computation_selection(self, trace: ComputationSelectionTrace) -> None:
        self._selection_traces.append(trace)

    def selection_traces(self) -> Tuple[ComputationSelectionTrace, ...]:
        return tuple(self._selection_traces)

    def total_metalevel_cost(self) -> float:
        return sum(t.actual_cost for t in self._selection_traces)

    def heuristic_select(self, *, state_id: str, horizon: int, budget: int, semantic_version: str, options: Iterable[ComputationOption], selector_version: str = "HEURISTIC_MAX_SCORE_V0") -> ComputationSelectionTrace:
        options_t = tuple(options)
        if not options_t:
            trace = ComputationSelectionTrace(state_id, horizon, budget, semantic_version, (), None, (), selector_version)
            self.record_computation_selection(trace)
            return trace
        selected = max(options_t, key=lambda o: (float("-inf") if o.heuristic_score is None else o.heuristic_score, -o.predicted_cost, o.computation_id))
        trace = ComputationSelectionTrace(
            state_id=state_id,
            horizon=horizon,
            budget=budget,
            semantic_version=semantic_version,
            options=options_t,
            selected_computation_id=selected.computation_id,
            rejected_computation_ids=tuple(o.computation_id for o in options_t if o.computation_id != selected.computation_id),
            selector_version=selector_version,
        )
        self.record_computation_selection(trace)
        return trace
