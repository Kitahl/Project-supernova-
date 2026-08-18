#!/usr/bin/env python3
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ERRORS = []
EXPECTED_WORKERS = {"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
SEALED_SLOTS = {"SEALED_ORACLE_SLOT_A","SEALED_ORACLE_SLOT_B"}
FORBIDDEN_PUBLIC_KEYS = {
    "hidden_task_name","hidden_task_id","protected_task_id","benchmark_item_id",
    "raw_hidden_prompt","private_manifest_payload","private_manifest_content",
    "secret","credential","api_key","access_token","password"
}
TEST_ID_PATTERN = re.compile(r"\bTEST-\d{3}\b", re.IGNORECASE)
CI_VALUES = {"PASS","FAIL","PENDING","CI_NOT_OBSERVED"}
REQUIRED_CONTROL_FILES = {
    "PROTOCOL.md","WORKER_PROTOCOL.md","plan/PLAN.json","config/roles.json",
    "schemas/assignment.schema.json","schemas/report.schema.json",
    "schemas/verification.schema.json","schemas/integration.schema.json",
    "schemas/director.schema.json","schemas/research.schema.json",
    "scripts/validate_bus.py",".github/workflows/validate-bus.yml"
}

def err(path, msg):
    ERRORS.append(f"{path}: {msg}")

def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        err(path.relative_to(ROOT), f"invalid JSON: {e}")
        return None

def git_blob_sha(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def walk_public(obj, filename):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in FORBIDDEN_PUBLIC_KEYS:
                err(filename, f"forbidden public key: {k}")
            walk_public(v, filename)
    elif isinstance(obj, list):
        for v in obj:
            walk_public(v, filename)
    elif isinstance(obj, str) and TEST_ID_PATTERN.search(obj):
        err(filename, "raw TEST-NNN identifier forbidden in public bus")

for p in ROOT.rglob("*.json"):
    if ".git" in p.parts:
        continue
    obj = load_json(p)
    if obj is not None:
        walk_public(obj, str(p.relative_to(ROOT)))

superseded = set()
supdir = ROOT / "superseded"
if supdir.exists():
    for p in supdir.glob("*.json"):
        s = load_json(p)
        if s and s.get("cohort_id"):
            superseded.add(s["cohort_id"])

state_path = ROOT / "state" / "CURRENT.json"
plan_path = ROOT / "plan" / "PLAN.json"
state = load_json(state_path) if state_path.exists() else None
plan = load_json(plan_path) if plan_path.exists() else None

if not state:
    err("state/CURRENT.json", "missing/unreadable state")
if not plan:
    err("plan/PLAN.json", "missing/unreadable plan")

if state and plan:
    pid = state.get("task_network_plan_id")
    if plan.get("task_network_plan_id") != pid:
        err("plan/PLAN.json", "plan ID != state plan ID")
    if state.get("protocol_version") != plan.get("protocol_version"):
        err("state/CURRENT.json", "protocol_version != plan")
    for key in ["runtime_state_id","accepted_network_checkpoint_id","network_mode",
                "active_cohort_id","active_assignment_path","active_assignment_git_identity",
                "active_control_manifest_path","active_control_manifest_git_identity"]:
        if not state.get(key):
            err("state/CURRENT.json", f"missing {key}")
    if state.get("active_cohort_id") in superseded:
        err("state/CURRENT.json", "active cohort is superseded")
    if state.get("fresh_allowed_globally") and state.get("network_mode") != "FRESH_ENABLED":
        err("state/CURRENT.json", "fresh_allowed_globally outside FRESH_ENABLED")
    if state.get("deep_research_owner") != "BIL00":
        err("state/CURRENT.json", "deep_research_owner must be BIL00")
    if state.get("deep_research_times_vancouver") != ["00:58","12:58"]:
        err("state/CURRENT.json", "deep research schedule must be exactly 00:58 and 12:58 Vancouver")

    control_path = ROOT / state.get("active_control_manifest_path","")
    assignment_path = ROOT / state.get("active_assignment_path","")
    control = load_json(control_path) if control_path.exists() else None
    assignment = load_json(assignment_path) if assignment_path.exists() else None

    if not control:
        err("state/CURRENT.json", "active control manifest missing/unreadable")
    else:
        if git_blob_sha(control_path) != state.get("active_control_manifest_git_identity"):
            err(control_path.relative_to(ROOT), "control manifest blob != state identity")
        if control.get("cohort_id") != state.get("active_cohort_id"):
            err(control_path.relative_to(ROOT), "control cohort != state active cohort")
        if control.get("task_network_plan_id") != pid:
            err(control_path.relative_to(ROOT), "control plan ID mismatch")
        files = control.get("files", {})
        if set(files) != REQUIRED_CONTROL_FILES:
            err(control_path.relative_to(ROOT), "control file set mismatch")
        for rel, expected_sha in files.items():
            fp = ROOT / rel
            if not fp.exists():
                err(control_path.relative_to(ROOT), f"frozen file missing: {rel}")
            elif git_blob_sha(fp) != expected_sha:
                err(control_path.relative_to(ROOT), f"frozen file drift: {rel}")

    if not assignment:
        err("state/CURRENT.json", "active assignment missing/unreadable")
    else:
        if git_blob_sha(assignment_path) != state.get("active_assignment_git_identity"):
            err(assignment_path.relative_to(ROOT), "assignment blob != state identity")
        for k, sv in [
            ("cohort_id", state.get("active_cohort_id")),
            ("task_network_plan_id", pid),
            ("network_checkpoint_id", state.get("accepted_network_checkpoint_id")),
            ("runtime_state_id", state.get("runtime_state_id")),
            ("network_mode", state.get("network_mode")),
            ("control_manifest_path", state.get("active_control_manifest_path")),
            ("control_manifest_git_identity", state.get("active_control_manifest_git_identity"))
        ]:
            if assignment.get(k) != sv:
                err(assignment_path.relative_to(ROOT), f"{k} mismatch with state")
        if control and assignment.get("control_manifest_id") != control.get("control_manifest_id"):
            err(assignment_path.relative_to(ROOT), "control_manifest_id mismatch")
        if set(assignment.get("workers", {})) != EXPECTED_WORKERS:
            err(assignment_path.relative_to(ROOT), "worker set mismatch")
        if set(assignment.get("sealed_slots", [])) != SEALED_SLOTS:
            err(assignment_path.relative_to(ROOT), "sealed slot set mismatch")
        if assignment.get("network_mode") == "GITHUB_BUS_CALIBRATION":
            for wid, w in assignment.get("workers", {}).items():
                if w.get("fresh_allowed") is not False:
                    err(assignment_path.relative_to(ROOT), f"{wid} fresh_allowed during calibration")
                if w.get("opaque_evidence_ids") != []:
                    err(assignment_path.relative_to(ROOT), f"{wid} evidence assigned during calibration")
                if w.get("private_manifest_id") is not None or w.get("private_manifest_git_identity") is not None:
                    err(assignment_path.relative_to(ROOT), f"{wid} private manifest during calibration")

reports_root = ROOT / "reports"
if reports_root.exists():
    for p in reports_root.rglob("*.json"):
        r = load_json(p)
        if not r:
            continue
        cohort = r.get("cohort_id")
        if cohort in superseded:
            continue
        worker = r.get("worker_id")
        if worker not in EXPECTED_WORKERS:
            err(p.relative_to(ROOT), "unknown worker_id")
            continue
        if p.stem != worker or p.parent.name != cohort:
            err(p.relative_to(ROOT), "path does not match cohort/worker fields")
        ap = ROOT / "assignments" / f"{cohort}.json"
        if not ap.exists():
            err(p.relative_to(ROOT), "cohort assignment missing")
            continue
        a = load_json(ap)
        cp = ROOT / a.get("control_manifest_path","") if a else None
        c = load_json(cp) if cp and cp.exists() else None
        if not a or not c:
            err(p.relative_to(ROOT), "assignment/control missing or unreadable")
            continue
        required = [
            "task_network_plan_id","cohort_id","worker_id","report_id","assignment_id",
            "assignment_git_identity","control_manifest_id","control_manifest_git_identity",
            "network_checkpoint_id","runtime_state_id","visibility_token","status","mode",
            "evidence_tier","fresh_evidence_ids","private_manifest_id","private_manifest_git_identity",
            "source_version_ids","claim_scope","runtime_implementation_implication","next_action",
            "negative_zero_outcomes","research_questions","cost_ledger","public_safety_status",
            "git_reread_verified","ci_status"
        ]
        for k in required:
            if k not in r:
                err(p.relative_to(ROOT), f"missing required report field {k}")
        checks = {
            "task_network_plan_id": a.get("task_network_plan_id"),
            "cohort_id": a.get("cohort_id"),
            "assignment_id": a.get("assignment_id"),
            "assignment_git_identity": git_blob_sha(ap),
            "control_manifest_id": a.get("control_manifest_id"),
            "control_manifest_git_identity": a.get("control_manifest_git_identity"),
            "network_checkpoint_id": a.get("network_checkpoint_id"),
            "runtime_state_id": a.get("runtime_state_id"),
            "visibility_token": a.get("workers",{}).get(worker,{}).get("visibility_token")
        }
        for k, v in checks.items():
            if r.get(k) != v:
                err(p.relative_to(ROOT), f"{k} mismatch")
        if r.get("status") != "VALID_ASSIGNED_REPORT":
            err(p.relative_to(ROOT), "nonstandard status")
        if r.get("mode") not in {"SAFE_REPLAY_ONLY","FRESH_EXECUTION"}:
            err(p.relative_to(ROOT), "nonstandard mode")
        if r.get("public_safety_status") != "PASS":
            err(p.relative_to(ROOT), "public_safety_status != PASS")
        if r.get("git_reread_verified") is not True:
            err(p.relative_to(ROOT), "git_reread_verified != true")
        if r.get("ci_status") not in CI_VALUES:
            err(p.relative_to(ROOT), "invalid ci_status")
        ledger = r.get("cost_ledger",{})
        for k in ["fresh_evidence_units_consumed","protected_manifest_reads","benchmark_executions","deep_research_runs"]:
            if not isinstance(ledger.get(k), int) or ledger.get(k) < 0:
                err(p.relative_to(ROOT), f"invalid cost ledger {k}")
        if ledger.get("deep_research_runs") != 0:
            err(p.relative_to(ROOT), "worker performed deep research")
        if a.get("network_mode") == "GITHUB_BUS_CALIBRATION":
            if r.get("mode") != "SAFE_REPLAY_ONLY":
                err(p.relative_to(ROOT), "calibration report not SAFE_REPLAY_ONLY")
            if r.get("fresh_evidence_ids") != []:
                err(p.relative_to(ROOT), "fresh evidence in calibration")
            if r.get("private_manifest_id") is not None or r.get("private_manifest_git_identity") is not None:
                err(p.relative_to(ROOT), "private manifest read/claimed in calibration")
            if ledger.get("fresh_evidence_units_consumed") != 0 or ledger.get("protected_manifest_reads") != 0 or ledger.get("benchmark_executions") != 0:
                err(p.relative_to(ROOT), "nonzero protected/fresh cost during calibration")

for cohort in superseded:
    dp = ROOT / "director" / f"{cohort}.json"
    if dp.exists():
        d = load_json(dp)
        if d and d.get("calibration_counted"):
            err(dp.relative_to(ROOT), "superseded cohort counted for calibration")

if ERRORS:
    print("BUS VALIDATION FAILED")
    for e in ERRORS:
        print("-", e)
    sys.exit(1)
print("BUS VALIDATION PASS")
