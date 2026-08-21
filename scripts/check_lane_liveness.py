#!/usr/bin/env python3
"""Out-of-band receipt-deadline monitor for Revision-4 cohorts.

Consumes an explicit frozen cohort liveness contract. It never guesses whether a
Scheduled Task ran. Missing GitHub receipt is NO_RECEIPT; it blocks only after the
declared deadline. Task cause remains TASK_STATE_UNKNOWN unless inspected separately.

The contract is bound to immutable pre-existing generation inputs (generation root,
control blob, assignment blob, cohort). The containing generation Git object binds the
contract into G; the contract therefore never tries to contain its own commit SHA.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, pathlib, urllib.error, urllib.parse, urllib.request
from typing import Callable

UTC=dt.timezone.utc
WORKERS={"MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"}
HEX40=lambda x:isinstance(x,str) and len(x)==40 and all(c in '0123456789abcdef' for c in x)


def parse_time(s: str) -> dt.datetime:
    x=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
    if x.tzinfo is None: raise ValueError('times must be timezone-aware')
    return x.astimezone(UTC)


def validate_contract(contract: dict) -> None:
    required={
        'schema_version','cohort_id','generation_root_sha','control_manifest_id',
        'control_manifest_git_identity','assignment_id','assignment_git_identity','lanes'
    }
    if set(contract)!=required:
        raise ValueError('liveness contract top-level keys mismatch')
    if contract['schema_version']!='PS-COHORT-LIVENESS-2':
        raise ValueError('unsupported liveness contract schema')
    for key in ('generation_root_sha','control_manifest_git_identity','assignment_git_identity'):
        if not HEX40(contract.get(key)): raise ValueError(f'{key} must be lowercase 40-hex')
    lanes=contract.get('lanes')
    if not isinstance(lanes,list) or len(lanes)!=12:
        raise ValueError('liveness contract must contain exactly 12 lanes')
    ids=[x.get('lane_id') for x in lanes if isinstance(x,dict)]
    if len(ids)!=12 or set(ids)!=WORKERS or len(set(ids))!=12:
        raise ValueError('liveness lane IDs must be exactly the 12 assigned workers')
    for lane in lanes:
        allowed={'lane_id','branch','path','expected_window_start_utc','deadline_utc','eligible_before_deadline'}
        if not set(lane).issubset(allowed): raise ValueError(f"{lane.get('lane_id')}: unknown liveness field")
        for key in ('branch','path','expected_window_start_utc','deadline_utc'):
            if not isinstance(lane.get(key),str) or not lane[key]: raise ValueError(f"{lane.get('lane_id')}: missing {key}")
        start=parse_time(lane['expected_window_start_utc']); deadline=parse_time(lane['deadline_utc'])
        if deadline < start: raise ValueError(f"{lane['lane_id']}: deadline precedes expected start")


def evaluate(contract: dict, now: dt.datetime, exists_fn: Callable[[str,str], bool]) -> dict:
    validate_contract(contract)
    if now.tzinfo is None: raise ValueError('now must be timezone-aware')
    now=now.astimezone(UTC); observations=[]; blocking=[]
    for lane in contract['lanes']:
        deadline=parse_time(lane['deadline_utc']); exists=exists_fn(lane['branch'],lane['path'])
        if exists:
            receipt_status='RUN_OBSERVED'; late=max(0,int((now-deadline).total_seconds())) if now>deadline else 0
        elif now>deadline:
            receipt_status='NO_RECEIPT'; late=int((now-deadline).total_seconds()); blocking.append(lane['lane_id'])
        else:
            receipt_status='NO_RECEIPT'; late=0
        observations.append({
            'lane_id':lane['lane_id'],'task_id':None,'associated_chat_ref':None,
            'expected_window_start':lane['expected_window_start_utc'],'expected_window_end':lane['deadline_utc'],
            'observation_time':now.isoformat().replace('+00:00','Z'),'receipt_status':receipt_status,
            'task_state':'TASK_STATE_UNKNOWN','observation_source':'GITHUB_RECEIPT_MONITOR',
            'receipt_ref':f"{lane['branch']}:{lane['path']}" if exists else None,'lateness_seconds':late,
            'notes':'GitHub receipt existence only; Scheduled Task state not inferred.'
        })
    return {
        'schema_version':'PS-LIVENESS-MONITOR-2',
        'cohort_id':contract['cohort_id'],
        'generation_root_sha':contract['generation_root_sha'],
        'control_manifest_git_identity':contract['control_manifest_git_identity'],
        'assignment_git_identity':contract['assignment_git_identity'],
        'observation_time':now.isoformat().replace('+00:00','Z'),
        'observations':observations,
        'blocking_lanes':blocking,
        'transition_liveness_pass':not blocking,
    }


def github_exists(repo: str, token: str):
    api='https://api.github.com/repos/'+repo
    def exists(branch,path):
        url=api+'/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(branch,safe='')
        req=urllib.request.Request(url); req.add_header('Accept','application/vnd.github+json'); req.add_header('X-GitHub-Api-Version','2022-11-28')
        if token: req.add_header('Authorization','Bearer '+token)
        try:
            with urllib.request.urlopen(req,timeout=20) as r: return r.status==200
        except urllib.error.HTTPError as e:
            if e.code==404: return False
            raise
    return exists


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--contract',required=True); ap.add_argument('--out',required=True); ap.add_argument('--now'); ap.add_argument('--repo',default=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-')); ns=ap.parse_args()
    contract=json.loads(pathlib.Path(ns.contract).read_text()); validate_contract(contract)
    now=parse_time(ns.now) if ns.now else dt.datetime.now(UTC)
    result=evaluate(contract,now,github_exists(ns.repo,os.environ.get('GITHUB_TOKEN','')))
    pathlib.Path(ns.out).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); print(json.dumps(result,sort_keys=True))
    return 0 if result['transition_liveness_pass'] else 3

if __name__=='__main__': raise SystemExit(main())
