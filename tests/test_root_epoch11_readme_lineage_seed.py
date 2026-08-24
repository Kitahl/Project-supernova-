import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/root_epoch11_readme_lineage_seed_v25.json"
SCRIPT = ROOT / "scripts/reconcile_root_epoch11_readme_lineage_seed.py"
WORKFLOW = ROOT / ".github/workflows/supernova-root-epoch11-readme-lineage-seed.yml"
SEED_PATHS = [
    "config/root_epoch11_readme_lineage_seed_v25.json",
    "scripts/reconcile_root_epoch11_readme_lineage_seed.py",
    ".github/workflows/supernova-root-epoch11-readme-lineage-seed.yml",
    "tests/test_root_epoch11_readme_lineage_seed.py",
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeInstallationSeed:
    def __init__(self, policy):
        self.policy = policy
        self.parent = policy["required_seed_base_main_sha"]
        self.state_blob = policy["required_state_blob"]
        self.seed_blobs = dict(policy["installed_seed_blob_pins"])

    def run(self, cmd, cwd=None):
        base = self.policy["required_seed_base_main_sha"]
        trusted = "f" * 40
        if cmd[:2] == ["git", "rev-parse"] and cmd[2] == base + "^{tree}":
            return 0, self.policy["required_seed_base_tree_sha"] + "\n"
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return 0, ""
        if cmd[:2] == ["git", "rev-parse"] and cmd[2] == trusted + "^1":
            return 0, self.parent + "\n"
        if cmd[:4] == ["git", "rev-list", "--count", "--first-parent"]:
            return 0, "1\n"
        if cmd[:3] == ["git", "diff", "--name-status"]:
            return 0, "\n".join("A\t" + path for path in SEED_PATHS) + "\n"
        if cmd[:2] == ["git", "ls-tree"]:
            path = cmd[-1]
            return 0, "100644 blob " + self.blob_at(trusted, path) + "\t" + path + "\n"
        return 1, "unexpected command"

    def blob_at(self, ref, path, cwd=None):
        base = self.policy["required_seed_base_main_sha"]
        if ref == base and path in SEED_PATHS:
            return None
        if path == "config/root_tcb_epoch_v25.json":
            return self.policy["required_current_root_epoch_blob"]
        if path == "state/CURRENT.json":
            return self.state_blob
        return self.seed_blobs.get(path, "e" * 40)


class FakeCandidateSeed:
    HEX40 = __import__("re").compile(r"^[0-9a-f]{40}$")

    def __init__(self, root_tcb, blobs):
        self.root_tcb = root_tcb
        self.blobs = blobs

    def blob_at(self, ref, path, cwd=None):
        return self.blobs.get((ref, path), self.blobs.get(path))

    def load(self, root, path):
        if path == "config/root_tcb_epoch_v25.json":
            return dict(self.root_tcb)
        return json.loads((root / path).read_text(encoding="utf-8"))

    @staticmethod
    def canonical_sha256(value):
        import hashlib
        raw = json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


class RootEpoch11ReadmeLineageSeedTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module("root11_readme_lineage_seed_test", SCRIPT)
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_policy_is_exact_non_circular_four_new_path_seed(self):
        self.assertEqual(self.module.policy_errors(self.policy), [])
        self.assertEqual(self.policy["required_seed_base_main_sha"], "de897f6243707410694a81733a23de4828408693")
        self.assertEqual(self.policy["required_seed_base_tree_sha"], "377cf23f0a40c069675ceb9ef9f9ab64c92b1453")
        self.assertEqual(self.policy["seed_paths"], SEED_PATHS)
        self.assertNotIn(SEED_PATHS[0], self.policy["installed_seed_blob_pins"])
        self.assertEqual(self.policy["policy_self_hash"], "FORBIDDEN_TO_AVOID_CIRCULAR_BINDING")
        self.assertEqual(len(self.policy["required_root_candidate_paths"]), 69)
        self.assertEqual(len(self.policy["expected_root_candidate_blobs"]), 68)
        self.assertEqual(set(self.policy["expected_root_candidate_blobs"]), set(self.policy["required_root_candidate_paths"]) - {"config/root_tcb_epoch_v25.json"})
        self.assertEqual(len(self.policy["root_tcb_dynamic_lineage_bindings"]), 5)
        self.assertEqual(len(set(self.policy["root_tcb_dynamic_lineage_bindings"].values())), 5)

    def test_generic_authority_bootstrap_is_phase_correct_for_lineage_seed(self):
        bootstrap = load_module("authority_bootstrap_for_lineage_seed_test", ROOT / "scripts/reconcile_authority_bootstrap.py")
        roots = bootstrap.bootstrap_root_paths(ROOT)
        self.assertTrue(set(SEED_PATHS).issubset(roots))
        self.assertTrue(all(path.startswith(("config/", "scripts/", "tests/", ".github/workflows/")) for path in SEED_PATHS))

        post_promotion_root_paths = bootstrap.bootstrap_root_paths
        bootstrap.bootstrap_root_paths = lambda trusted_root: post_promotion_root_paths(trusted_root) - set(SEED_PATHS)
        try:
            self.assertEqual(bootstrap.bootstrap_invariant_errors(ROOT, ROOT, SEED_PATHS), [])
        finally:
            bootstrap.bootstrap_root_paths = post_promotion_root_paths

        self.assertEqual(
            bootstrap.bootstrap_invariant_errors(ROOT, ROOT, SEED_PATHS),
            ["bootstrap root self-modification requires installed owner root-transition authorization: " + sorted(SEED_PATHS)[0]],
        )

    def test_installation_fails_on_base_advance_seed_change_or_state_drift(self):
        seed = FakeInstallationSeed(self.policy)
        trusted = "f" * 40
        self.assertEqual(self.module.accepted_seed_installation(trusted, self.policy, seed), (True, ""))
        seed.parent = "a" * 40
        self.assertFalse(self.module.accepted_seed_installation(trusted, self.policy, seed)[0])
        seed.parent = self.policy["required_seed_base_main_sha"]
        seed.seed_blobs[SEED_PATHS[1]] = "a" * 40
        self.assertFalse(self.module.accepted_seed_installation(trusted, self.policy, seed)[0])
        seed.seed_blobs = dict(self.policy["installed_seed_blob_pins"])
        seed.state_blob = "b" * 40
        self.assertFalse(self.module.accepted_seed_installation(trusted, self.policy, seed)[0])

    def test_actions_provenance_rejects_non_actions_or_unbound_run(self):
        trusted, candidate = "1" * 40, "2" * 40
        pr = {"number": 7}
        run = {
            "id": 91,
            "run_attempt": 2,
            "name": "Supernova Root Epoch11 README Lineage Seed",
            "path": ".github/workflows/supernova-root-epoch11-readme-lineage-seed.yml",
            "event": "pull_request_target",
            "head_sha": trusted,
            "head_branch": "main",
            "status": "in_progress",
            "repository": {"full_name": "Kitahl/Project-supernova-"},
            "actor": {"login": "Kitahl"},
            "pull_requests": [{"number": 7, "head": {"sha": candidate}, "base": {"sha": trusted}}],
        }
        self.assertEqual(self.module.actions_provenance_errors(run, pr, trusted, candidate, self.policy, 91, 2), [])
        for key, value in (("event", "workflow_dispatch"), ("path", ".github/workflows/other.yml"), ("head_sha", "3" * 40), ("actor", {"login": "other"})):
            with self.subTest(key=key):
                changed = dict(run)
                changed[key] = value
                self.assertTrue(self.module.actions_provenance_errors(changed, pr, trusted, candidate, self.policy, 91, 2))

    def test_exact_candidate_rejects_wrong_count_and_dynamic_binding(self):
        required = self.policy["required_root_candidate_paths"]
        trusted = "1" * 40
        seed_paths = self.policy["seed_paths"]
        installed = ["2" * 40, "3" * 40, "4" * 40, "5" * 40]
        root_tcb = {key: value for key, value in zip(self.policy["root_tcb_dynamic_lineage_bindings"], [trusted] + installed)}
        normalized = dict(root_tcb)
        for key, sentinel in self.policy["root_tcb_dynamic_lineage_bindings"].items():
            normalized[key] = sentinel
        policy = dict(self.policy)
        fake_blobs = {path: blob for path, blob in policy["expected_root_candidate_blobs"].items()}
        for path, blob in zip(seed_paths, installed):
            fake_blobs[(trusted, path)] = blob
        fake = FakeCandidateSeed(root_tcb, fake_blobs)
        policy["expected_normalized_root_tcb_sha256"] = fake.canonical_sha256(normalized)
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            self.assertEqual(self.module.exact_candidate(tmp, trusted, policy, fake), (True, ""))
            bad_count = dict(policy)
            bad_count["required_root_candidate_paths"] = required[:-1]
            self.assertFalse(self.module.exact_candidate(tmp, trusted, bad_count, fake)[0])
            first = next(iter(root_tcb))
            fake.root_tcb[first] = "9" * 40
            self.assertFalse(self.module.exact_candidate(tmp, trusted, policy, fake)[0])

    def test_missing_countable_admission_or_bootstrap_protection_fails(self):
        class SemanticSeed:
            def load(self, root, path):
                return json.loads((root / path).read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            (tmp / "config").mkdir()
            (tmp / "scripts").mkdir()
            (tmp / "config/countable_control_set_v25.json").write_text(json.dumps({"required_control_paths": SEED_PATHS}), encoding="utf-8")
            (tmp / "config/admission_authority.json").write_text(json.dumps({"trusted_authority_helpers": SEED_PATHS}), encoding="utf-8")
            roles = ["MF01", "MF02", "MF03", "MF04", "MF05", "MM01", "MM02", "MM03", "MM04", "MM05", "MM07", "EXT01", "MM06", "MF06", "BIL00"]
            (tmp / "config/task_registry_v25.json").write_text(json.dumps({"active_task_count": 15, "no_sixteenth_lane": True, "tasks": [{"role_id": role} for role in roles]}), encoding="utf-8")
            literals = "\n".join(repr(path) + "\n" + repr(path) for path in SEED_PATHS)
            (tmp / "scripts/reconcile_authority_bootstrap.py").write_text("ROOTS={" + literals.replace("\n", ",") + "}\n", encoding="utf-8")
            self.assertEqual(self.module.lineage_semantic_errors(tmp, self.policy, SemanticSeed()), [])
            (tmp / "config/countable_control_set_v25.json").write_text(json.dumps({"required_control_paths": SEED_PATHS[:-1]}), encoding="utf-8")
            self.assertTrue(self.module.lineage_semantic_errors(tmp, self.policy, SemanticSeed()))

    def test_trusted_semantic_tuple_is_unpacked_before_lineage_errors(self):
        class Amendment:
            result = (True, "")
            def corrected_candidate_semantics(self, *args):
                return self.result
        amendment = Amendment()
        original = self.module.lineage_semantic_errors
        self.module.lineage_semantic_errors = lambda *args: ["lineage break"]
        try:
            self.assertEqual(self.module.trusted_candidate_semantic_errors(pathlib.Path("."), self.policy, object(), amendment, {}, {}), ["lineage break"])
            amendment.result = (False, "root11 break")
            self.assertEqual(self.module.trusted_candidate_semantic_errors(pathlib.Path("."), self.policy, object(), amendment, {}, {}), ["root11 break"])
        finally:
            self.module.lineage_semantic_errors = original

    def test_privileged_job_never_executes_candidate_code(self):
        candidate, trusted = self.workflow.split("  trusted-seed:", 1)
        self.assertIn("pull_request_target:", self.workflow)
        self.assertNotIn("statuses: write", candidate)
        self.assertIn('GITHUB_TOKEN: ""', candidate)
        self.assertIn("persist-credentials: false", candidate)
        self.assertIn("unittest discover", candidate)
        self.assertIn("statuses: write", trusted)
        self.assertNotIn("contents: write", trusted)
        self.assertIn("reconcile_root_epoch11_readme_lineage_seed.py", trusted)
        self.assertNotIn("validate_bus.py", trusted)
        self.assertNotIn("unittest", trusted)
        self.assertNotIn("git -C candidate", trusted)
        self.assertIn('candidate_bytes_in_privileged_phase": "DATA_ONLY"', POLICY.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
