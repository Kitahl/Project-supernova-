#!/usr/bin/env python3
"""Out-of-band receipt-deadline monitor for Revision-4 cohorts.

Consumes an explicit frozen cohort liveness contract. It never guesses whether a
Scheduled Task ran. Missing GitHub receipt is NO_RECEIPT; it blocks only after the
declared deadline. Existing receipts are timed from their immutable create-once
GitHub path history rather than from monitor poll time. Task cause remains
TASK_STATE_UNKNOWN unless inspected separately.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, pathlib, urllib.error, urllib.parse, urllib.request
from typing import Callable
UTC=dt.timezone.utc

def parse_time(s: str) -> dt.datetime:
    x=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
    if x.tzinfo is None: raise ValueError('times must be timezone-aware')
    return x.astimezone(UTC)

def _creation_time(value) -> dt.datetime | None:
    if value is None or value is False:
        return None
    if isinstance(value, dt.datetime):
        if value.tzinfo is None: raise ValueError('receipt creation time must be timezone-aware')
        return value.astimezone(UTC)
    if isinstance(value, str):
        return parse_time(value)
    raise ValueError('existing receipt must provide an authoritative creation time')

def evaluate(contract: dict, now: dt.datetime, receipt_fn: Callable[[str,str], object]) -> dict:
    if now.tzinfo is None: raise ValueError('now must be timezone-aware')
    now=now.astimezone(UTC); observations=[]; blocking=[]
    for lane in contract['lanes']:
        deadline=parse_time(lane['deadline_utc'])
        created=_creation_time(receipt_fn(lane['branch'],lane['path']))
        if created is not None:
            if created>deadline:
                receipt_status='RUN_LATE';late=int((created-deadline).total_seconds());blocking.append(lane['lane_id'])
                notes='GitHub create-once receipt creation time is after the frozen deadline; transition blocked.'
            else:
                receipt_status='RUN_OBSERVED';late=0
                notes='GitHub create-once receipt creation time is on/before the frozen deadline; delayed polling does not make it late.'
        elif now>deadline:
            receipt_status='NO_RECEIPT';late=int((now-deadline).total_seconds());blocking.append(lane['lane_id'])
            notes='No GitHub receipt exists after the frozen deadline; Scheduled Task state not inferred.'
        else:
            receipt_status='NO_RECEIPT';late=0
            notes='No GitHub receipt yet; before deadline this remains pending and Scheduled Task state is not inferred.'
        observations.append({'lane_id':lane['lane_id'],'task_id':None,'associated_chat_ref':None,'expected_window_start':lane['expected_window_start_utc'],'expected_window_end':lane['deadline_utc'],'observation_time':now.isoformat().replace('+00:00','Z'),'receipt_status':receipt_status,'task_state':'TASK_STATE_UNKNOWN','observation_source':'GITHUB_RECEIPT_MONITOR','receipt_ref':f"{lane['branch']}:{lane['path']}" if created is not None else None,'lateness_seconds':late,'notes':notes})
    return {'schema_version':'PS-LIVENESS-MONITOR-2','cohort_id':contract['cohort_id'],'generation_root_sha':contract['generation_root_sha'],'observation_time':now.isoformat().replace('+00:00','Z'),'observations':observations,'blocking_lanes':blocking,'transition_liveness_pass':not blocking}

def github_receipt_creation(repo: str, token: str):
    api='https://api.github.com/repos/'+repo
    def get_json(url):
        req=urllib.request.Request(url);req.add_header('Accept','application/vnd.github+json');req.add_header('X-GitHub-Api-Version','2022-11-28')
        if token:req.add_header('Authorization','Bearer '+token)
        with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read())
    def observe(branch,path):
        contents=api+'/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(branch,safe='')
        try:get_json(contents)
        except urllib.error.HTTPError as e:
            if e.code==404:return None
            raise
        commits=api+'/commits?sha='+urllib.parse.quote(branch,safe='')+'&path='+urllib.parse.quote(path,safe='')+'&per_page=100'
        history=get_json(commits)
        if not isinstance(history,list) or len(history)!=1:
            raise RuntimeError(f'{branch}:{path}: create-once receipt history must contain exactly one commit')
        c=history[0].get('commit') or {};d=(c.get('committer') or {}).get('date')
        if not isinstance(d,str):raise RuntimeError(f'{branch}:{path}: authoritative creation time unavailable')
        return parse_time(d)
    return observe

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--contract',required=True);ap.add_argument('--out',required=True);ap.add_argument('--now');ap.add_argument('--repo',default=os.environ.get('GITHUB_REPOSITORY','Kitahl/Project-supernova-'));ns=ap.parse_args()
    contract=json.loads(pathlib.Path(ns.contract).read_text());now=parse_time(ns.now) if ns.now else dt.datetime.now(UTC)
    result=evaluate(contract,now,github_receipt_creation(ns.repo,os.environ.get('GITHUB_TOKEN','')))
    pathlib.Path(ns.out).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,sort_keys=True))
    return 0 if result['transition_liveness_pass'] else 3

if __name__=='__main__':raise SystemExit(main())
