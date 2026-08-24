import json
import os
import pathlib
import re
import unittest
from unittest import mock

from scripts import reconcile_open_prs as reconciler


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
NORMAL_CONTEXTS = {
    "supernova/static-control",
    "supernova/report-admission",
    "supernova/transition-admission",
}
APP_ACTION = "actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1"
APP_ENVIRONMENT = "supernova-protected-writer"
APP_CLIENT_ID_VARIABLE = "SUPERNOVA_STATUS_APP_CLIENT_ID"
APP_PRIVATE_KEY_SECRET = "SUPERNOVA_STATUS_APP_PRIVATE_KEY"
APP_TOKEN = "SUPERNOVA_STATUS_TOKEN"
EXPRESSION = "$" + "{{"
WORKFLOW_PROTECTED_JOBS = {
    "supernova-actions-heartbeat.yml": "reconcile",
    "supernova-bootstrap-completion-reconcile.yml": "reconcile",
    "supernova-comment-admission.yml": "reconcile",
    "supernova-open-pr-reconciler.yml": "reconcile",
    "supernova-pr-target-admission.yml": "reconcile",
}
WORKFLOW_GENERIC_JOBS = {
    "supernova-actions-heartbeat.yml": {"structural-heartbeat"},
    "supernova-bootstrap-completion-reconcile.yml": set(),
    "supernova-comment-admission.yml": {"structural-comment-heartbeat"},
    "supernova-open-pr-reconciler.yml": set(),
    "supernova-pr-target-admission.yml": {
        "structural-pr-target-heartbeat",
        "structural-ruleset-attestation",
    },
}


class Response:
    status = 200

    def __init__(self, body=b"{}", date="Sat, 23 Aug 2026 00:00:00 GMT"):
        self.body = body
        self.headers = {"Date": date}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def job_blocks(text):
    after_jobs = text.split("\njobs:\n", 1)[1]
    matches = list(re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\s*$", after_jobs))
    result = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(after_jobs)
        result[match.group(1)] = after_jobs[match.start():end]
    return result


def yaml_run_blocks(text):
    lines = text.splitlines()
    result = []
    for index, line in enumerate(lines):
        match = re.match(r"^(?P<indent>\s*)run:\s*(?P<value>.*)$", line)
        if not match:
            continue
        value = match.group("value")
        indent = len(match.group("indent"))
        if value in {"|", "|-", ">", ">-"}:
            body = []
            for child in lines[index + 1:]:
                child_indent = len(child) - len(child.lstrip())
                if child and child_indent <= indent:
                    break
                body.append(child)
            result.append("\n".join(body))
        else:
            result.append(value)
    return result


def yaml_mapping(block, name, indent):
    match = re.search(rf"(?m)^{' ' * indent}{re.escape(name)}:\s*$", block)
    if match is None:
        return None
    result = {}
    for line in block[match.end():].splitlines():
        if not line:
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= indent:
            break
        if line_indent != indent + 2:
            continue
        item = re.match(rf"^{' ' * (indent + 2)}([^:#]+):\s*(.*?)\s*$", line)
        if item:
            result[item.group(1)] = item.group(2)
    return result


def effective_job_permissions(text, job):
    job_permissions = yaml_mapping(job, "permissions", 4)
    if job_permissions is not None:
        return job_permissions
    workflow = text.split("\njobs:\n", 1)[0]
    return yaml_mapping(workflow, "permissions", 0)


def step_blocks(job):
    matches = list(re.finditer(r"(?m)^      - ", job))
    return [
        job[match.start():matches[index + 1].start()].rstrip()
        if index + 1 < len(matches)
        else job[match.start():].rstrip()
        for index, match in enumerate(matches)
    ]


def named_step(job, name):
    expected = "      - name: " + name
    matches = [step for step in step_blocks(job) if step.splitlines()[0] == expected]
    if len(matches) != 1:
        raise AssertionError(f"expected one step {name}, got {len(matches)}")
    return matches[0]


def reconciler_step(job):
    candidates = [
        step for step in step_blocks(job)
        if "reconcile_open_prs.py" in "\n".join(yaml_run_blocks(step))
    ]
    if len(candidates) != 1:
        raise AssertionError(f"expected one executable reconciler step, got {len(candidates)}")
    return candidates[0]


class StatusAppTokenBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.generic = "generic-read-token"
        self.app = "app-status-token"

    def environment(self, **values):
        env = {"GITHUB_TOKEN": self.generic, APP_TOKEN: self.app}
        env.update(values)
        return mock.patch.dict(os.environ, env, clear=True)

    def test_missing_or_malformed_app_token_fails_before_inventory_or_network(self):
        invalid = ("", " ", "\t", " token", "token ", "\n", "token\n")
        for token in invalid:
            with self.subTest(repr(token)), self.environment(**{APP_TOKEN: token}), \
                 mock.patch.object(reconciler, "open_main_prs") as inventory, \
                 mock.patch("urllib.request.urlopen") as urlopen:
                with self.assertRaises(RuntimeError):
                    reconciler.main()
                inventory.assert_not_called()
                urlopen.assert_not_called()

    def test_required_status_token_has_no_generic_fallback_or_secret_echo(self):
        for generic_name in ("GITHUB_TOKEN", "GH_TOKEN"):
            env = {generic_name: self.generic, APP_TOKEN: ""}
            with self.subTest(generic_name=generic_name), mock.patch.dict(
                os.environ, env, clear=True
            ):
                with self.assertRaises(RuntimeError) as raised:
                    reconciler.required_status_token()
            self.assertNotIn(self.generic, str(raised.exception))
        with self.environment():
            self.assertEqual(reconciler.required_status_token(), self.app)

    def test_read_api_is_get_only_and_never_uses_app_token(self):
        requests = []

        def urlopen(request, timeout):
            requests.append((request, timeout))
            return Response()

        with self.environment(), mock.patch(
            "urllib.request.urlopen", side_effect=urlopen
        ):
            self.assertEqual(reconciler.api("/pulls?state=open"), {})
            value, server_date = reconciler.api_with_server_date("/commits/" + self.sha)
        self.assertEqual(value, {})
        self.assertEqual(server_date, "Sat, 23 Aug 2026 00:00:00 GMT")
        self.assertEqual(len(requests), 2)
        for request, timeout in requests:
            self.assertEqual(timeout, 30)
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.data)
            self.assertEqual(request.get_header("Authorization"), "Bearer " + self.generic)
            self.assertNotIn(self.app, repr(request.header_items()))

    def test_gh_token_is_only_a_read_fallback(self):
        seen = []

        def urlopen(request, timeout):
            seen.append(request)
            return Response()

        with mock.patch.dict(
            os.environ, {"GH_TOKEN": self.generic, APP_TOKEN: self.app}, clear=True
        ), mock.patch("urllib.request.urlopen", side_effect=urlopen):
            reconciler.api("/branches/main")
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer " + self.generic)
        self.assertNotIn(self.app, repr(seen[0].header_items()))

    def test_generic_read_boundary_has_no_write_method_or_payload_surface(self):
        with self.environment():
            with self.assertRaises(TypeError):
                reconciler.api("/statuses/" + self.sha, "POST", {})
            with self.assertRaises(TypeError):
                reconciler.api_with_server_date("/statuses/" + self.sha, method="POST")
        source = (ROOT / "scripts" / "reconcile_open_prs.py").read_text(encoding="utf-8")
        self.assertNotIn('api("/statuses/"+sha,"POST"', source)
        self.assertNotIn("api('/statuses/'+sha,'POST'", source)

    def test_status_api_rejects_raw_and_wrapped_endpoint_bypasses_before_network(self):
        invalid = (
            ("/statuses/" + self.sha.upper(), {"context": next(iter(NORMAL_CONTEXTS))}),
            ("/statuses/" + self.sha + "/suffix", {"context": next(iter(NORMAL_CONTEXTS))}),
            ("/commits/" + self.sha, {"context": next(iter(NORMAL_CONTEXTS))}),
            ("/statuses/" + self.sha, {"context": "supernova/diagnostic-only"}),
            ("/statuses/" + self.sha, {"not_context": next(iter(NORMAL_CONTEXTS))}),
            ("/statuses/" + self.sha, []),
        )
        for path, body in invalid:
            with self.subTest(path=path, body=body), self.environment(), \
                 mock.patch("urllib.request.urlopen") as urlopen:
                with self.assertRaises((RuntimeError, TypeError, ValueError)):
                    reconciler.status_api(path, body)
                urlopen.assert_not_called()

    def test_all_three_protected_posts_use_only_app_token(self):
        requests = []

        def urlopen(request, timeout):
            requests.append(request)
            return Response()

        with self.environment(), mock.patch(
            "urllib.request.urlopen", side_effect=urlopen
        ):
            for context in sorted(NORMAL_CONTEXTS):
                reconciler.post_status(self.sha, context, "success", "boundary probe")
        self.assertEqual(len(requests), 3)
        for request in requests:
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.full_url, reconciler.API + "/statuses/" + self.sha)
            self.assertEqual(request.get_header("Authorization"), "Bearer " + self.app)
            self.assertNotIn(self.generic, repr(request.header_items()))
            body = json.loads(request.data.decode("utf-8"))
            self.assertIn(body["context"], NORMAL_CONTEXTS)

    def test_blank_app_token_rejects_protected_post_without_network_or_echo(self):
        with mock.patch.dict(
            os.environ, {"GITHUB_TOKEN": self.generic, APP_TOKEN: " "}, clear=True
        ), mock.patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(RuntimeError) as raised:
                reconciler.post_status(
                    self.sha, "supernova/static-control", "success", "probe"
                )
        urlopen.assert_not_called()
        self.assertNotIn(self.generic, str(raised.exception))

    def test_exact_five_workflows_have_one_isolated_protected_reconciler_job(self):
        for filename, protected_job in WORKFLOW_PROTECTED_JOBS.items():
            with self.subTest(filename=filename):
                text = (WORKFLOWS / filename).read_text(encoding="utf-8")
                self.assertIn("group: supernova-required-context-writers", text)
                self.assertIn("cancel-in-progress: false", text)
                self.assertNotIn("statuses: write", text.split("\njobs:\n", 1)[0])
                jobs = job_blocks(text)
                self.assertEqual(set(jobs) - {protected_job}, WORKFLOW_GENERIC_JOBS[filename])
                job = jobs[protected_job]
                self.assertEqual(
                    effective_job_permissions(text, job),
                    {
                        "actions": "read",
                        "contents": "read",
                        "issues": "read",
                        "pull-requests": "read",
                        "statuses": "read",
                    },
                )
                self.assertEqual(
                    re.findall(r"(?m)^    environment:\s*(\S+)\s*$", job),
                    [APP_ENVIRONMENT],
                )
                self.assertEqual(
                    sum("reconcile_open_prs.py" in run for run in yaml_run_blocks(job)),
                    1,
                )

    def test_mint_step_is_pinned_scoped_and_precedes_the_only_status_step(self):
        expected_inputs = {
            "client-id": EXPRESSION + " vars." + APP_CLIENT_ID_VARIABLE + " }}",
            "private-key": EXPRESSION + " secrets." + APP_PRIVATE_KEY_SECRET + " }}",
            "permission-statuses": "write",
        }
        for filename, protected_job in WORKFLOW_PROTECTED_JOBS.items():
            with self.subTest(filename=filename):
                job = job_blocks((WORKFLOWS / filename).read_text(encoding="utf-8"))[
                    protected_job
                ]
                mint = named_step(job, "Mint repository-scoped protected status token")
                self.assertIn("id: status-token", mint)
                self.assertIn("uses: " + APP_ACTION, mint)
                self.assertEqual(yaml_mapping(mint, "with", 8), expected_inputs)
                self.assertNotIn("owner:", mint)
                self.assertNotIn("repositories:", mint)
                self.assertNotIn("app-id:", mint)
                reconcile = reconciler_step(job)
                self.assertLess(job.index(mint), job.index(reconcile))
                env = yaml_mapping(reconcile, "env", 8)
                self.assertIsNotNone(env)
                self.assertEqual(env["GITHUB_TOKEN"], EXPRESSION + " github.token }}")
                self.assertEqual(env["GITHUB_REPOSITORY"], EXPRESSION + " github.repository }}")
                self.assertEqual(
                    env[APP_TOKEN], EXPRESSION + " steps.status-token.outputs.token }}"
                )
                self.assertNotIn("GH_TOKEN", env)
                self.assertNotIn(APP_CLIENT_ID_VARIABLE, reconcile)
                self.assertNotIn(APP_PRIVATE_KEY_SECRET, reconcile)
                self.assertNotIn("steps.status-token.outputs.token", mint)
                for other in step_blocks(job):
                    if other == mint or other == reconcile:
                        continue
                    self.assertNotIn(APP_TOKEN, other)
                    self.assertNotIn(APP_CLIENT_ID_VARIABLE, other)
                    self.assertNotIn(APP_PRIVATE_KEY_SECRET, other)
                    self.assertNotIn("steps.status-token.outputs.token", other)

    def test_mixed_generic_jobs_cannot_access_app_boundary_or_normal_contexts(self):
        forbidden = NORMAL_CONTEXTS | {
            APP_ENVIRONMENT,
            APP_CLIENT_ID_VARIABLE,
            APP_PRIVATE_KEY_SECRET,
            APP_TOKEN,
            APP_ACTION,
            "steps.status-token.outputs.token",
            "reconcile_open_prs.py",
        }
        for filename, protected_job in WORKFLOW_PROTECTED_JOBS.items():
            with self.subTest(filename=filename):
                jobs = job_blocks((WORKFLOWS / filename).read_text(encoding="utf-8"))
                for name, job in jobs.items():
                    if name == protected_job:
                        continue
                    self.assertNotIn("environment:", job)
                    for needle in forbidden:
                        self.assertNotIn(needle, job)
                    if "statuses: write" in job:
                        self.assertNotIn("permission-statuses: write", job)


if __name__ == "__main__":
    unittest.main()
