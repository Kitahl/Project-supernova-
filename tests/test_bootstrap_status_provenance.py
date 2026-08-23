import importlib.util
import os
import pathlib
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/reconcile_open_prs.py'


def load_module():
    spec=importlib.util.spec_from_file_location('bootstrap_provenance_test',SCRIPT)
    module=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(module); return module


class BootstrapStatusProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.mod=load_module(); self.head='a'*40; self.base='b'*40; self.pr=42; self.run_id=123456

    def status(self,run_id=None,**overrides):
        rid=self.run_id if run_id is None else run_id
        s={'context':self.mod.BOOTSTRAP_CONTEXT,'state':'success','creator':{'login':self.mod.BOOTSTRAP_CREATOR},'description':self.mod.expected_bootstrap_description(self.pr,self.head,self.base),'target_url':f'https://github.com/{self.mod.REPO}/actions/runs/{rid}'}
        s.update(overrides); return s

    def run_obj(self,run_id=None,**overrides):
        rid=self.run_id if run_id is None else run_id
        r={'id':rid,'path':self.mod.BOOTSTRAP_WORKFLOW,'event':'pull_request_target','status':'completed','conclusion':'success','repository':{'full_name':self.mod.REPO},'actor':{'login':self.mod.OWNER},'head_sha':self.head,'pull_requests':[{'number':self.pr,'head':{'sha':self.head},'base':{'sha':self.base}}]}
        r.update(overrides); return r

    def current_pr(self,**overrides):
        value={'number':self.pr,'head':{'sha':self.head,'ref':'root-rotation/test','repo':{'full_name':self.mod.REPO}},'base':{'sha':self.base}}
        value.update(overrides);return value

    def fake_api(self,statuses,runs=None,current_pr=None):
        runs=dict(runs or {self.run_id:self.run_obj()})
        current=self.current_pr() if current_pr is None else current_pr
        def call(path,method='GET',data=None):
            if path.startswith('/commits/'): return statuses
            if path==f'/pulls/{self.pr}':return current
            prefix='/actions/runs/'
            if path.startswith(prefix):
                rid=int(path[len(prefix):])
                if rid in runs:return runs[rid]
            raise AssertionError(path)
        return call

    def check(self,statuses,run_obj=None,*,base=None,pr=None,completed='DEFAULT',runs=None,current_pr=None):
        if runs is None:
            runs={self.run_id:self.run_obj() if run_obj is None else run_obj}
        env={}
        if completed=='DEFAULT': env['COMPLETED_BOOTSTRAP_RUN_ID']=str(self.run_id)
        elif completed is not None: env['COMPLETED_BOOTSTRAP_RUN_ID']=str(completed)
        with mock.patch.dict(os.environ,env,clear=True), mock.patch.object(self.mod,'api',side_effect=self.fake_api(statuses,runs,current_pr)):
            return self.mod.trusted_bootstrap_success(self.head,self.base if base is None else base,self.pr if pr is None else pr)

    def test_exact_designated_completed_run_passes(self): self.assertTrue(self.check([self.status()]))
    def test_persistent_rederivation_without_completion_environment_passes(self): self.assertTrue(self.check([self.status()],completed=None))
    def test_wrong_completion_run_id_fails(self): self.assertFalse(self.check([self.status()],completed=self.run_id+1))
    def test_same_principal_wrong_workflow_rejected(self): self.assertFalse(self.check([self.status()],self.run_obj(path='.github/workflows/other.yml')))
    def test_wrong_event_rejected(self): self.assertFalse(self.check([self.status()],self.run_obj(event='push')))
    def test_incomplete_or_failed_run_rejected(self):
        self.assertFalse(self.check([self.status()],self.run_obj(status='in_progress',conclusion=None)))
        self.assertFalse(self.check([self.status()],self.run_obj(status='completed',conclusion='failure')))
    def test_wrong_creator_rejected(self): self.assertFalse(self.check([self.status(creator={'login':'other-app[bot]'})]))
    def test_missing_or_wrong_run_target_rejected(self):
        self.assertFalse(self.check([self.status(target_url=None)])); self.assertFalse(self.check([self.status(target_url='https://example.com/run/123')]))
    def test_description_head_base_pr_binding_required(self):
        self.assertFalse(self.check([self.status(description='trusted-main bootstrap PASS')]))
        self.assertFalse(self.check([self.status()],base='c'*40)); self.assertFalse(self.check([self.status()],pr=43))
    def test_run_head_binding_required(self): self.assertFalse(self.check([self.status()],self.run_obj(head_sha='c'*40)))
    def test_empty_run_pr_association_uses_independent_current_pr_reread(self): self.assertTrue(self.check([self.status()],self.run_obj(pull_requests=[])))
    def test_current_pr_head_binding_required(self):
        current=self.current_pr(head={'sha':'c'*40,'ref':'root-rotation/test','repo':{'full_name':self.mod.REPO}})
        self.assertFalse(self.check([self.status()],current_pr=current))
    def test_current_pr_base_binding_required(self):
        current=self.current_pr(base={'sha':'c'*40})
        self.assertFalse(self.check([self.status()],current_pr=current))
    def test_wrong_repository_or_actor_rejected(self):
        self.assertFalse(self.check([self.status()],self.run_obj(repository={'full_name':'other/repo'})))
        self.assertFalse(self.check([self.status()],self.run_obj(actor={'login':'other'})))
    def test_ambiguous_multiple_valid_designated_runs_fail_closed(self):
        other=self.run_id+9
        statuses=[self.status(),self.status(run_id=other)]
        runs={self.run_id:self.run_obj(),other:self.run_obj(run_id=other)}
        self.assertFalse(self.check(statuses,completed=None,runs=runs))
    def test_durable_policy_marker_is_explicit(self):
        self.assertEqual(self.mod.DURABLE_BOOTSTRAP_PROVENANCE,'PERSISTENT_GITHUB_WORKFLOW_RUN_REDERIVATION_AND_EXACT_PR_HEAD_BASE_REQUIRED')

if __name__=='__main__':unittest.main()
