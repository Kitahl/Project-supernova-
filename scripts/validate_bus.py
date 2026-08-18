#!/usr/bin/env python3
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ERRORS = []

FORBIDDEN_PUBLIC_KEYS = {
    "hidden_task_name", "hidden_task_id", "protected_task_id", "benchmark_item_id",
    "raw_hidden_prompt", "private_manifest_payload", "secret", "credential", "api_key"
}
TEST_ID_PATTERN = re.compile(r"\bTEST-\d{3}\b", re.IGNORECASE)
EXPECTED_WORKERS = {"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}


def err(path, msg):
    ERRORS.append(f"{path}: {msg}")


def walk_keys(obj, path, filename):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in FORBIDDEN_PUBLIC_KEYS:
                err(filename, f"forbidden public key: {k}")
            walk_keys(v, path + [k], filename)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_keys(v, path + [str(i)], filename)
    elif isinstance(obj, str):
        if TEST_ID_PATTERN.search(obj):
            err(filename, "raw TEST-NNN identifier forbidden in public bus")


def load_json(path):
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        err(path.relative_to(ROOT), f"invalid JSON: {e}")
        return None
    walk_keys(obj, [], str(path.relative_to(ROOT)))
    return obj


for p in ROOT.rglob("*.json"):
    if ".git" in p.parts:
        continue
    load_json(p)

state_path = ROOT / "state" / "CURRENT.json"
state = load_json(state_path) if state_path.exists() else None
if state:
    for key in ["task_network_plan_id","runtime_state_id","accepted_network_checkpoint_id","network_mode","active_cohort_id","active_assignment_path"]:
        if not state.get(key): err("state/CURRENT.json", f"missing {key}")
    assignment = ROOT / state.get("active_assignment_path", "")
    if not assignment.exists():
        err("state/CURRENT.json", "active_assignment_path does not exist")
    else:
        a = load_json(assignment)
        if a:
            if a.get("cohort_id") != state.get("active_cohort_id"): err(assignment.relative_to(ROOT), "cohort != state active_cohort_id")
            if a.get("task_network_plan_id") != state.get("task_network_plan_id"): err(assignment.relative_to(ROOT), "plan ID mismatch")
            if a.get("runtime_state_id") != state.get("runtime_state_id"): err(assignment.relative_to(ROOT), "runtime ID mismatch")
            if set(a.get("workers",{})) != EXPECTED_WORKERS: err(assignment.relative_to(ROOT), "worker set mismatch")
            if a.get("network_mode") == "GITHUB_BUS_CALIBRATION":
                for wid, w in a.get("workers",{}).items():
                    if w.get("fresh_allowed") is not False: err(assignment.relative_to(ROOT), f"{wid} fresh_allowed during calibration")
                    if w.get("opaque_evidence_ids") not in ([], None): err(assignment.relative_to(ROOT), f"{wid} evidence assigned during calibration")
                    if w.get("private_manifest_id") is not None: err(assignment.relative_to(ROOT), f"{wid} private manifest during calibration")

for p in (ROOT / "reports").rglob("*.json") if (ROOT / "reports").exists() else []:
    r = load_json(p)
    if not r: continue
    if r.get("worker_id") not in EXPECTED_WORKERS: err(p.relative_to(ROOT), "unknown worker_id")
    if r.get("mode") == "GITHUB_BUS_CALIBRATION" and r.get("fresh_evidence_ids"): err(p.relative_to(ROOT), "fresh evidence in calibration report")

if ERRORS:
    print("BUS VALIDATION FAILED")
    for e in ERRORS: print("-", e)
    sys.exit(1)
print("BUS VALIDATION PASS")
