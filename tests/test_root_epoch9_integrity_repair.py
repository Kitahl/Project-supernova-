import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = '0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa'
EPOCH8_BLOB = 'b98b3378ad90e9c35fd02017ea3a4a0f21320c52'
EPOCH9_BLOB = '9a45b2098cd5870b53f9faa92e52409fa3204c81'
SEED_INSTALL = '7c6cca62c51afd28c0554353331abe172dbee389'


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


class RootEpoch9IntegrityRepairTests(unittest.TestCase):
    def test_root11_binds_epoch10_and_preserves_exact_epoch8_through_epoch10_seed_history(self):
        epoch = load('config/root_tcb_epoch_v25.json')
        self.assertEqual(epoch['schema_version'], 'PS-ROOT-TCB-EPOCH-2.5-11')
        self.assertEqual(epoch['protocol_version'], '2.5')
        self.assertEqual(epoch['task_network_plan_id'], PLAN)
        self.assertEqual(epoch['epoch'], 11)
        self.assertEqual(epoch['previous_epoch_blob'], 'cf74b9c17bf1d763e7d89dc07f9bb74c334f8b59')
        self.assertEqual(epoch['root_epoch9_integrity_repair_seed_install_commit_sha'], SEED_INSTALL)
        self.assertEqual(epoch['root_epoch9_integrity_repair_marker'], 'config/root_epoch9_integrity_repair_epoch_v25.json')
        self.assertEqual(epoch['root_epoch10_scheduler_admission_seed_amendment_install_commit_sha'], 'cff3368586764248f4658603d5278eeb86c375ee')
        self.assertEqual(epoch['minimum_worker_liveness_window_minutes'], 45)
        self.assertEqual(epoch['strict_json_authority_boundary'], 'FINITE_DUPLICATE_FREE_JSON_AND_ALLOW_NAN_FALSE')
        self.assertEqual(epoch['single_authoritative_structural_writer'], 'scripts/reconcile_branch_statuses.py')

    def test_epoch9_marker_is_zero_credit_and_zero_science(self):
        marker = load('config/root_epoch9_integrity_repair_epoch_v25.json')
        self.assertEqual(marker['previous_root_epoch'], 8)
        self.assertEqual(marker['new_root_epoch'], 9)
        self.assertEqual(marker['source_cohort'], 'CAL-BR-011-v25-27955ce6')
        self.assertEqual(marker['source_verifier_head'], 'a58939b12e66ab4604b8f2e5f2033bd70d5c0bd3')
        self.assertEqual(marker['calibration_credit_effect'], 0)
        self.assertEqual(marker['fresh_science_effect'], 'NONE')
        self.assertEqual(marker['runtime_effect'], 'NONE')

    def test_authority_and_bootstrap_are_root11_while_epoch9_helpers_remain(self):
        authority = load('config/admission_authority.json')
        bootstrap = load('config/authority_bootstrap_v25.json')
        self.assertEqual(authority['root_tcb_epoch'], 11)
        self.assertEqual(bootstrap['root_tcb_epoch_required'], 11)
        self.assertEqual(authority['authoritative_structural_status_writer'], 'scripts/reconcile_branch_statuses.py')
        self.assertEqual(authority['structural_status_writer_cardinality'], 1)
        self.assertEqual(authority['strict_json_contract'], 'scripts/strict_json.py')
        self.assertIn('config/root_epoch9_integrity_repair_epoch_v25.json', authority['trusted_authority_helpers'])

    def test_countable_v25_freezes_complete_root11_and_historical_repair_surface(self):
        control = load('config/countable_control_set_v25.json')
        paths = set(control['required_control_paths'])
        self.assertEqual(control['schema_version'], 'PS-COUNTABLE-CONTROL-SET-2.5-26')
        self.assertEqual(control['minimum_worker_liveness_window_minutes'], 45)
        self.assertEqual(control['strict_json_contract'], 'FINITE_DUPLICATE_FREE_JSON_AND_ALLOW_NAN_FALSE')
        required = {
            'scripts/strict_json.py',
            'tests/test_strict_json_contract.py',
            'tests/test_root_epoch9_integrity_repair.py',
            'tests/test_gen11_zero_credit_terminal_transition.py',
            'schemas/mastermind_mm04_replay_payload.schema.json',
            'schemas/branch_report.schema.json',
            '.github/workflows/supernova-pr-target-admission.yml',
            '.github/workflows/supernova-comment-admission.yml',
            '.github/workflows/supernova-open-pr-reconciler.yml',
            'config/root_epoch10_scheduler_admission_seed_amendment_v25.json',
            'scripts/reconcile_root_epoch10_scheduler_admission_seed_amendment.py',
            '.github/workflows/supernova-root-epoch10-scheduler-admission-seed-amendment.yml',
            'scripts/scheduler_admission_guard.py',
            'config/root_epoch11_stageability_repair_seed_v25.json',
            'config/root_epoch11_stageability_repair_epoch_v25.json',
            'scripts/reconcile_root_epoch11_stageability_repair_seed.py',
            '.github/workflows/supernova-root-epoch11-stageability-repair-seed.yml',
        }
        self.assertTrue(required.issubset(paths), sorted(required - paths))

    def test_branch_config_names_single_authority_and_minimum_slack(self):
        cfg = load('branch/CONFIG.json')
        self.assertEqual(cfg['structural_reconciler']['authoritative'], 'scripts/reconcile_branch_statuses.py via supernova-branch-reconciler.yml')
        self.assertIn('non-authoritative', cfg['structural_reconciler']['diagnostic'])
        self.assertGreaterEqual(cfg['minimum_worker_liveness_window_minutes'], 45)

    def test_privileged_publishers_assert_frozen_environment(self):
        for name in ('supernova-pr-target-admission.yml', 'supernova-comment-admission.yml', 'supernova-open-pr-reconciler.yml'):
            text = (ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8')
            with self.subTest(name=name):
                self.assertIn('runs-on: ubuntu-24.04', text)
                self.assertIn("python-version: '3.13.15'", text)
                self.assertIn('assert_validator_environment.py', text)


if __name__ == '__main__':
    unittest.main()
