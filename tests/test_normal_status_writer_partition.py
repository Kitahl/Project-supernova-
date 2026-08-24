import ast
import json
import pathlib
import unittest

from scripts import root_transition_authorization as kernel


ROOT = pathlib.Path(__file__).resolve().parents[1]
NORMAL_CONTEXTS = {
    "supernova/static-control",
    "supernova/report-admission",
    "supernova/transition-admission",
}
PARTITION = {
    "open_main_pr_heads": "scripts/reconcile_open_prs.py",
    "non_pr_active_cohort_heads": "scripts/reconcile_v25_admission.py",
    "legacy_seed_programs": "RECEIPT_CONTEXT_ONLY",
}
OPEN_PR_WORKFLOWS = {
    ".github/workflows/supernova-actions-heartbeat.yml",
    ".github/workflows/supernova-bootstrap-completion-reconcile.yml",
    ".github/workflows/supernova-comment-admission.yml",
    ".github/workflows/supernova-open-pr-reconciler.yml",
    ".github/workflows/supernova-pr-target-admission.yml",
}
V25_WORKFLOW = ".github/workflows/supernova-rest-branch-reconciler.yml"
NORMAL_WRITERS = {
    "reconcile_open_prs.py",
}
ROOT_PROTECTED_LINEAGE_PATHS = {
    "scripts/root_transition_authorization.py",
    "tests/test_normal_status_writer_partition.py",
    "config/root_epoch11_readme_lineage_seed_v25.json",
    "scripts/reconcile_root_epoch11_readme_lineage_seed.py",
    ".github/workflows/supernova-root-epoch11-readme-lineage-seed.yml",
    "tests/test_root_epoch11_readme_lineage_seed.py",
}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def calls_in(node):
    return [child for child in ast.walk(node) if isinstance(child, ast.Call)]


def call_name(call):
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def node_names(node):
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name)
    }


def contains_required_context_lookup(node):
    return any(
        isinstance(child, ast.Constant) and child.value == "required_status_contexts"
        for child in ast.walk(node)
    )


def contains_normal_literal(node):
    return any(
        isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value in NORMAL_CONTEXTS
        for child in ast.walk(node)
    )


def assigned_normal_aliases(tree):
    assignments = [
        assignment
        for assignment in ast.walk(tree)
        if isinstance(assignment, ast.Assign)
        and all(isinstance(target, ast.Name) for target in assignment.targets)
    ]
    aliases = set()
    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            if not (
                contains_required_context_lookup(assignment.value)
                or contains_normal_literal(assignment.value)
                or node_names(assignment.value).intersection(aliases)
            ):
                continue
            for target in assignment.targets:
                if target.id not in aliases:
                    aliases.add(target.id)
                    changed = True
    return aliases


def executable_normal_context_publication(source):
    """Reject publication flow, while allowing inert historical JSON comparisons."""

    tree = ast.parse(source)
    aliases = assigned_normal_aliases(tree)
    for loop in (node for node in ast.walk(tree) if isinstance(node, ast.For)):
        iterator_is_normal = (
            contains_required_context_lookup(loop.iter)
            or contains_normal_literal(loop.iter)
            or bool(node_names(loop.iter).intersection(aliases))
        )
        if iterator_is_normal and any(
            call_name(call) in {"post", "post_status", "status"}
            for call in calls_in(loop)
        ):
            return True
    for call in calls_in(tree):
        if call_name(call) not in {"post", "post_status", "status"}:
            continue
        if contains_normal_literal(call) or node_names(call).intersection(aliases):
            return True
    return False


class NormalStatusWriterPartitionTests(unittest.TestCase):
    def test_frozen_partition_and_kernel_contract_match_every_authority_projection(self):
        expected_kernel = kernel.contract()
        self.assertEqual(expected_kernel, {
            "schema_version": "PS-ROOT-TRANSITION-KERNEL-1",
            "helper": "scripts/root_transition_authorization.py",
            "command": "/supernova-root-authorize v1",
            "command_prefix": "/supernova-root-authorize v1 ",
            "repository_id": 1338642578,
            "owner_user_id": 222771578,
            "max_lifetime_seconds": 1800,
            "bound_fields": [
                "kernel", "repo_id", "owner_id", "pr", "base", "head", "tree",
                "changed_path_blob_manifest_sha256", "predecessor_epoch",
                "successor_epoch", "nonce", "expires",
            ],
        })
        for path in (
            "config/repo_policy.json",
            "config/admission_authority.json",
            "config/authority_bootstrap_v25.json",
            "config/root_tcb_epoch_v25.json",
            "config/countable_control_set_v25.json",
            "config/root_epoch11_stageability_repair_epoch_v25.json",
        ):
            with self.subTest(path=path):
                value = load(path)
                self.assertEqual(value["root_transition_authorization"], expected_kernel)
                self.assertEqual(value["status_writer_partition"], PARTITION)
        self.assertEqual(
            load("config/repo_policy.json")["legacy_seed_normal_context_publication"],
            "FORBIDDEN_RECEIPT_CONTEXT_ONLY",
        )

    def test_bootstrap_freezes_kernel_census_and_installed_lineage_paths(self):
        bootstrap = (ROOT / "scripts/reconcile_authority_bootstrap.py").read_text(encoding="utf-8")
        countable = set(load("config/countable_control_set_v25.json")["required_control_paths"])
        trusted = set(load("config/admission_authority.json")["trusted_authority_helpers"])
        for path in ROOT_PROTECTED_LINEAGE_PATHS:
            with self.subTest(path=path):
                self.assertIn(path, bootstrap)
                self.assertIn(path, countable)
                self.assertIn(path, trusted)

    def test_alias_and_required_list_publication_evasions_are_rejected(self):
        fixtures = {
            "literal-alias-loop": """
NORMAL_CONTEXTS = ["supernova/static-control"]
for context in NORMAL_CONTEXTS:
    post_status("head", context, "success")
""",
            "required-list-alias-loop": """
historical = policy["required_status_contexts"]
for context in historical:
    post_status("head", context, "success")
""",
            "transitive-alias-direct-call": """
normal = "supernova/report-admission"
copied = normal
post_status("head", copied, "success")
""",
        }
        for name, source in fixtures.items():
            with self.subTest(name=name):
                self.assertTrue(executable_normal_context_publication(source))

    def test_historical_seed_policy_declarations_are_permitted_but_executable_publication_is_not(self):
        """Historical JSON may retain declarations; executable publishers may not expand them."""

        normal_publishers = set()
        for script in sorted((ROOT / "scripts").glob("*.py")):
            source = script.read_text(encoding="utf-8")
            if executable_normal_context_publication(source):
                normal_publishers.add(script.name)
        self.assertEqual(normal_publishers, NORMAL_WRITERS)
        for script in sorted((ROOT / "scripts").glob("reconcile_*seed*.py")):
            self.assertNotIn(script.name, normal_publishers, script.name)

    def test_open_prs_owns_all_open_main_heads_and_v25_delegates_them(self):
        open_prs = (ROOT / PARTITION["open_main_pr_heads"]).read_text(encoding="utf-8")
        v25 = (ROOT / PARTITION["non_pr_active_cohort_heads"]).read_text(encoding="utf-8")
        self.assertIn("def open_main_prs():", open_prs)
        self.assertIn("/pulls?state=open&base=main&per_page=100&page={page}", open_prs)
        self.assertIn("for pr in prs:", open_prs)
        self.assertIn("def open_main_pr_heads():", v25)
        self.assertIn("delegated_heads=open_main_pr_heads()", v25)
        self.assertIn("OPEN_MAIN_PR_HEAD_DELEGATED_TO_STRICT_RECONCILER", v25)
        self.assertIn("if ch in delegated_heads:", v25)

    def test_every_writer_workflow_uses_the_single_writer_concurrency_group(self):
        observed = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / ".github/workflows").glob("*.yml")
            if any(
                marker in path.read_text(encoding="utf-8")
                for marker in ("python scripts/reconcile_open_prs.py", "python3 scripts/reconcile_open_prs.py")
            )
        }
        self.assertEqual(observed, OPEN_PR_WORKFLOWS)
        for path in sorted(observed | {V25_WORKFLOW}):
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("group: supernova-required-context-writers", text, path)
            self.assertIn("cancel-in-progress: false", text, path)
        self.assertIn(
            "reconcile_v25_admission.py",
            (ROOT / V25_WORKFLOW).read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
