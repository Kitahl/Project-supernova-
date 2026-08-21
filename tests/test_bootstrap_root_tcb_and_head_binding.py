import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOT = ROOT / "scripts/reconcile_authority_bootstrap.py"
WF = ROOT / ".github/workflows/supernova-authority-bootstrap.yml"


def load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("bootstrap_root_tcb_test", BOOT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BootstrapRootTcbAndHeadBindingTests(unittest.TestCase):
    def test_transitive_write_capable_admission_tcb_is_root_protected(self):
        mod = load_bootstrap_module()
        roots = mod.bootstrap_root_paths(ROOT)
        expected = {
            "config/admission_authority.json",
            "config/authority_bootstrap_v25.json",
            "config/root_tcb_epoch_v25.json",
            "config/root_rotation_seed_v25.json",
            "scripts/reconcile_authority_bootstrap.py",
            "scripts/reconcile_open_prs.py",
            "scripts/reconcile_root_rotation_seed.py",
            "scripts/validate_bus.py",
            "scripts/parent_lineage_guard.py",
            "scripts/transition_guard.py",
            ".github/workflows/supernova-authority-bootstrap.yml",
            ".github/workflows/supernova-bootstrap-completion-reconcile.yml",
            ".github/workflows/supernova-pr-target-admission.yml",
            ".github/workflows/supernova-comment-admission.yml",
            ".github/workflows/supernova-open-pr-reconciler.yml",
            ".github/workflows/supernova-root-rotation-seed.yml",
            "requirements-validation.lock",
        }
        self.assertTrue(expected.issubset(roots), sorted(expected - roots))

    def test_each_root_class_is_rejected_by_normal_bootstrap(self):
        mod = load_bootstrap_module()
        for path in (
            "scripts/reconcile_open_prs.py",
            "scripts/validate_bus.py",
            ".github/workflows/supernova-pr-target-admission.yml",
            ".github/workflows/supernova-bootstrap-completion-reconcile.yml",
            "scripts/reconcile_root_rotation_seed.py",
            "requirements-validation.lock",
        ):
            with self.subTest(path=path):
                errors = mod.bootstrap_invariant_errors(ROOT, ROOT, [path])
                self.assertTrue(any("bootstrap root self-modification" in e for e in errors), errors)

    def test_diagnostic_binding_accepts_only_exact_head_and_base(self):
        mod = load_bootstrap_module()
        a = "a" * 40; b = "b" * 40; c = "c" * 40
        pr = {"head": {"sha": a}, "base": {"sha": b}}
        self.assertEqual(mod.diagnostic_binding_errors(pr, a, b), [])
        self.assertIn("diagnosed head SHA no longer matches current PR head", mod.diagnostic_binding_errors(pr, c, b))
        self.assertIn("diagnosed base SHA no longer matches current PR base", mod.diagnostic_binding_errors(pr, a, c))
        self.assertIn("invalid diagnosed head SHA", mod.diagnostic_binding_errors(pr, "bad", b))
        self.assertIn("invalid diagnosed base SHA", mod.diagnostic_binding_errors(pr, a, "bad"))

    def test_privileged_workflow_passes_immutable_event_head_and_base(self):
        text = WF.read_text(encoding="utf-8")
        self.assertIn("DIAGNOSED_HEAD_SHA: ${{ github.event.pull_request.head.sha }}", text)
        self.assertIn("DIAGNOSED_BASE_SHA: ${{ github.event.pull_request.base.sha }}", text)
        self.assertIn("GITHUB_RUN_ID: ${{ github.run_id }}", text)
        self.assertIn("CANDIDATE_DIAGNOSTICS_RESULT: ${{ needs.candidate-diagnostics.result }}", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("persist-credentials: false", text)

    def test_new_unrooted_status_writer_is_detected(self):
        mod = load_bootstrap_module()
        path = ".github/workflows/supernova-bootstrap-completion-reconcile.yml"
        self.assertTrue(mod.workflow_declares_status_write(ROOT, path))
        self.assertIn(path, mod.bootstrap_root_paths(ROOT))


if __name__ == "__main__":
    unittest.main()
