#!/usr/bin/env python3
"""Out-of-band receipt-deadline monitor for Revision-4 cohorts.

Consumes an explicit frozen cohort liveness contract. It never guesses whether a
Scheduled Task ran. Missing GitHub receipt is NO_RECEIPT; it blocks only after the
declared deadline. Task cause remains TASK_STATE_UNKNOWN unless inspected separately.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, pathlib, urllib.error, urllib.parse, urllib.request
from typing import Callable

UTC=dt.timezone.utc

def parse_time(s: str) -> dt.datetime:
    x=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
    if x.tzinfo is None: raise ValueError('times must be timezone-aware')
    return x.astimezone(UTC)

def evaluate(contract: dict, now: dt.datetime, exists_fn: Callable[[str,str], bool]) -> dict:
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
    return {'schema_version':'PS-LIVENESS-MONITOR-1','cohort_id':contract['cohort_id'],'generation_head_sha':contract['generation_head_sha'],'observation_time':now.isoformat().replace('+00:00','Z'),'observations':observations,'blocking_lanes':blocking,'transition_liveness_pass':not blocking}

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
    contract=json.loads(pathlib.Path(ns.contract).read_text()); now=parse_time(ns.now) if ns.now else dt.datetime.now(UTC)
    result=evaluate(contract,now,github_exists(ns.repo,os.environ.get('GITHUB_TOKEN','')))
    pathlib.Path(ns.out).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); print(json.dumps(result,sort_keys=True))
    return 0 if result['transition_liveness_pass'] else 3

if __name__=='__main__': raise SystemExit(main())
