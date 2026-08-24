#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import strict_json

REPO = os.environ.get("GITHUB_REPOSITORY", "Kitahl/Project-supernova-")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/" + REPO
OWNER = REPO.split("/", 1)[0]
PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
BOOTSTRAP_CONTEXT = "supernova/bootstrap-admission"
BOOTSTRAP_CREATOR = "github-actions[bot]"
REQUIRED_CONTEXTS = ["supernova/static-control", "supernova/report-admission", "supernova/transition-admission"]
HEX40 = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_HEAD_PREFIXES = ("hardening/", "rev4/", "root-rotation/")
ALLOWED_PREFIXES = ("config/", "schemas/", "scripts/", "tests/", ".github/workflows/", "docs/")
ALLOWED_EXACT = {"PROTOCOL.md", "WORKER_PROTOCOL.md", "BRANCH_PROTOCOL.md", "BRANCH_WORKER_PROTOCOL.md", "SESSION_STANDARD.md", "plan/PLAN.json", "requirements-validation.lock", "branch/CONFIG.json"}
FORBIDDEN_EXACT = {"state/CURRENT.json", "config/worker_auth.json", "config/task_registry_v25.json", "benchmark/registry.json", "benchmark/pool_disposition.json", "research/open_lanes.json"}
FORBIDDEN_PREFIXES = ("state/", "control/", "assignments/", "liveness/", "scheduler/", "scheduler_admission/", "preactivation/", "reports/", "verification/", "integration/", "history/", "transitions/", "superseded/", "runtime/", "benchmark/", "research/")
DURABLE_BOOTSTRAP_PROVENANCE = "PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED"
# Root-epoch11 invariant tokens are also checked by the independent seed:
# "root_tcb_epoch": 11
# "root_tcb_epoch_required": 11

ROOT_BOOTSTRAP_PATHS = {
    "config/authority_bootstrap_v25.json",
    "scripts/reconcile_authority_bootstrap.py",
    ".github/workflows/supernova-authority-bootstrap.yml",
}
ROOT_BOOTSTRAP_STATIC_PATHS = ROOT_BOOTSTRAP_PATHS | {
    "config/repo_policy.json",
    "config/countable_control_set_v25.json",
    "config/admission_authority.json",
    "scripts/root_transition_authorization.py",
    "tests/test_normal_status_writer_partition.py",
    "config/root_tcb_epoch_v25.json",
    "config/root_rotation_seed_v25.json",
    "scripts/reconcile_root_rotation_seed.py",
    ".github/workflows/supernova-root-rotation-seed.yml",
    "config/root_epoch7_repair_seed_v25.json",
    "scripts/reconcile_root_epoch7_repair_seed.py",
    ".github/workflows/supernova-root-epoch7-repair-seed.yml",
    "config/root_epoch7_repair_epoch_v25.json",
    "config/root_epoch8_status_writer_repair_seed_v25.json",
    "scripts/reconcile_root_epoch8_status_writer_repair_seed.py",
    ".github/workflows/supernova-root-epoch8-status-writer-repair-seed.yml",
    "config/root_epoch8_status_writer_repair_epoch_v25.json",
    "config/root_epoch9_integrity_repair_seed_v25.json",
    "scripts/reconcile_root_epoch9_integrity_repair_seed.py",
    ".github/workflows/supernova-root-epoch9-integrity-repair-seed.yml",
    "config/root_epoch9_integrity_repair_epoch_v25.json",
    "config/root_epoch10_scheduler_admission_seed_v25.json",
    "scripts/reconcile_root_epoch10_scheduler_admission_seed.py",
    ".github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml",
    "config/root_epoch10_scheduler_admission_seed_amendment_v25.json",
    "scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py",
    ".github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml",
    "config/root_epoch10_scheduler_admission_epoch_v25.json",
    "config/root_epoch11_stageability_repair_seed_v25.json",
    "config/root_epoch11_stageability_repair_seed_amendment_v25.json",
    "scripts/reconcile_root_epoch11_stageability_repair_seed.py",
    "scripts/reconcile_root_epoch11_stageability_repair_seed_amendment.py",
    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",
    ".github/workflows/supernova-root-epoch11-stageability-repair-seed-amendment.yml",
    "tests/test_root_epoch11_stageability_repair_seed_amendment.py",
    "config/root_epoch11_stageability_repair_epoch_v25.json",
    "config/root_epoch11_readme_lineage_seed_v25.json",
    "scripts/reconcile_root_epoch11_readme_lineage_seed.py",
    ".github/workflows/supernova-root-epoch11-readme-lineage-seed.yml",
    "tests/test_root_epoch11_readme_lineage_seed.py",
    "scripts/scheduler_admission_guard.py",
    "schemas/scheduler_manifest.schema.json",
    "schemas/preactivation_receipt.schema.json",
    "schemas/scheduler_admission.schema.json",
    "schemas/scheduler_admission_copy.schema.json",
    "schemas/staged_candidate.schema.json",
    "scripts/strict_json.py",
    "requirements-validation.lock",
}
REQUIRED_INSTALLED_CONTROL_PATHS = {
    "config/repo_policy.json","config/countable_control_set_v25.json","config/admission_authority.json","config/authority_bootstrap_v25.json","config/root_rotation_seed_v25.json","config/root_tcb_epoch_v25.json",
    "scripts/root_transition_authorization.py","tests/test_normal_status_writer_partition.py",
    "config/validator_environment_v25.json","config/substrate_epoch_v25.json","config/read_only_probe_parallelism_v25.json",
    "config/root_epoch6_repair_seed_v25.json","config/root_epoch6_repair_epoch_v25.json",
    "config/root_epoch7_repair_seed_v25.json","config/root_epoch7_repair_epoch_v25.json",
    "config/root_epoch8_status_writer_repair_seed_v25.json","config/root_epoch8_status_writer_repair_epoch_v25.json",
    "config/root_epoch9_integrity_repair_seed_v25.json","config/root_epoch9_integrity_repair_epoch_v25.json",
    "config/root_epoch10_scheduler_admission_seed_v25.json","config/root_epoch10_scheduler_admission_seed_amendment_v25.json","config/root_epoch10_scheduler_admission_epoch_v25.json",
    "config/root_epoch11_stageability_repair_seed_v25.json","config/root_epoch11_stageability_repair_seed_amendment_v25.json","config/root_epoch11_stageability_repair_epoch_v25.json",
    "config/root_epoch11_readme_lineage_seed_v25.json","scripts/reconcile_root_epoch11_readme_lineage_seed.py","tests/test_root_epoch11_readme_lineage_seed.py",
    "scripts/assert_validator_environment.py","scripts/strict_json.py","scripts/reconcile_open_prs.py","scripts/reconcile_authority_bootstrap.py",
    "scripts/reconcile_root_rotation_seed.py","scripts/reconcile_root_epoch6_repair_seed.py","scripts/reconcile_root_epoch7_repair_seed.py",
    "scripts/reconcile_root_epoch8_status_writer_repair_seed.py","scripts/reconcile_root_epoch9_integrity_repair_seed.py",
    "scripts/reconcile_root_epoch10_scheduler_admission_seed.py","scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py","scripts/scheduler_admission_guard.py",
    "scripts/reconcile_root_epoch11_stageability_repair_seed.py","scripts/reconcile_root_epoch11_stageability_repair_seed_amendment.py",
    "schemas/scheduler_manifest.schema.json","schemas/preactivation_receipt.schema.json","schemas/scheduler_admission.schema.json","schemas/scheduler_admission_copy.schema.json","schemas/staged_candidate.schema.json",
    "tests/test_authority_bootstrap.py","tests/test_bootstrap_root_tcb_and_head_binding.py","tests/test_bootstrap_status_provenance.py",
    "tests/test_validator_environment_contract.py","tests/test_root_epoch6_repair_seed.py","tests/test_root_epoch6_repair.py",
    "tests/test_root_epoch8_status_writer_repair_seed.py","tests/test_root_epoch9_integrity_repair.py","tests/test_strict_json_contract.py",
    "tests/test_root_epoch10_scheduler_admission_seed.py","tests/test_root_epoch10_scheduler_admission_seed_amendment.py","tests/test_root_epoch10_scheduler_admission.py","tests/test_scheduler_admission_negative.py",
    "tests/test_root_epoch11_stageability_repair_seed.py","tests/test_root_epoch11_stageability_repair_seed_amendment.py","tests/test_root_epoch11_stageability_repair.py",
    ".github/workflows/supernova-authority-bootstrap.yml",".github/workflows/supernova-bootstrap-completion-reconcile.yml",
    ".github/workflows/supernova-root-rotation-seed.yml",".github/workflows/supernova-root-epoch6-repair-seed.yml",".github/workflows/supernova-root-epoch7-repair-seed.yml",".github/workflows/supernova-root-epoch8-status-writer-repair-seed.yml",
    ".github/workflows/supernova-root-epoch9-integrity-repair-seed.yml",
    ".github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml",".github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml",
    ".github/workflows/supernova-root-epoch11-stageability-repair-seed.yml",".github/workflows/supernova-root-epoch11-stageability-repair-seed-amendment.yml",
    ".github/workflows/supernova-root-epoch11-readme-lineage-seed.yml",
}


def api(path: str, method: str = "GET", data=None):
    payload=None if data is None else strict_json.canonical_dumps(data).encode("utf-8")
    req = urllib.request.Request(API + path, data=payload, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read();return strict_json.loads(raw.decode("utf-8")) if raw else None

def post(state: str, sha: str, description: str):
    body = {"state": state, "context": BOOTSTRAP_CONTEXT, "description": description[:140]}
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if run_id.isdigit():body["target_url"] = f"https://github.com/{REPO}/actions/runs/{run_id}"
    api("/statuses/" + sha, "POST", body)
def run(cmd, cwd: pathlib.Path):
    p = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False);return p.returncode, p.stdout
def load_json(root: pathlib.Path, path: str):return strict_json.loads((root / path).read_text(encoding="utf-8"))
def fail(sha: str | None, reason: str):
    if sha and HEX40.fullmatch(sha):post("failure", sha, "trusted bootstrap refused: " + reason)
    print("BOOTSTRAP REFUSED:", reason);return 1

def bootstrap_root_paths(trusted_root: pathlib.Path):
    roots = set(ROOT_BOOTSTRAP_STATIC_PATHS);admission = load_json(trusted_root, "config/admission_authority.json")
    for key in ("authority_bootstrap_policy","trusted_reconciler","trusted_authority_bootstrap_reconciler","candidate_diagnostic_workflow","bootstrap_completion_workflow","root_tcb_epoch_path","validator_environment_contract","validator_environment_assertion","strict_json_contract","generation_delta_policy","scheduler_admission_policy","scheduler_admission_guard","scheduler_manifest_schema","preactivation_receipt_schema","scheduler_admission_schema","scheduler_admission_copy_schema","staged_candidate_schema"):
        value = admission.get(key)
        if isinstance(value, str) and value:roots.add(value)
    for key in ("trusted_validator_entrypoints", "authoritative_status_workflows", "trusted_authority_helpers"):
        values = admission.get(key) or []
        if not isinstance(values, list):raise ValueError(f"accepted admission authority {key} is not a list")
        for value in values:
            if not isinstance(value, str) or not value:raise ValueError(f"accepted admission authority {key} contains invalid path")
            roots.add(value)
    return roots

def diagnostic_binding_errors(pr: dict, diagnosed_head_sha: str | None, diagnosed_base_sha: str | None):
    errors=[];head_sha=(pr.get("head") or {}).get("sha");base_sha=(pr.get("base") or {}).get("sha")
    if not isinstance(diagnosed_head_sha,str) or not HEX40.fullmatch(diagnosed_head_sha):errors.append("invalid diagnosed head SHA")
    elif diagnosed_head_sha!=head_sha:errors.append("diagnosed head SHA no longer matches current PR head")
    if not isinstance(diagnosed_base_sha,str) or not HEX40.fullmatch(diagnosed_base_sha):errors.append("invalid diagnosed base SHA")
    elif diagnosed_base_sha!=base_sha:errors.append("diagnosed base SHA no longer matches current PR base")
    return errors

def bootstrap_invariant_errors(trusted_root: pathlib.Path, candidate_root: pathlib.Path, changed: list[str]):
    errors: list[str]=[]
    try:
        root_drift=sorted(bootstrap_root_paths(trusted_root).intersection(changed))
        if root_drift:errors.append("bootstrap root self-modification requires installed owner root-transition authorization: "+root_drift[0])
    except Exception as exc:errors.append("bootstrap root TCB derivation failed: "+repr(exc))
    try:
        policy=load_json(candidate_root,"config/repo_policy.json")
        required_policy={"required_protected":True,"required_pull_request_for_consolidation":True,"forbid_force_push":True,"forbid_branch_deletion":True,"required_main_status_contexts":REQUIRED_CONTEXTS,"required_status_source_integration_ids":[4697060],"required_status_source_creator_logins":["project-supernova-status-authority[bot]"],"operational_source_binding_proof_required":True,"candidate_code_execution_with_status_write_token":"FORBIDDEN","fresh_gate":"BLOCK","legacy_seed_normal_context_publication":"FORBIDDEN_RECEIPT_CONTEXT_ONLY"}
        for key,expected in required_policy.items():
            if policy.get(key)!=expected:errors.append(f"repo policy invariant weakened: {key}")
    except Exception as exc:errors.append("repo policy invariant check failed: "+repr(exc))
    try:
        admission=load_json(candidate_root,"config/admission_authority.json")
        required_admission={"protocol_version":"2.5","task_network_plan_id":PLAN,"required_status_creator":BOOTSTRAP_CREATOR,"candidate_code_execution_with_status_write_token":"FORBIDDEN","ref_selectable_dispatch_with_status_write_token":"FORBIDDEN","candidate_bytes_treatment":"DATA_ONLY_UNDER_TRUSTED_MAIN_VALIDATORS","trusted_reconciler":"scripts/reconcile_open_prs.py","trusted_authority_bootstrap_reconciler":"scripts/reconcile_authority_bootstrap.py","authority_bootstrap_context":BOOTSTRAP_CONTEXT,"bootstrap_completion_workflow":".github/workflows/supernova-bootstrap-completion-reconcile.yml","bootstrap_status_provenance":DURABLE_BOOTSTRAP_PROVENANCE,"validator_environment_contract":"config/validator_environment_v25.json","validator_environment_assertion":"scripts/assert_validator_environment.py","strict_json_contract":"scripts/strict_json.py","root_tcb_epoch_path":"config/root_tcb_epoch_v25.json","root_tcb_epoch":11,"scheduler_admission_guard":"scripts/scheduler_admission_guard.py","scheduler_admission_required_for_countable_promotion":True,"scheduler_task_cardinality":15,"scheduler_replacement_task":"FORBIDDEN","scheduler_active_cohort_constructive_repair":"FORBIDDEN","same_repository_required":True,"owner_authored_required_for_privileged_reconciliation":True,"exact_current_main_ancestor_required":True,"required_contexts":REQUIRED_CONTEXTS}
        for key,expected in required_admission.items():
            if admission.get(key)!=expected:errors.append(f"admission authority invariant weakened: {key}")
    except Exception as exc:errors.append("admission authority invariant check failed: "+repr(exc))
    try:
        bootstrap=load_json(candidate_root,"config/authority_bootstrap_v25.json")
        required_bootstrap={"protocol_version":"2.5","task_network_plan_id":PLAN,"enabled_after_install":True,"bootstrap_context":BOOTSTRAP_CONTEXT,"required_status_creator":BOOTSTRAP_CREATOR,"trusted_executable_source":"EXACT_ACCEPTED_MAIN","candidate_bytes_in_privileged_phase":"DATA_ONLY","candidate_diagnostics":"READ_ONLY_SEPARATE_JOB_REQUIRED","diagnostic_binding":"EXACT_EVENT_HEAD_AND_BASE_REQUIRED","bootstrap_status_target":"DESIGNATED_AUTHORITY_BOOTSTRAP_WORKFLOW_RUN_URL_REQUIRED","bootstrap_success_consumption":DURABLE_BOOTSTRAP_PROVENANCE,"bootstrap_completion_workflow":".github/workflows/supernova-bootstrap-completion-reconcile.yml","completion_run_id_environment":"COMPLETED_BOOTSTRAP_RUN_ID","validator_environment_contract":"config/validator_environment_v25.json","validator_environment_assertion":"scripts/assert_validator_environment.py","strict_json_contract":"scripts/strict_json.py","same_repository_required":True,"owner_authored_required":True,"base_branch_required":"main","exact_current_main_ancestor_required":True,"calibration_streak_required":0,"fresh_allowed_globally_required":False,"protocol_version_required":"2.5","specification_revision_required":4,"root_tcb_epoch_required":11,"worker_auth_change":"FORBIDDEN_IN_AUTOMATED_BOOTSTRAP","state_or_scientific_change":"FORBIDDEN_IN_AUTOMATED_BOOTSTRAP","root_tcb_change":"REQUIRES_EXACT_INSTALLED_OWNER_ROOT_TRANSITION_KERNEL","active_cohort_constructive_scheduler_repair":"FORBIDDEN","merge_authority":"EXISTING_GITHUB_RULESET_ONLY","bootstrap_verifier_may_bypass_ruleset":False,"bootstrap_verifier_may_merge":False,"failure_semantics":"FAIL_CLOSED"}
        for key,expected in required_bootstrap.items():
            if bootstrap.get(key)!=expected:errors.append(f"bootstrap policy invariant weakened: {key}")
    except Exception as exc:errors.append("bootstrap policy invariant check failed: "+repr(exc))
    try:
        freeze=load_json(candidate_root,"config/protocol_freeze.json")
        if freeze.get("frozen_protocol_version")!="2.5":errors.append("protocol freeze weakened: frozen_protocol_version")
        if freeze.get("frozen_specification_revision")!=4:errors.append("protocol freeze weakened: frozen_specification_revision")
        if freeze.get("status")!="FROZEN_UNTIL_TWO_CLEAN_COUNTABLE_COHORTS":errors.append("protocol freeze weakened: status")
        gate=freeze.get("no_successor_before") or {}
        if gate.get("repository_policy_independently_verified") is not True:errors.append("protocol freeze weakened: repository policy gate")
        if gate.get("required_source_bound_contexts")!=REQUIRED_CONTEXTS:errors.append("protocol freeze weakened: source-bound contexts")
        if gate.get("consecutive_countable_clean_v25_cohorts")!=2:errors.append("protocol freeze weakened: clean cohort count")
        if freeze.get("mid_streak_change_rule")!="Any authoritative change to the countable frozen control set after cohort 1 begins resets the streak to zero by default. Non-authoritative external rejection-only evidence may be exempt only when its lack of authority is mechanically demonstrated.":errors.append("protocol freeze weakened: mid-streak reset rule")
    except Exception as exc:errors.append("protocol freeze invariant check failed: "+repr(exc))
    try:
        trusted_control=load_json(trusted_root,"config/countable_control_set_v25.json");candidate_control=load_json(candidate_root,"config/countable_control_set_v25.json")
        if candidate_control.get("protocol_version")!="2.5" or candidate_control.get("task_network_plan_id")!=PLAN:errors.append("countable control identity weakened")
        old_paths=set(trusted_control.get("required_control_paths") or []);new_paths=set(candidate_control.get("required_control_paths") or [])
        removed=sorted(old_paths-new_paths)
        if removed:errors.append("countable control set shrank: "+removed[0])
        missing_installed=sorted(REQUIRED_INSTALLED_CONTROL_PATHS-new_paths)
        if missing_installed:errors.append("countable control missing installed authority/substrate path: "+missing_installed[0])
        if candidate_control.get("scheduler_manifest_required_for_countable_generation") is not True:errors.append("countable scheduler manifest invariant weakened")
        if candidate_control.get("scheduler_admission_required_before_promotion") is not True:errors.append("countable scheduler admission invariant weakened")
        if candidate_control.get("canonical_scheduled_task_count")!=15 or candidate_control.get("replacement_scheduled_task")!="FORBIDDEN":errors.append("canonical 15-task identity invariant weakened")
        if candidate_control.get("active_cohort_constructive_scheduler_repair")!="FORBIDDEN":errors.append("active-cohort scheduler immutability weakened")
        if candidate_control.get("authoritative_change_after_cohort1")!="RESETS_CALIBRATION_STREAK_TO_ZERO":errors.append("countable control mid-streak reset invariant weakened")
        if candidate_control.get("candidate_code_with_status_write_token")!="FORBIDDEN":errors.append("countable control candidate privilege invariant weakened")
        if candidate_control.get("fresh_science")!="FORBIDDEN_UNTIL_TWO_CLEAN_COUNTABLE_COHORTS_PLUS_PRIVATE_FROZEN_PRE_OUTCOME_MANIFEST":errors.append("countable control fresh-science invariant weakened")
    except Exception as exc:errors.append("countable control invariant check failed: "+repr(exc))
    return errors

def main():
    root=pathlib.Path.cwd().resolve()
    try:number=int(os.environ.get("PR_NUMBER","0"))
    except ValueError:number=0
    if number<=0:print("BOOTSTRAP REFUSED: missing PR number");return 1
    pr=api(f"/pulls/{number}");head=pr.get("head") or {};base=pr.get("base") or {};head_sha=head.get("sha");head_ref=head.get("ref");head_repo=(head.get("repo") or {}).get("full_name");author=(pr.get("user") or {}).get("login")
    if os.environ.get("CANDIDATE_DIAGNOSTICS_RESULT")!="success":return fail(head_sha,"read-only candidate diagnostics did not succeed")
    binding_errors=diagnostic_binding_errors(pr,os.environ.get("DIAGNOSED_HEAD_SHA"),os.environ.get("DIAGNOSED_BASE_SHA"))
    if binding_errors:return fail(head_sha,binding_errors[0])
    if base.get("ref")!="main":return fail(head_sha,"base is not main")
    if head_repo!=REPO or author!=OWNER:return fail(head_sha,"same-repository owner-authored PR required")
    if not isinstance(head_ref,str) or not head_ref.startswith(ALLOWED_HEAD_PREFIXES):return fail(head_sha,"head prefix not bootstrap-eligible")
    if not isinstance(head_sha,str) or not HEX40.fullmatch(head_sha):return fail(None,"invalid head SHA")
    state=load_json(root,"state/CURRENT.json")
    if state.get("calibration_streak") != 0:return fail(head_sha,"calibration streak must be zero before authority bootstrap")
    if state.get("fresh_allowed_globally") is not False:return fail(head_sha,"fresh work must be disabled before authority bootstrap")
    rc,out=run(["git","rev-parse","HEAD"],root);trusted=out.strip()
    if rc or not HEX40.fullmatch(trusted):return fail(head_sha,"cannot resolve exact accepted main")
    if os.environ.get("DIAGNOSED_BASE_SHA")!=trusted:return fail(head_sha,"diagnosed base SHA is not exact accepted main")
    run(["git","fetch","--no-tags","origin",f"pull/{number}/head"],root)
    rc,_=run(["git","merge-base","--is-ancestor",trusted,head_sha],root)
    if rc:return fail(head_sha,"PR head does not descend from exact accepted main")
    rc,out=run(["git","diff","--name-only",trusted+"..."+head_sha],root)
    if rc:return fail(head_sha,"cannot enumerate candidate changes")
    changed=[x for x in out.splitlines() if x]
    if not changed:return fail(head_sha,"empty authority change")
    for path in changed:
        if path in FORBIDDEN_EXACT or path.startswith(FORBIDDEN_PREFIXES):return fail(head_sha,"state/scientific/runtime-sensitive path changed: "+path)
        if path not in ALLOWED_EXACT and not path.startswith(ALLOWED_PREFIXES):return fail(head_sha,"path outside automated bootstrap allowlist: "+path)
        rc,tree=run(["git","ls-tree",head_sha,"--",path],root)
        if rc:return fail(head_sha,"cannot inspect candidate git mode: "+path)
        if tree.strip() and tree.split(None,1)[0]!="100644":return fail(head_sha,"non-regular candidate path: "+path)
    tmp=pathlib.Path(tempfile.mkdtemp(prefix=f"supernova-bootstrap-{number}-"))
    try:
        rc,_=run(["git","worktree","add","--detach",str(tmp),head_sha],root)
        if rc:return fail(head_sha,"cannot create candidate data worktree")
        plan=load_json(tmp,"plan/PLAN.json")
        if plan.get("task_network_plan_id")!=PLAN or plan.get("protocol_version")!="2.5":return fail(head_sha,"plan identity/protocol drift")
        if plan.get("specification_revision")!=4:return fail(head_sha,"Revision 4 freeze violated")
        invariant_errors=bootstrap_invariant_errors(root,tmp,changed)
        if invariant_errors:return fail(head_sha,invariant_errors[0])
    except Exception as exc:return fail(head_sha,"candidate policy parse/check failed: "+repr(exc))
    finally:
        run(["git","worktree","remove","--force",str(tmp)],root);shutil.rmtree(tmp,ignore_errors=True)
    description=f"trusted-main bootstrap PASS pr={number} head={head_sha} base={trusted}";post("success",head_sha,description)
    print(f"AUTHORITY_BOOTSTRAP_PASS pr={number} head={head_sha} base={trusted} run={os.environ.get('GITHUB_RUN_ID','')}");return 0
if __name__=="__main__":raise SystemExit(main())
