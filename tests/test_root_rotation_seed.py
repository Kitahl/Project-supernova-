import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
POLICY=ROOT/'config/root_rotation_seed_v25.json'
SCRIPT=ROOT/'scripts/reconcile_root_rotation_seed.py'
WORKFLOW=ROOT/'.github/workflows/supernova-root-rotation-seed.yml'

class RootRotationSeedTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(POLICY.read_text(encoding='utf-8'))

    def test_seed_is_one_shot_and_cannot_modify_itself(self):
        self.assertEqual(self.p['one_shot_marker_path'],'config/root_tcb_epoch_v25.json')
        self.assertEqual(self.p['one_shot_rule'],'SEED_REFUSES_ONCE_MARKER_EXISTS_ON_ACCEPTED_MAIN')
        self.assertEqual(self.p['seed_self_modification'],'FORBIDDEN')
        self.assertTrue(set(self.p['seed_paths']).isdisjoint(self.p['allowed_root_candidate_paths']))

    def test_root_candidate_scope_is_exact_and_non_scientific(self):
        allowed=set(self.p['allowed_root_candidate_paths'])
        required=set(self.p['required_root_candidate_paths'])
        self.assertTrue(required.issubset(allowed))
        for forbidden in ('state/','control/','assignments/','runtime/','benchmark/','research/'):
            self.assertIn(forbidden,self.p['forbidden_candidate_prefixes'])
        self.assertIn('scripts/reconcile_authority_bootstrap.py',required)
        self.assertIn('scripts/reconcile_open_prs.py',required)
        self.assertIn('.github/workflows/supernova-authority-bootstrap.yml',required)
        self.assertIn('.github/workflows/supernova-bootstrap-completion-reconcile.yml',required)

    def test_seed_script_binds_exact_event_bytes_and_accepted_main(self):
        text=SCRIPT.read_text(encoding='utf-8')
        for needle in (
            "DIAGNOSED_HEAD_SHA","DIAGNOSED_BASE_SHA","diagnosed base is not exact accepted main",
            "candidate does not descend from exact accepted main","state changed in root rotation candidate",
            "root epoch marker already exists; seed is permanently inert","seed self-modification forbidden",
        ):
            self.assertIn(needle,text)

    def test_privileged_seed_never_checks_out_candidate_with_write_token(self):
        text=WORKFLOW.read_text(encoding='utf-8')
        self.assertIn("persist-credentials: false",text)
        self.assertIn("GITHUB_TOKEN: ''",text)
        self.assertIn("statuses: write",text)
        self.assertIn("cd trusted && python3 scripts/reconcile_root_rotation_seed.py",text)
        self.assertIn("DIAGNOSED_HEAD_SHA: ${{ github.event.pull_request.head.sha }}",text)
        self.assertIn("DIAGNOSED_BASE_SHA: ${{ github.event.pull_request.base.sha }}",text)

if __name__=='__main__': unittest.main()
