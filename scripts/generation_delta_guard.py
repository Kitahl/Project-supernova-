#!/usr/bin/env python3
from __future__ import annotations
import argparse, pathlib, subprocess
import strict_json

ROOT=pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH=ROOT/'config/generation_delta_policy_v25.json'


def git(*args: str) -> tuple[int,str,str]:
    p=subprocess.run(['git','-C',str(ROOT),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    return p.returncode,p.stdout.strip(),p.stderr.strip()


def load_policy() -> dict:
    return strict_json.loads(POLICY_PATH.read_text(encoding='utf-8'))


def expected_paths(cohort: str, countable: bool, policy: dict | None=None) -> list[str]:
    p=policy or load_policy()
    key='countable' if countable else 'non_countable'
    block=p[key]
    paths=[x.format(cohort=cohort) for x in block['exact_path_templates']]
    if len(paths)!=block['exact_cardinality']:
        raise ValueError('generation delta policy cardinality mismatch')
    if len(paths)!=len(set(paths)):
        raise ValueError('generation delta policy contains duplicate paths')
    if countable:
        if block.get('exact_cardinality') != 4 or f'scheduler/{cohort}.json' not in paths:
            raise ValueError('countable generation must freeze scheduler manifest as fourth path')
        if block.get('scheduler_admission_required_before_promotion') is not True:
            raise ValueError('countable scheduler admission gate disabled')
    return paths


def validate_names(names: list[str], cohort: str, countable: bool, policy: dict | None=None) -> list[str]:
    expected=expected_paths(cohort,countable,policy)
    got=sorted(names); want=sorted(expected)
    errors=[]
    if got!=want:
        missing=sorted(set(want)-set(got)); extra=sorted(set(got)-set(want))
        if missing: errors.append('generation delta missing: '+','.join(missing))
        if extra: errors.append('generation delta extra: '+','.join(extra))
        if not missing and not extra: errors.append('generation delta does not equal canonical policy')
    return errors


def validate_git(root_sha: str, generation_sha: str, cohort: str, countable: bool) -> list[str]:
    rc,out,err=git('diff','--name-only',root_sha,generation_sha)
    if rc:
        return ['cannot compute generation delta: '+(err or 'git diff failed')]
    names=[x for x in out.splitlines() if x]
    return validate_names(names,cohort,countable)


def main() -> int:
    q=argparse.ArgumentParser()
    q.add_argument('--root-sha',required=True)
    q.add_argument('--generation-head',required=True)
    q.add_argument('--cohort',required=True)
    q.add_argument('--countable',action='store_true')
    a=q.parse_args()
    errors=validate_git(a.root_sha,a.generation_head,a.cohort,a.countable)
    if errors:
        print('GENERATION DELTA POLICY FAILED')
        for e in errors: print('-',e)
        return 1
    print('GENERATION DELTA POLICY PASS')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
