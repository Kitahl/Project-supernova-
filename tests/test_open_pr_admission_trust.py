import importlib.util
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reconcile_open_prs", ROOT / "scripts/reconcile_open_prs.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


class OpenPrAdmissionTrustTests(unittest.TestCase):
    def pr(self, repo="Kitahl/Project-supernova-", base="main", head="hardening/probe"):
        return {
            "number": 1,
            "base": {"ref": base},
            "head": {"ref": head, "sha": "a" * 40, "repo": {"full_name": repo}},
        }

    def test_same_repo_main_and_allowed_prefix_required(self):
        self.assertEqual(MOD.pr_metadata_errors(self.pr()), [])
        self.assertIn(
            "PR head repository is not canonical repository",
            MOD.pr_metadata_errors(self.pr(repo="someone/fork")),
        )
        self.assertIn("PR base is not main", MOD.pr_metadata_errors(self.pr(base="dev")))
        self.assertIn(
            "PR head prefix is not admitted",
            MOD.pr_metadata_errors(self.pr(head="feature/untrusted")),
        )

    def test_authority_byte_drift_is_detected(self):
        changed = [
            "scripts/validate_bus.py",
            "tests/test_ci_guard.py",
            "schemas/state.schema.json",
            "config/repo_policy.json",
            ".github/workflows/supernova-v25-admission.yml",
            "requirements-validation.lock",
        ]
        self.assertEqual(MOD.authority_path_changes(changed), sorted(changed))
        self.assertEqual(
            MOD.authority_path_changes(
                ["state/CURRENT.json", "history/C/CONSOLIDATION.json", "benchmark/registry.json"]
            ),
            [],
        )

    def test_stale_head_is_not_descendant_of_current_trusted_main(self):
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Supernova Test"], cwd=repo, check=True)
            (repo / "f").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "f"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

            subprocess.run(["git", "checkout", "-qb", "candidate"], cwd=repo, check=True)
            (repo / "f").write_text("candidate\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-qam", "candidate"], cwd=repo, check=True)
            candidate = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

            subprocess.run(["git", "checkout", "-q", "-"], cwd=repo, check=True)
            (repo / "g").write_text("new-main\n", encoding="utf-8")
            subprocess.run(["git", "add", "g"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "new main"], cwd=repo, check=True)
            current_main = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

            self.assertTrue(MOD.is_ancestor(repo, base, candidate))
            self.assertFalse(MOD.is_ancestor(repo, current_main, candidate))


if __name__ == "__main__":
    unittest.main()
