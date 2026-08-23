#!/usr/bin/env python3
from __future__ import annotations
import base64, os, pathlib, re, sys, urllib.error, urllib.parse, urllib.request

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import strict_json

TOKEN=os.environ.get('GITHUB_TOKEN','')
REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-')
API='https://api.github.com/repos/'+REPO
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
HMAC2='PS-HMAC-SHA256-CANONICAL-REPORT-2'
ACTIONS_CREATOR='github-actions[bot]'
WORKERS={'MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01'}
TERMINAL_VERDICTS={'VERIFIED_COMPLETE','VERIFIED_WITH_QUARANTINES','INCOMPLETE','INVALID'}
HEX40=re.compile(r'^[0-9a-f]{40}$')
MINIMUM_HARDENED_CONTROL={
    'PROTOCOL.md','BRANCH_PROTOCOL.md','BRANCH_WORKER_PROTOCOL.md','SESSION_STANDARD.md','plan/PLAN.json',
    'config/protocol_freeze.json','config/repo_policy.json','config/roles.json','config/worker_auth.json',
    'config/task_registry_v25.json','config/task_registry_semantics_v25.json','config/checker_pins.json','config/countable_control_set_v25.json',
    'config/admission_authority.json','config/root_tcb_epoch_v25.json','config/root_epoch10_scheduler_admission_seed_v25.json',
    'config/root_epoch10_scheduler_admission_seed_amendment_v25.json','config/root_epoch10_scheduler_admission_epoch_v25.json',
    'branch/CONFIG.json','research/open_lanes.json','benchmark/registry.json','benchmark/pool_disposition.json',
    'schemas/state.schema.json','schemas/control.schema.json','schemas/assignment.schema.json','schemas/branch_report.schema.json',
    'schemas/branch_verification.schema.json','schemas/branch_integration.schema.json','schemas/branch_director.schema.json',
    'schemas/branch_consolidation.schema.json','schemas/lane_liveness_observation.schema.json','schemas/cohort_liveness_contract.schema.json',
    'schemas/verifier_assurance.schema.json','schemas/runtime_update.schema.json','schemas/private_manifest_contract.schema.json',
    'schemas/scheduler_manifest.schema.json','schemas/preactivation_receipt.schema.json','schemas/scheduler_admission.schema.json',
    'scripts/strict_json.py','scripts/validate_bus.py','scripts/validate_branch_bus_v251.py','scripts/parent_lineage_guard.py',
    'scripts/generation_delta_guard.py','scripts/scheduler_admission_guard.py','scripts/reconcile_root_epoch10_scheduler_admission_seed.py',
    'scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py',
    'scripts/transition_guard.py','scripts/reconcile_branch_rest.py','scripts/reconcile_branch_statuses.py','scripts/reconcile_v25_admission.py',
    'scripts/reconcile_open_prs.py','scripts/check_lane_liveness.py','scripts/liveness_contract_guard.py',
    'tests/test_v25_report_contracts.py','tests/test_source_bound_repo_policy.py','tests/test_countable_control_freeze.py',
    'tests/test_generation_delta_policy.py','tests/test_root_epoch10_scheduler_admission_seed.py',
    'tests/test_root_epoch10_scheduler_admission_seed_amendment.py','tests/test_root_epoch10_scheduler_admission.py','tests/test_scheduler_admission_negative.py',
    'tests/test_actions_trigger_bridge.py','tests/test_open_pr_admission_trust.py','tests/test_countable_control_gate_consistency.py',
    'tests/test_privileged_admission_workflows.py','tests/liveness/test_liveness_monitor.py','tests/verifier_assurance/test_verifier_assurance_schema.py',
    '.github/workflows/supernova-v25-admission.yml','.github/workflows/supernova-rest-branch-reconciler.yml',
    '.github/workflows/supernova-open-pr-reconciler.yml','.github/workflows/supernova-actions-heartbeat.yml',
    '.github/workflows/supernova-comment-admission.yml','.github/workflows/supernova-pr-target-admission.yml',
    '.github/workflows/supernova-liveness-monitor.yml','.github/workflows/supernova-root-epoch10-scheduler-admission-seed.yml',
    '.github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml','requirements-validation.lock'
}

def req(path,method='GET',data=None):
    payload=None if data is None else strict_json.canonical_dumps(data).encode('utf-8')
    r=urllib.request.Request(API+path,data=payload,method=method)
    r.add_header('Accept','application/vnd.github+json');r.add_header('X-GitHub-Api-Version','2022-11-28')
    if TOKEN:r.add_header('Authorization','Bearer '+TOKEN)
    with urllib.request.urlopen(r,timeout=30) as z:
        raw=z.read();return strict_json.loads(raw.decode('utf-8')) if raw else None

def branch_head(branch):
    try:return req('/branches/'+urllib.parse.quote(branch,safe=''))['commit']['sha']
    except urllib.error.HTTPError as e:
        if e.code==404:return None
        raise

def content(path,ref):
    o=req('/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(ref,safe=''))
    if not isinstance(o,dict) or o.get('type')!='file':raise RuntimeError(f'{path}@{ref}: not file')
    return o,strict_json.loads(base64.b64decode(o['content']).decode('utf-8'))

def status(sha,ctx,state,desc):req('/statuses/'+sha,'POST',{'state':state,'context':ctx,'description':desc[:140]})
def status_observation(sha,ctx):
    for row in req('/commits/'+sha+'/statuses?per_page=100') or []:
        if row.get('context')==ctx:return {'state':row.get('state'),'creator':(row.get('creator') or {}).get('login'),'id':row.get('id'),'created_at':row.get('created_at')}
    return None
def source_bound_pass(sha,ctx):
    o=status_observation(sha,ctx)
    if not o:return False,f'{ctx} missing'
    if o.get('state')!='success':return False,f'{ctx} state={o.get("state")}'
    if o.get('creator')!=ACTIONS_CREATOR:return False,f'{ctx} creator={o.get("creator")} != {ACTIONS_CREATOR}'
    return True,''
def compare(base,head):return req('/compare/'+base+'...'+head)
def changed(base,head):return [f['filename'] for f in compare(base,head).get('files',[]) if f.get('status')!='unchanged']

def required_countable_paths(contract):
    if not isinstance(contract,dict):raise ValueError('countable control contract is not an object')
    if contract.get('protocol_version')!='2.5':raise ValueError('countable control contract protocol != 2.5')
    if contract.get('task_network_plan_id')!=PLAN:raise ValueError('countable control contract plan mismatch')
    paths=contract.get('required_control_paths')
    if not isinstance(paths,list) or not paths or any(not isinstance(x,str) or not x for x in paths):raise ValueError('countable control required paths invalid')
    required=set(paths);missing=sorted(MINIMUM_HARDENED_CONTROL-required)
    if missing:raise ValueError('canonical countable contract drops hardened minimum: '+','.join(missing[:6]))
    return required

def result_state(errors,waiting=False):return 'pending' if waiting else ('failure' if errors else 'success')

def source_bound_scheduler_admission(cohort,admission):
    """The promoted copy must be byte-identical to admitted MM06 preactivation evidence."""
    e=[];branch=admission.get('source_preactivation_admission_branch');commit=admission.get('source_preactivation_admission_commit_sha');blob=admission.get('source_preactivation_admission_blob_sha')
    if admission.get('admission_verdict')!='SCHEDULER_ADMISSION_PASS':e.append('scheduler admission verdict is not SCHEDULER_ADMISSION_PASS')
    if branch!=f'ps/preactivate/{cohort}/MM06':e.append('source_preactivation_admission branch mismatch');return e
    if not isinstance(commit,str) or not HEX40.fullmatch(commit):e.append('source_preactivation_admission commit invalid');return e
    if branch_head(branch)!=commit:e.append('source_preactivation_admission branch head drift');return e
    try:
        meta,source=content(f'preactivation/{cohort}/MM06.json',commit)
        if meta.get('sha')!=blob:e.append('source_preactivation_admission blob mismatch')
        if dict(admission)!=dict(source):e.append('scheduler admission copy differs from MM06 preactivation source')
        ok,msg=source_bound_pass(commit,'supernova/report-admission')
        if not ok:e.append('source_preactivation_admission report-admission '+msg)
    except Exception as x:e.append('source_preactivation_admission '+str(x))
    return e

def generation_check(state):
    e=[];G=state.get('generation_head_sha');gen=state.get('generation_branch');cohort=state.get('active_cohort_id')
    if state.get('protocol_version')!='2.5':e.append('protocol != 2.5')
    if state.get('task_network_plan_id')!=PLAN:e.append('plan mismatch')
    if state.get('transport_mode')!='BRANCH_GITOPS':e.append('transport != BRANCH_GITOPS')
    if not G or branch_head(gen)!=G:e.append('generation head mismatch')
    try:
        cm,c=content(state['active_control_manifest_path'],G);am,a=content(state['active_assignment_path'],G)
        if cm['sha']!=state.get('active_control_manifest_git_identity'):e.append('control blob mismatch')
        if am['sha']!=state.get('active_assignment_git_identity'):e.append('assignment blob mismatch')
        if c.get('task_network_plan_id')!=PLAN or a.get('task_network_plan_id')!=PLAN:e.append('generation plan mismatch')
        if c.get('protocol_version')!='2.5':e.append('control protocol != 2.5')
        if c.get('cohort_id')!=cohort or a.get('cohort_id')!=cohort:e.append('cohort mismatch')
        if c.get('worker_auth_scheme')!=HMAC2:e.append('control HMAC scheme mismatch')
        root=c.get('control_release_commit_sha')
        if not isinstance(root,str) or not HEX40.fullmatch(root):e.append('bad control root')
        if a.get('generation_root_sha')!=root:e.append('assignment root mismatch')
        required=set(c.get('required_control_paths',[]));countable=bool(c.get('calibration_countable') is True or a.get('calibration_countable') is True or state.get('calibration_countable_current') is True)
        if countable:
            _,accepted_contract=content('config/countable_control_set_v25.json','main');required_contract=required_countable_paths(accepted_contract)
            missing=sorted(required_contract-required)
            if missing:e.append('countable control missing canonical hardened paths: '+','.join(missing[:6]))
            try:
                _,frozen_contract=content('config/countable_control_set_v25.json',root)
                if frozen_contract!=accepted_contract:e.append('frozen countable-control contract differs from accepted main contract')
            except Exception as x:e.append('frozen countable-control contract '+str(x))
            if state.get('repo_policy_status')!='VERIFIED_PROTECTED_SOURCE_BOUND':e.append('countable cohort repo policy not source-bound verified')
            _,auth=content('config/worker_auth.json',root)
            if auth.get('scheme')!=HMAC2:e.append('frozen worker auth metadata != HMAC-2')
            _,pins=content('config/checker_pins.json',root)
            if pins.get('protocol_version')!='2.5':e.append('checker pins protocol mismatch')
            _,authority=content('config/admission_authority.json',root)
            if authority.get('candidate_code_execution_with_status_write_token')!='FORBIDDEN':e.append('frozen admission authority permits privileged candidate code')
            if c.get('scheduler_admission_required') is True:
                smeta,_=content(c.get('scheduler_manifest_path'),G)
                if smeta.get('sha')!=c.get('scheduler_manifest_git_identity'):e.append('frozen scheduler manifest blob mismatch')
                try:
                    _,admission=content(f'scheduler_admission/{cohort}.json','main');e.extend(source_bound_scheduler_admission(cohort,admission))
                except Exception as x:e.append('scheduler admission missing after promotion: '+str(x))
    except Exception as x:e.append('generation '+str(x))
    return e

def verification_semantic_errors(v,state):
    e=[];verdict=v.get('verdict')
    if verdict not in TERMINAL_VERDICTS:e.append('invalid terminal verifier verdict')
    if v.get('partition_exhaustive_verified') is not True:e.append('partition not exhaustive')
    refs=v.get('safe_report_refs',[]);qrefs=v.get('quarantined_report_refs',[]);missing=v.get('missing_workers',[])
    if not isinstance(refs,list) or not isinstance(qrefs,list) or not isinstance(missing,list):return e+['verifier partition fields must be arrays']
    safe_ids=[r.get('worker_id') for r in refs if isinstance(r,dict)];q_ids=[r.get('worker_id') for r in qrefs if isinstance(r,dict)];missing_ids=[x for x in missing if isinstance(x,str)];all_ids=safe_ids+q_ids+missing_ids
    if any(x not in WORKERS for x in all_ids):e.append('verifier partition contains unknown worker')
    if len(all_ids)!=len(WORKERS) or set(all_ids)!=WORKERS:e.append('worker partition is not exhaustive over 12 workers')
    if len(set(all_ids))!=len(all_ids):e.append('worker partition is not disjoint')
    for r in refs:
        if not isinstance(r,dict):e.append('safe ref is not object');continue
        wid=str(r.get('worker_id'))
        if r.get('path_change_commit_count')!=1:e.append(wid+' path-change count')
        if r.get('immutable_history_valid') is not True:e.append(wid+' immutable history')
        if r.get('auth_valid') is not True or r.get('schema_valid') is not True or r.get('strict_session_valid') is not True:e.append(wid+' verification flags')
        if r.get('execution_mode_valid') is not True and state.get('calibration_countable_current') is True:e.append(wid+' execution mode not verified')
        if r.get('structural_ci_status')!='PASS':e.append(wid+' worker structural status')
        if not HEX40.fullmatch(str(r.get('report_creation_commit_sha',''))):e.append(wid+' creation commit')
    for r in qrefs:
        if not isinstance(r,dict):e.append('quarantine ref is not object');continue
        wid=str(r.get('worker_id'));h=r.get('observed_head_sha');b=r.get('observed_blob_sha')
        if h is not None and not HEX40.fullmatch(str(h)):e.append(wid+' quarantine head')
        if b is not None and not HEX40.fullmatch(str(b)):e.append(wid+' quarantine blob')
        if not r.get('reason_code'):e.append(wid+' quarantine reason missing')
    if verdict=='VERIFIED_COMPLETE':
        if qrefs or missing or set(safe_ids)!=WORKERS or len(safe_ids)!=len(WORKERS):e.append('complete verdict requires 12 SAFE and zero quarantine/missing')
    elif verdict=='VERIFIED_WITH_QUARANTINES':
        if not qrefs or missing:e.append('quarantine verdict requires nonempty quarantine and zero missing')
        if v.get('calibration_pass') is not False:e.append('nonclean verifier verdict cannot grant calibration pass')
    elif verdict=='INCOMPLETE':
        if not missing:e.append('incomplete verdict requires missing workers')
        if v.get('calibration_pass') is not False:e.append('nonclean verifier verdict cannot grant calibration pass')
    elif verdict=='INVALID' and v.get('calibration_pass') is not False:e.append('nonclean verifier verdict cannot grant calibration pass')
    if state.get('calibration_countable_current') is True:
        liv=v.get('lane_liveness_observations',[])
        if not isinstance(liv,list) or len(liv)!=12:e.append('liveness partition size')
        else:
            lane_ids=[o.get('lane_id') for o in liv if isinstance(o,dict)]
            if len(lane_ids)!=12 or set(lane_ids)!=WORKERS:e.append('liveness workers do not exhaust 12 lanes')
            if verdict=='VERIFIED_COMPLETE':
                if v.get('liveness_complete') is not True:e.append('complete verdict requires liveness complete')
                for o in liv:
                    if not isinstance(o,dict) or o.get('receipt_status') in ('NO_RECEIPT','RUN_LATE','RUN_TIMING_UNKNOWN'):e.append(str(o.get('lane_id') if isinstance(o,dict) else 'unknown')+' liveness not clean')
        if v.get('checker_pin_bundle_ref')!='config/checker_pins.json':e.append('checker pins not bound')
        if v.get('statement_fidelity_policy')!='NOT_APPLICABLE_TRANSPORT_ONLY':e.append('transport fidelity policy mismatch')
    if v.get('pre_ci_observation') not in ('PRE_CI','CI_NOT_OBSERVED'):e.append('invalid temporal CI field')
    if v.get('required_post_write_ci_context')!='supernova/report-admission':e.append('wrong required report context')
    return e

def verification_check(state):
    e=[];cohort=state['active_cohort_id'];G=state['generation_head_sha'];vb=state['verifier_branch'];H=branch_head(vb)
    if not H or H==G:return H,['verifier receipt absent']
    try:
        _,v=content(f'verification/{cohort}.json',H)
        if v.get('task_network_plan_id')!=PLAN or v.get('cohort_id')!=cohort or v.get('generation_head_sha')!=G:e.append('verifier identity mismatch')
        e.extend(verification_semantic_errors(v,state))
    except Exception as x:e.append('verifier '+str(x))
    return H,e

def integration_semantic_errors(i,v,state):
    e=[]
    if i.get('verification_verdict')!=v.get('verdict'):e.append('integration verification verdict mismatch')
    if i.get('verification_partition_exhaustive')!=v.get('partition_exhaustive_verified'):e.append('integration partition flag mismatch')
    if i.get('verification_liveness_complete')!=v.get('liveness_complete'):e.append('integration liveness flag mismatch')
    if i.get('safe_report_refs')!=v.get('safe_report_refs'):e.append('integration safe refs differ from MM06 safe refs')
    if i.get('quarantines')!=v.get('quarantined_report_refs'):e.append('integration quarantines differ from MM06 quarantine refs')
    if i.get('missing_workers')!=v.get('missing_workers'):e.append('integration missing workers differ from MM06')
    if i.get('calibration_pass') is True:
        clean=(v.get('verdict')=='VERIFIED_COMPLETE' and v.get('calibration_pass') is True and not v.get('quarantined_report_refs') and not v.get('missing_workers') and len(v.get('safe_report_refs',[]))==len(WORKERS) and v.get('liveness_complete') is True)
        if not clean:e.append('integration calibration pass requires clean MM06 verdict/partition/liveness')
    if v.get('verdict')!='VERIFIED_COMPLETE' and i.get('calibration_pass') is not False:e.append('diagnostic integration must force calibration pass false')
    return e

def integration_check(state,verifier_head):
    e=[];cohort=state['active_cohort_id'];G=state['generation_head_sha'];ib=state['integrator_branch'];H=branch_head(ib)
    if not H or H==G:return H,['integration receipt absent']
    try:
        _,i=content(f'integration/{cohort}.json',H);_,v=content(f'verification/{cohort}.json',verifier_head)
        if i.get('task_network_plan_id')!=PLAN or i.get('cohort_id')!=cohort or i.get('generation_head_sha')!=G:e.append('integration identity mismatch')
        if i.get('verification_head_sha')!=verifier_head:e.append('verification head mismatch')
        if i.get('verification_external_ci_context')!='supernova/report-admission' or i.get('verification_external_ci_status')!='PASS' or i.get('verification_external_ci_observed_after_receipt') is not True:e.append('later verifier CI not bound in receipt')
        if i.get('verification_external_ci_source')!=ACTIONS_CREATOR:e.append('integration CI source field is not github-actions[bot]')
        ok,msg=source_bound_pass(verifier_head,'supernova/report-admission')
        if not ok:e.append('later verifier CI source check '+msg)
        e.extend(integration_semantic_errors(i,v,state))
    except Exception as x:e.append('integration '+str(x))
    return H,e

def consolidation_check(state,vh,ih):
    e=[];cohort=state['active_cohort_id'];G=state['generation_head_sha'];cb=state.get('consolidation_branch');H=branch_head(cb) if cb else None
    if not H:return H,['consolidation branch absent']
    if H==G:return H,['consolidation receipt absent']
    try:
        _,r=content(f'history/{cohort}/CONSOLIDATION.json',H);M=branch_head('main');B=r.get('expected_main_head')
        if not isinstance(B,str) or not HEX40.fullmatch(B):e.append('bad expected main')
        if M!=B:e.append('stale main CAS')
        if r.get('verification_head_sha')!=vh or r.get('integration_head_sha')!=ih:e.append('fan-in head mismatch')
        files=changed(B,H);allowed=all(x.startswith(f'history/{cohort}/') or x=='state/CURRENT.json' or x=='benchmark/registry.json' or x.startswith('control/') or x.startswith('assignments/') or x.startswith('liveness/') or x.startswith('scheduler/') or x.startswith('scheduler_admission/') or x.startswith('superseded/') or x.startswith('transitions/') for x in files)
        if not allowed or 'state/CURRENT.json' not in files:e.append('illegal consolidation diff')
    except Exception as x:e.append('consolidation '+str(x))
    return H,e

def main():
    _,state=content('state/CURRENT.json','main')
    if state.get('task_network_plan_id')!=PLAN or state.get('transport_mode')!='BRANCH_GITOPS':return 0
    G=state['generation_head_sha'];ge=generation_check(state)
    status(G,'supernova/static-control','failure' if ge else 'success',('FAIL '+ge[0]) if ge else 'v2.5 frozen static control PASS')
    vh,ve=verification_check(state);v_wait=bool(vh and vh==G)
    if vh:
        vs=result_state(ve,v_wait);vd='awaiting verifier receipt' if v_wait else (('FAIL '+ve[0]) if ve else 'MM06 exact-head report admission PASS');status(vh,'supernova/report-admission',vs,vd)
    ih,ie=integration_check(state,vh);i_wait=bool(ih and ih==G);ch,ce=consolidation_check(state,vh,ih);c_wait=bool(ch and ch==G)
    if ch:
        status(ch,'supernova/static-control','failure' if ge else 'success',('FAIL '+ge[0]) if ge else 'underlying v2.5 static control PASS')
        ri_wait=v_wait or i_wait;rs=result_state(ve+ie,ri_wait);rdesc='awaiting verifier/integration receipt' if ri_wait else (('FAIL '+(ve+ie)[0]) if (ve or ie) else 'verified fan-in/report admission PASS');status(ch,'supernova/report-admission',rs,rdesc)
        ts=result_state(ce,c_wait);tdesc='awaiting consolidation receipt' if c_wait else (('FAIL '+ce[0]) if ce else 'consolidation CAS/allowed-diff PASS');status(ch,'supernova/transition-admission',ts,tdesc)
    return 1 if ge else 0
if __name__=='__main__':raise SystemExit(main())
