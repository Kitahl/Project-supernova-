# Retrigger nonce: exact-scope repair-reset seed retry 2; semantics unchanged.
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/reconcile_open_prs.py'
OLD_BLOB='856481759722e23ff9a652ce140f304efe13b023'
OLD_COHORT='CAL-BR-007-v25-c13b6ee4'
OLD_G='7c182fb7ce3a3941f86f7508bbb4a18152402bb8'


def mod():
    s=importlib.util.spec_from_file_location('gen7_reset',SCRIPT);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def candidate(tmp):
    root=pathlib.Path(tmp);(root/'state').mkdir();(root/'superseded').mkdir()
    state={'generation_seq':8,'active_parent_state_git_identity':OLD_BLOB,'active_cohort_id':'STAGING-8','calibration_countable_current':False,'calibration_streak':0,'fresh_allowed_globally':False,'superseded_cohorts':[OLD_COHORT]}
    (root/'state/CURRENT.json').write_text(json.dumps(state),encoding='utf-8')
    receipt={'schema_version':'PS-COHORT-SUPERSESSION-1','cohort_id':OLD_COHORT,'generation_head_sha':OLD_G,'state_blob_sha':OLD_BLOB,'disposition':'INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS','calibration_credit':0,'fresh_evidence_consumed':False,'replacement_generation_seq':8,'replacement_countable':False}
    (root/f'superseded/{OLD_COHORT}.json').write_text(json.dumps(receipt),encoding='utf-8')
    return root

class Gen7RepairResetTests(unittest.TestCase):
    def old(self):return {'generation_seq':7,'active_cohort_id':OLD_COHORT,'generation_head_sha':OLD_G,'calibration_countable_current':True,'calibration_streak':0,'fresh_allowed_globally':False}
    def check(self,root,old=None,blob=OLD_BLOB):
        m=mod()
        with mock.patch.object(m,'run',return_value=(0,blob+'\n')):
            return m.exact_invalidated_gen7_repair_parent(root,'a'*40,self.old() if old is None else old,['state/CURRENT.json',f'superseded/{OLD_COHORT}.json'])
    def test_exact_zero_credit_reset_passes(self):
        with tempfile.TemporaryDirectory() as d:self.assertTrue(self.check(candidate(d)))
    def test_wrong_parent_blob_fails(self):
        with tempfile.TemporaryDirectory() as d:self.assertFalse(self.check(candidate(d),blob='d'*40))
    def test_wrong_old_generation_fails(self):
        with tempfile.TemporaryDirectory() as d:
            o=self.old();o['generation_seq']=6;self.assertFalse(self.check(candidate(d),old=o))
    def test_credit_or_fresh_mutation_fails(self):
        for field,value in [('calibration_credit',1),('fresh_evidence_consumed',True)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as d:
                r=candidate(d);p=r/f'superseded/{OLD_COHORT}.json';x=json.loads(p.read_text());x[field]=value;p.write_text(json.dumps(x));self.assertFalse(self.check(r))
    def test_successor_must_be_noncountable_streak_zero_fresh_false(self):
        for field,value in [('calibration_countable_current',True),('calibration_streak',1),('fresh_allowed_globally',True)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as d:
                r=candidate(d);p=r/'state/CURRENT.json';x=json.loads(p.read_text());x[field]=value;p.write_text(json.dumps(x));self.assertFalse(self.check(r))
    def test_missing_supersession_receipt_fails(self):
        with tempfile.TemporaryDirectory() as d:
            r=candidate(d);(r/f'superseded/{OLD_COHORT}.json').unlink();self.assertFalse(self.check(r))

if __name__=='__main__':unittest.main()
