#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, urllib.parse, urllib.request, urllib.error

TOKEN=os.environ.get('GITHUB_TOKEN','')
REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-')
API='https://api.github.com/repos/'+REPO
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
HMAC2='PS-HMAC-SHA256-CANONICAL-REPORT-2'
WORKERS={'MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01'}
HEX40=re.compile(r'^[0-9a-f]{40}$')
FULL_HARDENED_CONTROL={
    'PROTOCOL.md','BRANCH_PROTOCOL.md','BRANCH_WORKER_PROTOCOL.md','SESSION_STANDARD.md','plan/PLAN.json',
    'config/protocol_freeze.json','config/repo_policy.json','config/roles.json','config/worker_auth.json','config/task_registry_v25.json','config/checker_pins.json',
    'benchmark/registry.json','benchmark/pool_disposition.json',
    'schemas/control.schema.json','schemas/assignment.schema.json','schemas/branch_report.schema.json','schemas/branch_verification.schema.json','schemas/branch_integration.schema.json','schemas/branch_director.schema.json','schemas/branch_consolidation.schema.json','schemas/lane_liveness_observation.schema.json','schemas/cohort_liveness_contract.schema.json','schemas/verifier_assurance.schema.json','schemas/runtime_update.schema.json','schemas/private_manifest_contract.schema.json',
    'scripts/validate_bus.py','scripts/validate_branch_bus_v251.py','scripts/reconcile_branch_rest.py','scripts/reconcile_v25_admission.py','scripts/check_lane_liveness.py',
    'tests/test_v25_report_contracts.py','tests/liveness/test_liveness_monitor.py','tests/verifier_assurance/test_verifier_assurance_schema.py',
    '.github/workflows/supernova-v25-admission.yml','.github/workflows/supernova-rest-branch-reconciler.yml','requirements-validation.lock'
}

def req(path,method='GET',data=None):
    r=urllib.request.Request(API+path,data=(json.dumps(data).encode() if data is not None else None),method=method)
    r.add_header('Accept','application/vnd.github+json');r.add_header('X-GitHub-Api-Version','2022-11-28')
    if TOKEN:r.add_header('Authorization','Bearer '+TOKEN)
    with urllib.request.urlopen(r,timeout=30) as z:
        raw=z.read();return json.loads(raw) if raw else None

def branch_head(branch):
    try:return req('/branches/'+urllib.parse.quote(branch,safe=''))['commit']['sha']
    except urllib.error.HTTPError as e:
        if e.code==404:return None
        raise

def content(path,ref):
    o=req('/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(ref,safe=''))
    if not isinstance(o,dict) or o.get('type')!='file':raise RuntimeError(f'{path}@{ref}: not file')
    return o,json.loads(base64.b64decode(o['content']).decode('utf-8'))

def status(sha,ctx,state,desc):
    req('/statuses/'+sha,'POST',{'state':state,'context':ctx,'description':desc[:140]})

def status_observation(sha,ctx):
    rows=req('/commits/'+sha+'/statuses?per_page=100') or []
    for row in rows:
        if row.get('context')==ctx:
            return {'state':row.get('state'),'creator':(row.get('creator') or {}).get('login'),'id':row.get('id'),'created_at':row.get('created_at')}
    return None

def source_bound_pass(sha,ctx,allowed):
    o=status_observation(sha,ctx)
    if not o:return False,f'{ctx} missing'
    if o.get('state')!='success':return False,f'{ctx} state={o.get("state")}'
    if o.get('creator') not in allowed:return False,f'{ctx} creator={o.get("creator")} not allowed'
    return True,''

def compare(base,head):return req('/compare/'+base+'...'+head)
def changed(base,head):return [f['filename'] for f in compare(base,head).get('files',[]) if f.get('status')!='unchanged']

def required_countable_paths(contract):
    if not isinstance(contract,dict):raise ValueError('countable control contract is not an object')
    if contract.get('protocol_version')!='2.5':raise ValueError('countable control contract protocol != 2.5')
    if contract.get('task_network_plan_id')!=PLAN:raise ValueError('countable control contract plan mismatch')
    paths=contract.get('required_control_paths')
    if not isinstance(paths,list) or not paths or any(not isinstance(x,str) or not x for x in paths):raise ValueError('countable control required paths invalid')
    required=set(paths)
    missing_legacy=sorted(FULL_HARDENED_CONTROL-required)
    if missing_legacy:raise ValueError('canonical countable contract drops hardened minimum: '+','.join(missing_legacy[:4]))
    return required

def result_state(errors,waiting=False):
    if waiting:return 'pending'
    return 'failure' if errors else 'success'

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
        required=set(c.get('required_control_paths',[]))
        countable=bool(c.get('calibration_countable') is True or a.get('calibration_countable') is True or state.get('calibration_countable_current') is True)
        if countable:
            _,accepted_contract=content('config/countable_control_set_v25.json','main')
            required_contract=required_countable_paths(accepted_contract)
            missing=sorted(required_contract-required)
            if missing:e.append('countable control missing canonical hardened paths: '+','.join(missing[:4])+('...' if len(missing)>4 else ''))
            try:
                _,frozen_contract=content('config/countable_control_set_v25.json',root)
                if frozen_contract!=accepted_contract:e.append('frozen countable-control contract differs from accepted main contract')
            except Exception as x:e.append('frozen countable-control contract '+str(x))
            if state.get('repo_policy_status')!='VERIFIED_PROTECTED_SOURCE_BOUND':e.append('countable cohort repo policy not source-bound verified')
            _,auth=content('config/worker_auth.json',root)
            if auth.get('scheme')!=HMAC2:e.append('frozen worker auth metadata != HMAC-2')
            _,pins=content('config/checker_pins.json',root)
            if pins.get('protocol_version')!='2.5':e.append('checker pins protocol mismatch')
    except Exception as x:e.append('generation '+str(x))
    return e

def verification_check(state):
    e=[];cohort=state['active_cohort_id'];G=state['generation_head_sha'];vb=state['verifier_branch'];H=branch_head(vb)
    if not H or H==G:return H,['verifier receipt absent']
    try:
        _,v=content(f'verification/{cohort}.json',H)
        if v.get('task_network_plan_id')!=PLAN or v.get('cohort_id')!=cohort or v.get('generation_head_sha')!=G:e.append('verifier identity mismatch')
        if v.get('verdict')!='VERIFIED_COMPLETE':e.append('verdict not complete')
        if v.get('partition_exhaustive_verified') is not True:e.append('partition not exhaustive')
        if v.get('quarantined_report_refs') or v.get('missing_workers'):e.append('quarantine/missing nonempty')
        refs=v.get('safe_report_refs',[]);ids=[r.get('worker_id') for r in refs if isinstance(r,dict)]
        if set(ids)!=WORKERS or len(ids)!=len(WORKERS):e.append('safe worker partition mismatch')
        for r in refs:
            wid=str(r.get('worker_id'))
            if r.get('path_change_commit_count')!=1:e.append(wid+' path-change count')
            if r.get('immutable_history_valid') is not True:e.append(wid+' immutable history')
            if r.get('auth_valid') is not True or r.get('schema_valid') is not True or r.get('strict_session_valid') is not True:e.append(wid+' verification flags')
            if r.get('execution_mode_valid') is not True and state.get('calibration_countable_current') is True:e.append(wid+' execution mode not verified')
            if r.get('structural_ci_status')!='PASS':e.append(wid+' worker structural status')
            if not HEX40.fullmatch(str(r.get('report_creation_commit_sha',''))):e.append(wid+' creation commit')
        if state.get('calibration_countable_current') is True:
            if v.get('liveness_complete') is not True:e.append('liveness incomplete')
            liv=v.get('lane_liveness_observations',[])
            if len(liv)!=12:e.append('liveness partition size')
            for o in liv:
                if o.get('receipt_status') in ('NO_RECEIPT','RUN_LATE'):e.append(str(o.get('lane_id'))+' liveness '+str(o.get('receipt_status')))
            if v.get('checker_pin_bundle_ref')!='config/checker_pins.json':e.append('checker pins not bound')
            if v.get('statement_fidelity_policy')!='NOT_APPLICABLE_TRANSPORT_ONLY':e.append('transport fidelity policy mismatch')
        if v.get('pre_ci_observation') not in ('PRE_CI','CI_NOT_OBSERVED'):e.append('invalid temporal CI field')
        if v.get('required_post_write_ci_context')!='supernova/report-admission':e.append('wrong required report context')
    except Exception as x:e.append('verifier '+str(x))
    return H,e

def integration_check(state,verifier_head):
    e=[];cohort=state['active_cohort_id'];G=state['generation_head_sha'];ib=state['integrator_branch'];H=branch_head(ib)
    if not H or H==G:return H,['integration receipt absent']
    try:
        _,i=content(f'integration/{cohort}.json',H)
        if i.get('task_network_plan_id')!=PLAN or i.get('cohort_id')!=cohort or i.get('generation_head_sha')!=G:e.append('integration identity mismatch')
        if i.get('verification_head_sha')!=verifier_head:e.append('verification head mismatch')
        if i.get('verification_external_ci_context')!='supernova/report-admission' or i.get('verification_external_ci_status')!='PASS' or i.get('verification_external_ci_observed_after_receipt') is not True:e.append('later verifier CI not bound in receipt')
        allowed=set(i.get('verification_external_ci_source') and [i.get('verification_external_ci_source')] or ['github-actions[bot]'])
        ok,msg=source_bound_pass(verifier_head,'supernova/report-admission',allowed)
        if not ok:e.append('later verifier CI source check '+msg)
        if state.get('calibration_countable_current') is True:
            if i.get('verification_verdict')!='VERIFIED_COMPLETE' or i.get('verification_partition_exhaustive') is not True or i.get('verification_liveness_complete') is not True:e.append('integration does not bind complete verifier+liveness')
            if i.get('quarantines'):e.append('integration quarantine nonempty')
    except Exception as x:e.append('integration '+str(x))
    return H,e

def consolidation_check(state,vh,ih):
    e=[];cohort=state['active_cohort_id'];G=state['generation_head_sha'];cb=state.get('consolidation_branch');H=branch_head(cb) if cb else None
    if not H:return H,['consolidation branch absent']
    if H==G:return H,['consolidation receipt absent']
    try:
        _,r=content(f'history/{cohort}/CONSOLIDATION.json',H)
        M=branch_head('main');B=r.get('expected_main_head')
        if not isinstance(B,str) or not HEX40.fullmatch(B):e.append('bad expected main')
        if M!=B:e.append('stale main CAS')
        if r.get('verification_head_sha')!=vh or r.get('integration_head_sha')!=ih:e.append('fan-in head mismatch')
        files=changed(B,H)
        allowed=all(x.startswith(f'history/{cohort}/') or x=='state/CURRENT.json' or x=='benchmark/registry.json' or x.startswith('control/') or x.startswith('assignments/') or x.startswith('superseded/') or x.startswith('transitions/') for x in files)
        if not allowed or 'state/CURRENT.json' not in files:e.append('illegal consolidation diff')
    except Exception as x:e.append('consolidation '+str(x))
    return H,e

def main():
    _,state=content('state/CURRENT.json','main')
    if state.get('task_network_plan_id')!=PLAN or state.get('transport_mode')!='BRANCH_GITOPS':return 0
    G=state['generation_head_sha']
    ge=generation_check(state)
    status(G,'supernova/static-control','failure' if ge else 'success',('FAIL '+ge[0]) if ge else 'v2.5 frozen static control PASS')
    vh,ve=verification_check(state)
    v_wait=bool(vh and vh==G)
    if vh:
        vs=result_state(ve,v_wait)
        vd='awaiting verifier receipt' if v_wait else (('FAIL '+ve[0]) if ve else 'MM06 exact-head report admission PASS')
        status(vh,'supernova/report-admission',vs,vd)
    ih,ie=integration_check(state,vh)
    i_wait=bool(ih and ih==G)
    if ih:
        is_=result_state(ie,i_wait)
        idesc='awaiting integration receipt' if i_wait else (('FAIL '+ie[0]) if ie else 'MF06 exact-head integration PASS')
        status(ih,'supernova/branch-integrate',is_,idesc)
    ch,ce=consolidation_check(state,vh,ih)
    c_wait=bool(ch and ch==G)
    if ch:
        status(ch,'supernova/static-control','failure' if ge else 'success',('FAIL '+ge[0]) if ge else 'underlying v2.5 static control PASS')
        ri_wait=v_wait or i_wait
        rs=result_state(ve+ie,ri_wait)
        rdesc='awaiting verifier/integration receipt' if ri_wait else (('FAIL '+(ve+ie)[0]) if (ve or ie) else 'verified fan-in/report admission PASS')
        status(ch,'supernova/report-admission',rs,rdesc)
        ts=result_state(ce,c_wait)
        tdesc='awaiting consolidation receipt' if c_wait else (('FAIL '+ce[0]) if ce else 'consolidation CAS/allowed-diff PASS')
        status(ch,'supernova/transition-admission',ts,tdesc)
    return 1 if ge else 0
if __name__=='__main__':raise SystemExit(main())