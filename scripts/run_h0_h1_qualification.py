#!/usr/bin/env python3
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagnostics.stage0.h0.oracle_worlds import build_worlds, qualification_oracle_receipt
from diagnostics.stage0.h1.horizon_kernel import BoundRegistry, BoundScope, EvidenceKind, HorizonBound


def main():
    oracle = qualification_oracle_receipt()
    sound_violations = []
    incorrect_stops = []
    total_bounds = 0
    for w in build_worlds().values():
        values = w.first_action_values()
        reg = BoundRegistry()
        for action_id, q in values.items():
            scope = BoundScope(w.start_state, action_id, w.horizon, w.budget, w.semantic_version)
            reg.register(HorizonBound(scope, q, q, EvidenceKind.SOUND, (f"exact:{w.world_id}:{action_id}",)))
            lo, hi = reg.sound_interval(scope)
            total_bounds += 1
            if not (lo <= q <= hi):
                sound_violations.append({"world": w.world_id, "action": action_id, "q": q, "bound": [lo, hi]})
        got = reg.certified_stop(state_id=w.start_state, action_ids=tuple(values), horizon=w.horizon, budget=w.budget, semantic_version=w.semantic_version)
        expected = w.best_first_action()
        if got != expected:
            incorrect_stops.append({"world": w.world_id, "expected": expected, "got": got})
    receipt = {
        "schema_version": "PS-H0-H1-QUALIFICATION-1",
        "execution_class": "SYNTHETIC_NON_ADMISSIBLE",
        "oracle_status": oracle["status"],
        "world_count": len(oracle["worlds"]),
        "sound_bound_count": total_bounds,
        "sound_containment_violations": sound_violations,
        "incorrect_certified_stops": incorrect_stops,
        "status": "PASS" if oracle["status"] == "PASS" and not sound_violations and not incorrect_stops else "FAIL",
        "scientific_status_changed": False,
        "protocol_changed": False,
        "revision_changed": False,
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
