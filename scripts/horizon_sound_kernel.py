#!/usr/bin/env python3
"""Non-authoritative H1 SOUND-only finite-horizon interval kernel.

Revision-4 engineering/qualification code only. This module does not execute
mathematics, admit science, mutate canonical state, or turn calibrated/heuristic
outputs into certifying evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Iterable


class EvidenceKind(str, Enum):
    SOUND = "SOUND"
    ANYTIME_CALIBRATED = "ANYTIME_CALIBRATED"
    FIXED_SAMPLE_CALIBRATED = "FIXED_SAMPLE_CALIBRATED"
    HEURISTIC_ONLY = "HEURISTIC_ONLY"


class HorizonKernelError(ValueError):
    pass


class ScopeMismatch(HorizonKernelError):
    pass


class BoundContradiction(HorizonKernelError):
    pass


class MissingSoundBound(HorizonKernelError):
    pass


@dataclass(frozen=True)
class HorizonScope:
    state_id: str
    horizon: int
    budget: int
    semantic_version: str

    def __post_init__(self) -> None:
        if not self.state_id:
            raise HorizonKernelError("state_id must be non-empty")
        if self.horizon < 0:
            raise HorizonKernelError("horizon must be non-negative")
        if self.budget < 0:
            raise HorizonKernelError("budget must be non-negative")
        if not self.semantic_version:
            raise HorizonKernelError("semantic_version must be non-empty")


@dataclass(frozen=True)
class HorizonBound:
    scope: HorizonScope
    action_id: str
    lower: float
    upper: float
    evidence_kind: EvidenceKind
    source_id: str
    provenance_ref: str

    def __post_init__(self) -> None:
        if not self.action_id:
            raise HorizonKernelError("action_id must be non-empty")
        if not self.source_id:
            raise HorizonKernelError("source_id must be non-empty")
        if not self.provenance_ref:
            raise HorizonKernelError("provenance_ref must be non-empty")
        if not math.isfinite(self.lower) or not math.isfinite(self.upper):
            raise HorizonKernelError("bounds must be finite")
        if self.lower > self.upper:
            raise HorizonKernelError("lower must not exceed upper")


@dataclass(frozen=True)
class SoundInterval:
    lower: float
    upper: float
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class ComputationSelectionTrace:
    scope: HorizonScope
    candidate_computations: tuple[str, ...]
    selected_computation: str
    rejected_computations: tuple[str, ...]
    complete_cost: float
    rationale: str

    def __post_init__(self) -> None:
        if not self.candidate_computations:
            raise HorizonKernelError("candidate_computations must be non-empty")
        if self.selected_computation not in self.candidate_computations:
            raise HorizonKernelError("selected computation must be in candidate set")
        if self.complete_cost < 0 or not math.isfinite(self.complete_cost):
            raise HorizonKernelError("complete_cost must be finite and non-negative")
        expected_rejected = set(self.candidate_computations) - {self.selected_computation}
        if set(self.rejected_computations) != expected_rejected:
            raise HorizonKernelError("rejected computations must equal candidates minus selected")


@dataclass
class SoundBoundBook:
    """Exact-scope registry whose certifying algebra uses SOUND evidence only."""

    scope: HorizonScope
    actions: tuple[str, ...]
    _bounds: dict[str, list[HorizonBound]] = field(default_factory=dict, init=False)
    _traces: list[ComputationSelectionTrace] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if not self.actions:
            raise HorizonKernelError("at least one action is required")
        if len(set(self.actions)) != len(self.actions):
            raise HorizonKernelError("actions must be unique")
        self._bounds = {action: [] for action in self.actions}

    def register(self, bound: HorizonBound) -> None:
        if bound.scope != self.scope:
            raise ScopeMismatch(f"bound scope {bound.scope!r} != book scope {self.scope!r}")
        if bound.action_id not in self._bounds:
            raise ScopeMismatch(f"unknown action: {bound.action_id}")
        self._bounds[bound.action_id].append(bound)
        # Detect contradictory SOUND evidence at registration time. Non-SOUND
        # evidence is retained for diagnostics/scheduling but cannot narrow a
        # certifying interval in this H1 qualification kernel.
        if bound.evidence_kind is EvidenceKind.SOUND:
            self.sound_interval(bound.action_id)

    def register_many(self, bounds: Iterable[HorizonBound]) -> None:
        for bound in bounds:
            self.register(bound)

    def sound_interval(self, action_id: str) -> SoundInterval:
        if action_id not in self._bounds:
            raise ScopeMismatch(f"unknown action: {action_id}")
        sound = [b for b in self._bounds[action_id] if b.evidence_kind is EvidenceKind.SOUND]
        if not sound:
            raise MissingSoundBound(f"no SOUND bound for action {action_id}")
        lower = max(b.lower for b in sound)
        upper = min(b.upper for b in sound)
        if lower > upper:
            raise BoundContradiction(
                f"BOUND_CONTRADICTION action={action_id} lower={lower} upper={upper}"
            )
        return SoundInterval(lower, upper, tuple(sorted(b.source_id for b in sound)))

    def certified_stop(self, candidate_action: str, delta: float = 0.0) -> bool:
        if delta < 0 or not math.isfinite(delta):
            raise HorizonKernelError("delta must be finite and non-negative")
        candidate = self.sound_interval(candidate_action)
        rivals = [a for a in self.actions if a != candidate_action]
        if not rivals:
            return True
        rival_upper = max(self.sound_interval(action).upper for action in rivals)
        return candidate.lower > rival_upper + delta

    def certified_winner(self, delta: float = 0.0) -> str | None:
        winners = [action for action in self.actions if self.certified_stop(action, delta)]
        if len(winners) > 1:
            raise BoundContradiction(f"multiple certified winners: {winners}")
        return winners[0] if winners else None

    def record_computation_selection(self, trace: ComputationSelectionTrace) -> None:
        if trace.scope != self.scope:
            raise ScopeMismatch("computation trace scope mismatch")
        self._traces.append(trace)

    @property
    def traces(self) -> tuple[ComputationSelectionTrace, ...]:
        return tuple(self._traces)

    def diagnostic_bounds(self, action_id: str) -> tuple[HorizonBound, ...]:
        """Return all evidence, including non-certifying calibrated/heuristic rows."""
        if action_id not in self._bounds:
            raise ScopeMismatch(f"unknown action: {action_id}")
        return tuple(self._bounds[action_id])
