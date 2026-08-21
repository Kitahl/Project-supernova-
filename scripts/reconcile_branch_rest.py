#!/usr/bin/env python3
from __future__ import annotations
import base64, datetime as dt, json, os, re, sys, urllib.parse, urllib.request, urllib.error
TOKEN=os.environ.get('GITHUB_TOKEN','')
REPO=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-')
API='https://api.github.com/repos/'+REPO
PLAN='0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
WORKERS=('MF01','MF02','MF03','MF04','MF05','MM01','MM02','MM03','MM04','MM05','MM07','EXT01')
WORKER_SET=set(WORKERS)
SESS={'MF01':'PS-MF-W01 | Representation Lab','MF02':'PS-MF-W02 | E1 Solver Routing','MF03':'PS-MF-W03 | Lemma & Operator Lab','MF04':'PS-MF-W04 | Adversarial Falsifier','MF05':'PS-MF-W05 | Product Closure','MM01':'PS-MM-W01 | React Mechanisms','MM02':'PS-MM-W02 | DeepSWE Mechanisms','MM03':'PS-MM-W03 | SlopCode Contracts','MM04':'PS-MM-W04 | Senior SWE Architecture','MM05':'PS-MM-W05 | E3 Mechanism Controls','MM07':'PS-MM-W07 | Before/After Self-Bench','EXT01':'PS-JOINT-A01 | Runtime & Transport Audit'}
HEX40=re.compile(r'^[0-9a-f]{40}$');HEX64=re.compile(r'^[0-9a-f]{64}$')
BAD={'hidden_task_name','hidden_task_id','protected_task_id','benchmark_item_id','raw_hidden_prompt','private_manifest_payload','private_manifest_content','worker_auth_secret','worker_auth_secret_hex','secret','credential','api_key','access_token','password'}
def req(path,method='GET',data=None):
    url=API+path
    r=urllib.request.Request(url,data=(json.dumps(data).encode() if data is not None else None),method=method)
    r.add_header('Accept','application/vnd.github+json');r.add_header('X-GitHub-Api-Version','2022-11-28')
    if TOKEN:r.add_header('Authorization','Bearer '+TOKEN)
    with urllib.request.urlopen(r,timeout=30) as z:
        raw=z.read();return json.loads(raw) if raw else None
def file_text(path,ref):
    o=req('/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(ref,safe=''))
    if not isinstance(o,dict) or o.get('type')!='file':raise RuntimeError(f'{path}@{ref}: not a file')
    return o,base64.b64decode(o.get('content','')).decode('utf-8')
def content(path,ref):
    o,text=file_text(path,ref)
    return o,json.loads(text)
def branch_head(branch):
    try:return req('/branches/'+urllib.parse.quote(branch,safe=''))['commit']['sha']
    except urllib.error.HTTPError as e:
        if e.code==404:return None
        raise
def compare(base,head):return req('/compare/'+base+'...'+head)
def status(sha,ctx,state,desc):
    req('/statuses/'+sha,'POST',{'state':state,'context':ctx,'description':desc[:140]})
def public_safe(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if str(k).lower() in BAD:return False
            if not public_safe(v):return False
    elif isinstance(o,list):
        return all(public_safe(x) for x in o)
    return True
def changed_files(base,head):
    c=compare(base,head);return c,[f['filename'] for f in c.get('files',[]) if f.get('status')!='unchanged']
def top_schema_check(obj,schema):
    if not isinstance(obj,dict):return False,'not object'
    missing=[x for x in schema.get('required',[]) if x not in obj]
    if missing:return False,'missing '+','.join(missing[:4])
    if schema.get('additionalProperties') is False:
        allowed=set(schema.get('properties',{}));extra=set(obj)-allowed
        if extra:return False,'extra '+','.join(sorted(extra)[:4])
    return True,'top envelope ok'
def parse_time(s):
    try:
        x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00'))
        return x if x.tzinfo is not None else None
    except Exception:return None
def liveness_errors(contract,control,assignment,control_blob,assignment_blob):
    e=[]
    if not isinstance(contract,dict):return ['liveness contract not object']
    exact={
        'schema_version':'PS-COHORT-LIVENESS-2',
        'cohort_id':assignment.get('cohort_id'),
        'generation_root_sha':assignment.get('generation_root_sha'),
        'control_manifest_id':assignment.get('control_manifest_id'),
        'control_manifest_git_identity':control_blob,
        'assignment_id':assignment.get('assignment_id'),
        'assignment_git_identity':assignment_blob,
    }
    for k,v in exact.items():
        if contract.get(k)!=v:e.append('liveness '+k+' mismatch')
    lanes=contract.get('lanes')
    if not isinstance(lanes,list) or len(lanes)!=12:return e+['liveness lanes != 12']
    ids=[x.get('lane_id') for x in lanes if isinstance(x,dict)]
    if set(ids)!=WORKER_SET or len(ids)!=12 or len(set(ids))!=12:e.append('liveness worker set mismatch')
    by={x.get('lane_id'):x for x in lanes if isinstance(x,dict)}
    for w in WORKERS:
        lane=by.get(w);aw=(assignment.get('workers') or {}).get(w,{})
        if not lane:continue
        if lane.get('branch')!=aw.get('worker_branch'):e.append('liveness branch '+w)
        if lane.get('path')!=f"reports/{assignment.get('cohort_id')}/{w}.json":e.append('liveness path '+w)
        start=parse_time(lane.get('expected_window_start_utc'));deadline=parse_time(lane.get('deadline_utc'))
        if start is None or deadline is None or deadline<start:e.append('liveness time '+w)
    return e
def main():
    _,state=content('state/CURRENT.json','main')
    if state.get('task_network_plan_id')!=PLAN or state.get('transport_mode')!='BRANCH_GITOPS':
        print('No active canonical branch-GitOps plan; nothing to reconcile.');return 0
    cohort=state['active_cohort_id'];G=state['generation_head_sha'];gen=state['generation_branch']
    errors=[]
    gh=branch_head(gen)
    if gh!=G:errors.append(f'generation ref {gh} != {G}')
    try:
        cm,control=content(state['active_control_manifest_path'],G);am,assignment=content(state['active_assignment_path'],G)
        if cm['sha']!=state['active_control_manifest_git_identity']:errors.append('state control blob mismatch')
        if am['sha']!=state['active_assignment_git_identity']:errors.append('state assignment blob mismatch')
        if control.get('task_network_plan_id')!=PLAN or assignment.get('task_network_plan_id')!=PLAN:errors.append('generation plan mismatch')
        if control.get('cohort_id')!=cohort or assignment.get('cohort_id')!=cohort:errors.append('generation cohort mismatch')
        root=control.get('control_release_commit_sha')
        if not isinstance(root,str) or not HEX40.fullmatch(root):errors.append('bad generation root')
        if assignment.get('generation_root_sha')!=root:errors.append('assignment root mismatch')
        if assignment.get('control_manifest_git_identity')!=cm['sha']:errors.append('assignment control blob mismatch')
        if assignment.get('generation_branch')!=gen:errors.append('assignment generation branch mismatch')
        c,files=changed_files(root,G)
        expected={state['active_control_manifest_path'],state['active_assignment_path']}
        if control.get('calibration_countable') is True:
            lp=f'liveness/{cohort}.json';expected.add(lp)
            lm,contract=content(lp,G)
            errors.extend(liveness_errors(contract,control,assignment,cm['sha'],am['sha']))
        if set(files)!=expected:errors.append('generation root->G changed paths '+repr(files))
        for p in control.get('required_control_paths',[]):
            a,_=file_text(p,root);b,_=file_text(p,G)
            if a['sha']!=b['sha']:errors.append('frozen control drift '+p)
    except Exception as e:errors.append('generation exception: '+str(e))
    status(G,'supernova/branch-generation','failure' if errors else 'success',('FAIL: '+errors[0]) if errors else 'immutable generation/control/assignment/liveness PASS')
    if errors:
        print('generation failed');[print('-',x) for x in errors];return 1
    _,report_schema=content('schemas/branch_report.schema.json',G)
    for w in WORKERS:
        branch=state['worker_branches'][w];H=branch_head(branch)
        if H is None:
            status(G,'supernova/branch-worker','failure',w+': assigned branch missing');continue
        if H==G:
            status(H,'supernova/branch-worker','pending',w+': awaiting immutable report');continue
        e=[]
        try:
            _,files=changed_files(G,H);path=f'reports/{cohort}/{w}.json'
            if files!=[path]:e.append('diff != exactly assigned report')
            fm,r=content(path,H);ok,msg=top_schema_check(r,report_schema)
            if not ok:e.append(msg)
            aw=assignment['workers'][w]
            exact={'task_network_plan_id':PLAN,'cohort_id':cohort,'worker_id':w,'generation_seq':assignment['generation_seq'],'generation_head_sha':G,'worker_branch':branch,'assignment_id':assignment['assignment_id'],'assignment_git_identity':am['sha'],'parent_state_git_identity':assignment['parent_state_git_identity'],'control_manifest_id':assignment['control_manifest_id'],'control_manifest_git_identity':cm['sha'],'network_checkpoint_id':assignment['network_checkpoint_id'],'runtime_state_id':assignment['runtime_state_id'],'visibility_token':aw['visibility_token'],'worker_auth_scheme':'PS-HMAC-SHA256-CANONICAL-REPORT-2','status':'VALID_ASSIGNED_REPORT','public_safety_status':'PASS','origin_reread_claim':False}
            for k,v in exact.items():
                if r.get(k)!=v:e.append('binding '+k)
            sh=r.get('session_header',{});sexact={'session_name':SESS[w],'target_program':aw['target_program'],'phase':assignment['phase'],'iteration_id':cohort,'iteration_number':assignment['generation_seq'],'role_id':w,'goal':aw['goal'],'plan_id':PLAN,'runtime_state_id':assignment['runtime_state_id'],'model_target':'GPT-5.6 Sol','reasoning_effort_target':'EXTRA_HIGH'}
            for k,v in sexact.items():
                if sh.get(k)!=v:e.append('session '+k)
            if not HEX64.fullmatch(str(r.get('worker_auth_proof',''))):e.append('bad auth proof format')
            if not public_safe(r):e.append('public-safety key')
            if assignment.get('network_mode')=='GITHUB_BRANCH_CALIBRATION':
                led=r.get('cost_ledger',{})
                if r.get('mode')!='SAFE_REPLAY_ONLY' or r.get('fresh_evidence_ids')!=[] or r.get('private_manifest_id') is not None:e.append('fresh/private calibration data')
                if any(led.get(k)!=0 for k in ('fresh_evidence_units_consumed','protected_manifest_reads','benchmark_executions','deep_research_runs')):e.append('nonzero calibration cost')
        except Exception as x:e.append(str(x))
        status(H,'supernova/branch-worker','failure' if e else 'success',w+(': FAIL '+e[0] if e else ': structural PASS; HMAC owned by MM06'))
    for key,ctx,path,schema_path in (
        ('verifier_branch','supernova/branch-verify',f'verification/{cohort}.json','schemas/branch_verification.schema.json'),
        ('integrator_branch','supernova/branch-integrate',f'integration/{cohort}.json','schemas/branch_integration.schema.json')):
        branch=state[key];H=branch_head(branch)
        if H is None:continue
        if H==G:
            status(H,ctx,'pending',key+': awaiting receipt');continue
        e=[]
        try:
            _,files=changed_files(G,H)
            if files!=[path]:e.append('diff != exactly '+path)
            _,obj=content(path,H);_,sch=content(schema_path,G);ok,msg=top_schema_check(obj,sch)
            if not ok:e.append(msg)
            if obj.get('task_network_plan_id')!=PLAN or obj.get('cohort_id')!=cohort or obj.get('generation_head_sha')!=G:e.append('identity binding')
            if key=='verifier_branch':
                lm,_=file_text(f'liveness/{cohort}.json',G)
                if obj.get('liveness_contract_path')!=f'liveness/{cohort}.json':e.append('liveness contract path')
                if obj.get('liveness_contract_git_identity')!=lm['sha']:e.append('liveness contract blob')
                if obj.get('liveness_contract_binding_verified') is not True:e.append('liveness binding flag')
        except Exception as x:e.append(str(x))
        status(H,ctx,'failure' if e else 'success',key+(': FAIL '+e[0] if e else ': structural PASS'))
    cb=state.get('consolidation_branch')
    if cb:
        H=branch_head(cb)
        if H:
            p=f'history/{cohort}/CONSOLIDATION.json'
            try:
                _,r=content(p,H);B=r.get('expected_main_head');M=branch_head('main');_,files=changed_files(B,H)
                allowed=all(x.startswith(f'history/{cohort}/') or x=='state/CURRENT.json' or x=='benchmark/registry.json' or x.startswith('control/') or x.startswith('assignments/') or x.startswith('superseded/') or x.startswith('transitions/') for x in files)
                ok=bool(B and HEX40.fullmatch(B) and M==B and allowed and 'state/CURRENT.json' in files)
                status(H,'supernova/branch-consolidate','success' if ok else 'failure','consolidation CAS/diff '+('PASS' if ok else 'FAIL'))
            except urllib.error.HTTPError as x:
                if x.code==404:status(H,'supernova/branch-consolidate','pending','awaiting consolidation receipt')
                else:raise
            except Exception as x:status(H,'supernova/branch-consolidate','failure','consolidation error '+str(x)[:100])
    print('REST branch reconciliation complete for',cohort);return 0
if __name__=='__main__':raise SystemExit(main())
