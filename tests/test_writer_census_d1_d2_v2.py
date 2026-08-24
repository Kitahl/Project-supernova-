import ast
import json
import os
import pathlib
import re
import textwrap
import unittest
from unittest import mock

from scripts import reconcile_open_prs as open_prs


ROOT = pathlib.Path(__file__).resolve().parents[1]
NORMAL = {
    "supernova/static-control",
    "supernova/report-admission",
    "supernova/transition-admission",
}
CALLERS = {
    "scripts/reconcile_open_prs.py": {
        ".github/workflows/supernova-actions-heartbeat.yml",
        ".github/workflows/supernova-bootstrap-completion-reconcile.yml",
        ".github/workflows/supernova-comment-admission.yml",
        ".github/workflows/supernova-open-pr-reconciler.yml",
        ".github/workflows/supernova-pr-target-admission.yml",
    },
    "scripts/reconcile_v25_admission.py": {
        ".github/workflows/supernova-rest-branch-reconciler.yml",
    },
}
INLINE = {
    ".github/workflows/supernova-actions-heartbeat.yml": {
        "supernova/actions-heartbeat",
    },
    ".github/workflows/supernova-comment-admission.yml": {
        "supernova/actions-comment-heartbeat",
    },
    ".github/workflows/supernova-liveness-monitor.yml": {"supernova/liveness"},
    ".github/workflows/supernova-pr-target-admission.yml": {
        "supernova/actions-pr-target-heartbeat",
    },
}
RECEIPTS = {
    "reconcile_gen7_repair_reset_seed.py": "supernova/gen7-repair-reset-seed",
    "reconcile_gen9_reset_compat_seed.py": "supernova/gen9-reset-compat-seed",
    "reconcile_root_epoch10_scheduler_admission_seed_amendment.py": "supernova/root-epoch10-scheduler-admission-seed-amendment",
    "reconcile_root_epoch10_scheduler_admission_seed.py": "supernova/root-epoch10-scheduler-admission-seed",
    "reconcile_root_epoch11_readme_lineage_seed.py": "supernova/root-epoch11-readme-lineage-seed",
    "reconcile_root_epoch11_stageability_repair_seed_amendment.py": "supernova/root-epoch11-stageability-repair-seed-amendment",
    "reconcile_root_epoch11_stageability_repair_seed.py": "supernova/root-epoch11-stageability-repair-seed",
    "reconcile_root_epoch6_repair_seed.py": "supernova/root-epoch6-repair-seed",
    "reconcile_root_epoch7_repair_seed.py": "supernova/root-epoch7-repair-seed",
    "reconcile_root_epoch8_status_writer_repair_seed.py": "supernova/root-epoch8-status-writer-repair-seed",
    "reconcile_root_epoch9_integrity_repair_seed.py": "supernova/root-epoch9-integrity-repair-seed",
    "reconcile_root_rotation_seed.py": "supernova/root-rotation-seed",
    "reconcile_structural_status_rotation_seed.py": "supernova/structural-status-rotation-seed",
    "reconcile_t0_trust_repair_seed.py": "supernova/t0-trust-repair-seed",
}
SEED_CONFIGS = {
    "reconcile_gen7_repair_reset_seed.py": "config/gen7_repair_reset_seed_v25.json",
    "reconcile_gen9_reset_compat_seed.py": "config/gen9_reset_compat_seed_v25.json",
    "reconcile_root_epoch10_scheduler_admission_seed_amendment.py": "config/root_epoch10_scheduler_admission_seed_amendment_v25.json",
    "reconcile_root_epoch10_scheduler_admission_seed.py": "config/root_epoch10_scheduler_admission_seed_v25.json",
    "reconcile_root_epoch11_stageability_repair_seed_amendment.py": "config/root_epoch11_stageability_repair_seed_amendment_v25.json",
    "reconcile_root_epoch6_repair_seed.py": "config/root_epoch6_repair_seed_v25.json",
    "reconcile_root_epoch7_repair_seed.py": "config/root_epoch7_repair_seed_v25.json",
    "reconcile_root_epoch8_status_writer_repair_seed.py": "config/root_epoch8_status_writer_repair_seed_v25.json",
    "reconcile_root_epoch9_integrity_repair_seed.py": "config/root_epoch9_integrity_repair_seed_v25.json",
    "reconcile_root_rotation_seed.py": "config/root_rotation_seed_v25.json",
    "reconcile_structural_status_rotation_seed.py": "config/structural_status_rotation_seed_v25.json",
    "reconcile_t0_trust_repair_seed.py": "config/t0_trust_repair_seed_v25.json",
}
LOCAL_RECEIPTS = {
    "reconcile_root_epoch11_readme_lineage_seed.py",
    "reconcile_root_epoch11_stageability_repair_seed.py",
}
NON_RAW_SEEDS = {
    "reconcile_root_epoch11_readme_lineage_seed.py",
    "reconcile_root_epoch11_stageability_repair_seed_amendment.py",
}
AUXILIARY_RAW = {
    "diagnose_authority_bootstrap.py",
    "reconcile_authority_bootstrap.py",
    "reconcile_branch_statuses.py",
    "reconcile_preactivation_admission.py",
    "reconcile_ruleset_attestation.py",
    "reconcile_v25_admission.py",
}
RUN = re.compile(r"^(?P<indent> *)run:\s*(?P<value>.*)$")
HEREDOC = re.compile(r"^(?:python|python3)\s+-\s+<<['\"]?([A-Za-z0-9_]+)['\"]?$")


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def calls(node):
    return [item for item in ast.walk(node) if isinstance(item, ast.Call)]


def call_name(call):
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def reference_key(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = reference_key(node.value)
        return (parent + "." if parent else "") + node.attr
    return None


def assignments(tree):
    result = {}
    for item in ast.walk(tree):
        if isinstance(item, ast.Assign):
            targets, value = item.targets, item.value
        elif isinstance(item, ast.AnnAssign):
            targets, value = (item.target,), item.value
        else:
            continue
        if value is None:
            continue
        for target in targets:
            key = reference_key(target)
            if key is not None:
                result.setdefault(key, []).append(value)
    return result


def strings(node, env, seen=frozenset()):
    """Bounded dataflow: follows names/attributes and data expressions, never bodies."""

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    key = reference_key(node)
    if key is not None:
        if key in seen:
            return set()
        return set().union(
            *(strings(value, env, seen | {key}) for value in env.get(key, ()))
        ) if key in env else set()
    if isinstance(node, ast.JoinedStr):
        children = node.values
    elif isinstance(node, ast.FormattedValue):
        children = (node.value,)
    elif isinstance(node, ast.BinOp):
        children = (node.left, node.right)
    elif isinstance(node, ast.Subscript):
        children = (node.value, node.slice)
    elif isinstance(node, ast.Dict):
        children = tuple(node.keys) + tuple(node.values)
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        children = node.elts
    elif isinstance(node, ast.Call):
        children = (
            tuple(node.args) + tuple(keyword.value for keyword in node.keywords)
            + ((node.func.value,) if isinstance(node.func, ast.Attribute) else ())
        )
    else:
        children = ()
    return set().union(*(strings(child, env, seen) for child in children if child is not None))


def status_post(call, env):
    found = set().union(
        *(strings(item, env) for item in tuple(call.args) + tuple(key.value for key in call.keywords))
    )
    endpoint = any("/statuses/" in item for item in found)
    return endpoint and (
        "POST" in found or call_name(call) == "status_api"
    )


def context_values(node, env, seen=frozenset()):
    key = reference_key(node)
    if key is not None and key not in seen and key in env:
        return set().union(
            *(context_values(value, env, seen | {key}) for value in env[key])
        )
    if isinstance(node, ast.Dict):
        result = set()
        for key_node, value in zip(node.keys, node.values):
            if key_node is None:
                continue
            if "context" in strings(key_node, env):
                result.update(strings(value, env))
            result.update(context_values(value, env, seen))
        return result
    if isinstance(node, ast.Call):
        children = (
            tuple(node.args) + tuple(key.value for key in node.keywords)
            + ((node.func.value,) if isinstance(node.func, ast.Attribute) else ())
        )
        return set().union(*(context_values(child, env, seen) for child in children))
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return set().union(*(context_values(child, env, seen) for child in node.elts))
    return set()


def raw_contexts(call, env):
    found = set()
    for keyword in call.keywords:
        if keyword.arg == "context":
            found.update(strings(keyword.value, env))
        elif keyword.arg in {"body", "data", "json", "payload"}:
            found.update(context_values(keyword.value, env))
    for argument in call.args:
        found.update(context_values(argument, env))
    return {item for item in found if item.startswith("supernova/")}


def functions(tree):
    return {
        item.name: item for item in ast.walk(tree)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def context_slots(function):
    positional = {
        index for index, arg in enumerate(function.args.args)
        if arg.arg in {"context", "ctx"}
    }
    keywords = {
        arg.arg for arg in tuple(function.args.args) + tuple(function.args.kwonlyargs)
        if arg.arg in {"context", "ctx"}
    }
    return positional, keywords


def argument_from_slot(call, slots):
    positions, names = slots
    result = []
    result.extend(call.args[index] for index in positions if index < len(call.args))
    result.extend(
        keyword.value for keyword in call.keywords if keyword.arg in names
    )
    return result


def status_wrappers(tree):
    env, definitions = assignments(tree), functions(tree)
    result = {
        fname: context_slots(function)
        for fname, function in definitions.items()
        if any(context_slots(function))
        and any(status_post(call, env) for call in calls(function))
    }
    changed = True
    while changed:
        changed = False
        for fname, function in definitions.items():
            own = context_slots(function)
            parameters = {
                argument.arg for argument in tuple(function.args.args) + tuple(function.args.kwonlyargs)
            }
            if fname in result or not any(own):
                continue
            for call in calls(function):
                target = result.get(call_name(call))
                if target is None:
                    continue
                if any(
                    isinstance(argument, ast.Name) and argument.id in parameters
                    for argument in argument_from_slot(call, target)
                ):
                    result[fname] = own
                    changed = True
                    break
    return result


def normal_aliases(tree):
    aliases, changed = set(), True
    statements = [
        item for item in ast.walk(tree)
        if isinstance(item, (ast.Assign, ast.AnnAssign))
    ]
    while changed:
        changed = False
        for statement in statements:
            value = statement.value
            if value is None:
                continue
            descendants = list(ast.walk(value))
            relevant = any(
                isinstance(node, ast.Constant)
                and node.value in NORMAL | {"required_status_contexts"}
                for node in descendants
            ) or any(
                isinstance(node, ast.Name) and node.id in aliases
                for node in descendants
            )
            targets = statement.targets if isinstance(statement, ast.Assign) else (statement.target,)
            if not relevant:
                continue
            for target in targets:
                key = reference_key(target)
                if key is not None and key not in aliases:
                    aliases.add(key)
                    changed = True
    return aliases


def is_normal(node, aliases):
    return any(
        isinstance(item, ast.Constant) and item.value in NORMAL
        for item in ast.walk(node)
    ) or any(
        reference_key(item) in aliases
        for item in ast.walk(node)
        if isinstance(item, (ast.Name, ast.Attribute))
    )


def normal_publication(source):
    tree, env = ast.parse(source), None
    env, wrappers, aliases = assignments(tree), status_wrappers(tree), normal_aliases(tree)
    for call in calls(tree):
        if status_post(call, env) and raw_contexts(call, env).intersection(NORMAL):
            return True
    for loop in (item for item in ast.walk(tree) if isinstance(item, ast.For)):
        targets = {
            reference_key(item) for item in ast.walk(loop.target)
            if reference_key(item) is not None
        }
        if not is_normal(loop.iter, aliases):
            continue
        for call in calls(loop):
            for argument in argument_from_slot(call, wrappers.get(call_name(call), (set(), set()))):
                if reference_key(argument) in targets:
                    return True
    return any(
        any(is_normal(argument, aliases) for argument in argument_from_slot(call, slots))
        for call in calls(tree)
        for slots in (wrappers.get(call_name(call), (set(), set())),)
    )


def contains_seed_context(node):
    return any(
        isinstance(item, ast.Subscript)
        and any(
            isinstance(descendant, ast.Constant) and descendant.value == "seed_context"
            for descendant in ast.walk(item.slice)
        )
        for item in ast.walk(node)
    )


def runtime_receipts(source, configured_receipt):
    tree, env, result = ast.parse(source), None, set()
    env = assignments(tree)
    for call in calls(tree):
        if call_name(call) != "post":
            continue
        argument = (
            call.args[1] if len(call.args) > 1 else next(
                (key.value for key in call.keywords if key.arg in {"context", "ctx"}),
                None,
            )
        )
        if argument is None:
            continue
        result.update(item for item in strings(argument, env) if item.startswith("supernova/"))
        if contains_seed_context(argument):
            result.add(configured_receipt)
    return result


def yaml_runs(text):
    lines, result, index = text.splitlines(), [], 0
    while index < len(lines):
        match = None if lines[index].lstrip().startswith("#") else RUN.match(lines[index])
        if match is None:
            index += 1
            continue
        indent, value = len(match.group("indent")), match.group("value").strip()
        index += 1
        if value.startswith("#"):
            continue
        if value not in {"|", "|-", "|+", ">", ">-", ">+"}:
            result.append(value)
            continue
        block = []
        while index < len(lines):
            candidate = lines[index]
            if candidate.strip() and len(candidate) - len(candidate.lstrip(" ")) <= indent:
                break
            block.append(candidate)
            index += 1
        result.append("\n".join(block))
    return result


def python_blocks(run):
    lines, result, index = run.splitlines(), [], 0
    while index < len(lines):
        match = HEREDOC.match(lines[index].strip())
        if match is None:
            index += 1
            continue
        index, body = index + 1, []
        while index < len(lines) and lines[index].strip() != match.group(1):
            body.append(lines[index])
            index += 1
        if index < len(lines):
            result.append(textwrap.dedent("\n".join(body)))
        index += 1
    return result


def inline_contexts(run):
    result = set()
    for source in python_blocks(run):
        tree, env = ast.parse(source), None
        env = assignments(tree)
        for call in calls(tree):
            if status_post(call, env):
                result.update(raw_contexts(call, env))
    return result


def inline_writers():
    result = {}
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        contexts = set().union(
            *(inline_contexts(run) for run in yaml_runs(path.read_text(encoding="utf-8")))
        )
        if contexts:
            result[path.relative_to(ROOT).as_posix()] = contexts
    return result


def invoked(run, script):
    command = re.compile(
        rf"(?:^|(?:&&|\|\||;|\|)\s*)(?:python|python3)\s+{re.escape(script)}(?:\s|$)"
    )
    return any(
        not line.strip().startswith("#") and command.search(line.strip())
        for line in run.splitlines()
    )


def workflow_callers():
    result = {script: set() for script in CALLERS}
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        runs = yaml_runs(path.read_text(encoding="utf-8"))
        for script in result:
            if any(invoked(run, script) for run in runs):
                result[script].add(path.relative_to(ROOT).as_posix())
    return result


def pr(number, head, tree, state):
    return {
        "number": number,
        "head": {"sha": head},
        "base": {"sha": "a" * 40},
        "tree": tree,
        "desired": {context: state for context in NORMAL},
    }


class WriterCensusD1D2Tests(unittest.TestCase):
    def test_direct_endpoint_dict_keyword_attribute_annotation_and_wrapper_evasions(self):
        direct = """
class Endpoint:
    pass
Endpoint.url: str = "/statuses/" + sha
Http.POST: str = "POST"
payload: dict = {"context": "supernova/static-control"}
client.request(url=Endpoint.url, method=Http.POST, json=payload)
"""
        tree, env = ast.parse(direct), None
        env = assignments(tree)
        direct_calls = [call for call in calls(tree) if status_post(call, env)]
        self.assertEqual(len(direct_calls), 1)
        self.assertEqual(raw_contexts(direct_calls[0], env), {"supernova/static-control"})
        self.assertTrue(normal_publication(direct))

        wrapper = """
def raw(*, sha, context):
    endpoint: str = "/statuses/" + sha
    Http.POST: str = "POST"
    transport(endpoint=endpoint, method=Http.POST, body={"context": context})
def publish(*, sha, context):
    raw(sha=sha, context=context)
required = policy["required_status_contexts"]
for context in required:
    publish(sha="head", context=context)
"""
        self.assertTrue(normal_publication(wrapper))
        self.assertFalse(normal_publication("""
historical = policy["required_status_contexts"]
assert historical == historical
"""))

    def test_raw_writer_partition_and_runtime_receipt_sets_are_exact(self):
        direct, normal = set(), set()
        for path in (ROOT / "scripts").glob("*.py"):
            source, tree = path.read_text(encoding="utf-8"), None
            tree = ast.parse(source)
            if any(status_post(call, assignments(tree)) for call in calls(tree)):
                direct.add(path.name)
            if normal_publication(source):
                normal.add(path.name)
        self.assertEqual(
            direct,
            {"reconcile_open_prs.py"} | (set(RECEIPTS) - NON_RAW_SEEDS) | AUXILIARY_RAW,
        )
        self.assertEqual(normal, {"reconcile_open_prs.py"})
        self.assertEqual({path.name for path in (ROOT / "scripts").glob("reconcile_*seed*.py")}, set(RECEIPTS))
        self.assertEqual(set(SEED_CONFIGS) | LOCAL_RECEIPTS, set(RECEIPTS))
        self.assertEqual(len(set(RECEIPTS.values())), len(RECEIPTS))
        self.assertTrue(set(RECEIPTS.values()).isdisjoint(NORMAL))
        for script, receipt in RECEIPTS.items():
            source = (ROOT / "scripts" / script).read_text(encoding="utf-8")
            with self.subTest(script=script):
                self.assertEqual(runtime_receipts(source, receipt), {receipt})
                if script in LOCAL_RECEIPTS:
                    self.assertIn(f'RECEIPT_CONTEXT = "{receipt}"', source)
                else:
                    config = SEED_CONFIGS[script]
                    self.assertIn(config, source)
                    self.assertEqual(load(config)["seed_context"], receipt)
                if script in NON_RAW_SEEDS:
                    self.assertIn("seed.post(", source)
                    tree = ast.parse(source)
                    self.assertFalse(any(status_post(call, assignments(tree)) for call in calls(tree)))

    def test_every_yaml_run_block_inline_status_inventory_is_non_normal(self):
        workflows = list((ROOT / ".github/workflows").glob("*.yml"))
        self.assertGreater(sum(len(yaml_runs(path.read_text(encoding="utf-8"))) for path in workflows), 0)
        self.assertEqual(inline_writers(), INLINE)
        self.assertTrue(set().union(*INLINE.values()).isdisjoint(NORMAL))
        fixture = """run: |
  python3 - <<'PY'
  Endpoint.url: str = "/statuses/" + sha
  Http.POST: str = "POST"
  body = {"context": "supernova/diagnostic-only"}
  request(url=Endpoint.url, method=Http.POST, json=body)
  PY
"""
        self.assertEqual(inline_contexts(yaml_runs(fixture)[0]), {"supernova/diagnostic-only"})

    def test_workflow_callers_are_executable_and_all_six_share_the_lock(self):
        self.assertEqual(yaml_runs("# run: python scripts/reconcile_open_prs.py\n"), [])
        self.assertFalse(invoked("# python scripts/reconcile_open_prs.py", "scripts/reconcile_open_prs.py"))
        self.assertEqual(workflow_callers(), CALLERS)
        all_callers = set().union(*CALLERS.values())
        self.assertEqual(len(all_callers), 6)
        self.assertNotIn(
            ".github/workflows/supernova-authority-bootstrap.yml",
            CALLERS["scripts/reconcile_open_prs.py"],
        )
        for path in all_callers:
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("group: supernova-required-context-writers", text)
            self.assertIn("cancel-in-progress: false", text)
        for path in CALLERS["scripts/reconcile_open_prs.py"]:
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("environment: supernova-protected-writer", text)
            self.assertIn("actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1", text)
            self.assertIn("permission-statuses: write", text)
            self.assertIn("SUPERNOVA_STATUS_TOKEN: ${{ steps.status-token.outputs.token }}", text)

    def full_state(self, rows):
        final, posts = {}, []

        def status_api(path, body):
            self.assertRegex(path, r"^/statuses/[0-9a-f]{40}$")
            self.assertIn(body["context"], NORMAL)
            posts.append((path, dict(body)))
            return {}

        def validate(_root, row, trusted_errors):
            self.assertEqual(trusted_errors, [])
            number, head, tree = row["number"], row["head"]["sha"], row["tree"]
            for context, state in row["desired"].items():
                open_prs.post_status(
                    head, context, state, f"binding pr={number} head={head} tree={tree}"
                )
                final[(number, head, tree, context)] = state

        with mock.patch.dict(os.environ, {"SUPERNOVA_STATUS_TOKEN": "app-status-token"}, clear=False), \
             mock.patch.object(open_prs, "status_api", side_effect=status_api), \
             mock.patch.object(open_prs, "trusted_self_check", return_value=[]), \
             mock.patch.object(open_prs, "open_main_prs", return_value=(rows, [])), \
             mock.patch.object(open_prs, "validate_pr", side_effect=validate):
            self.assertEqual(open_prs.main(), 0)
        return final, posts

    def test_repeated_reordered_and_duplicate_free_full_state_runs(self):
        first = pr(41, "1" * 40, "tree-41", "success")
        second = pr(42, "2" * 40, "tree-42", "failure")
        expected, posts = self.full_state([first, second])
        replay, replay_posts = self.full_state([first, second])
        reordered, reordered_posts = self.full_state([second, first])
        self.assertEqual(replay, expected)
        self.assertEqual(reordered, expected)
        self.assertEqual(len(posts), 6)
        self.assertEqual(len(replay_posts), 6)
        self.assertEqual(len(reordered_posts), 6)
        self.assertEqual(len({(path, body["context"]) for path, body in posts}), 6)
        self.assertEqual(sorted(posts, key=repr), sorted(replay_posts, key=repr))
        self.assertEqual(sorted(posts, key=repr), sorted(reordered_posts, key=repr))
        for path, body in posts:
            self.assertIn(f"head={path.rsplit('/', 1)[1]}", body["description"])
            self.assertRegex(body["description"], r"binding pr=4[12] .* tree=tree-4[12]")

    def test_failure_success_replacement_and_later_coalesced_run_cover_skipped_trigger(self):
        failed = pr(51, "3" * 40, "tree-51", "failure")
        passed, skipped = pr(51, "3" * 40, "tree-51", "success"), pr(52, "4" * 40, "tree-52", "success")
        before, _ = self.full_state([failed])
        after, posts = self.full_state([passed, skipped])
        self.assertTrue(all(value == "failure" for value in before.values()))
        self.assertTrue(all(value == "success" for value in after.values()))
        self.assertEqual({path.rsplit("/", 1)[1] for path, _ in posts}, {"3" * 40, "4" * 40})
        self.assertEqual(len(after), 6)

    def test_open_main_prs_paginates_deduplicates_before_later_full_state(self):
        first_page = [{"number": number} for number in range(1, 101)]
        second_page, paths = [{"number": 100}, {"number": 101}], []

        def api(path):
            paths.append(path)
            return first_page if path.endswith("page=1") else second_page if path.endswith("page=2") else self.fail(path)

        with mock.patch.object(open_prs, "api", side_effect=api):
            rows, errors = open_prs.open_main_prs()
        self.assertEqual(errors, [])
        self.assertEqual([row["number"] for row in rows], list(range(1, 102)))
        self.assertEqual(paths, [
            "/pulls?state=open&base=main&per_page=100&page=1",
            "/pulls?state=open&base=main&per_page=100&page=2",
        ])


if __name__ == "__main__":
    unittest.main()
