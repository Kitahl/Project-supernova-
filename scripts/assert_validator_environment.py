#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/validator_environment_v25.json'


def load_contract(path: pathlib.Path=CONFIG) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _git_version() -> str:
    p=subprocess.run(['git','--version'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    if p.returncode:
        return ''
    text=p.stdout.strip()
    return text.removeprefix('git version ').strip()


def _runner_image() -> str:
    explicit=os.environ.get('SUPERNOVA_RUNNER_IMAGE')
    if explicit:
        return explicit
    image_os=os.environ.get('ImageOS','')
    if image_os=='ubuntu24':
        return 'ubuntu-24.04'
    if image_os=='ubuntu22':
        return 'ubuntu-22.04'
    if image_os:
        return image_os
    try:
        values={}
        for line in pathlib.Path('/etc/os-release').read_text(encoding='utf-8').splitlines():
            if '=' in line:
                k,v=line.split('=',1); values[k]=v.strip().strip('"')
        if values.get('ID')=='ubuntu' and values.get('VERSION_ID'):
            return 'ubuntu-'+values['VERSION_ID']
    except Exception:
        pass
    return ''


def observe() -> dict:
    return {
        'runner_image': _runner_image(),
        'runner_image_version': os.environ.get('SUPERNOVA_RUNNER_IMAGE_VERSION') or os.environ.get('ImageVersion',''),
        'python_version': os.environ.get('SUPERNOVA_PYTHON_VERSION') or platform.python_version(),
        'git_version': os.environ.get('SUPERNOVA_GIT_VERSION') or _git_version(),
    }


def errors(contract: dict, observed: dict) -> list[str]:
    out=[]
    for key in ('runner_image','runner_image_version','python_version','git_version'):
        expected=contract.get(key); got=observed.get(key)
        if not isinstance(expected,str) or not expected:
            out.append('validator environment contract missing '+key)
        elif got!=expected:
            out.append(f'validator environment mismatch {key}: expected={expected!r} observed={got!r}')
    return out


def main() -> int:
    contract=load_contract(); observed=observe(); e=errors(contract,observed)
    print(json.dumps({'contract':{k:contract.get(k) for k in ('runner_image','runner_image_version','python_version','git_version')},'observed':observed,'status':'PASS' if not e else 'FAIL'},sort_keys=True))
    if e:
        for x in e: print('VALIDATOR ENVIRONMENT FAILED:',x,file=sys.stderr)
        return 1
    print('VALIDATOR ENVIRONMENT PASS')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
