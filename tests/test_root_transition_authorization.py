import copy
import importlib.util
import inspect
import json
import pathlib
import unittest
from datetime import datetime, timezone
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "scripts/root_transition_authorization.py"
RECONCILER_PATH = ROOT / "scripts/reconcile_open_prs.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


AUTH = load("root_transition_authorization_test", AUTH_PATH)
RECON = load("root_transition_reconciler_test", RECONCILER_PATH)


class RootTransitionAuthorizationTests(unittest.TestCase):
    repository = "Kitahl/Project-supernova-"
    repo_id = AUTH.REPOSITORY_ID
    owner_id = AUTH.OWNER_USER_ID
    owner_login = "Kitahl"
    pr = 235
    base = "a" * 40
    head = "b" * 40
    tree = "c" * 40
    manifest = "d" * 64
    nonce = "e" * 64
    created = "2026-08-23T20:00:00Z"
    expires = "2026-08-23T20:20:00Z"
    server_date = "Sun, 23 Aug 2026 20:10:00 GMT"

    def command(self, **overrides):
        values = {
            "kernel": AUTH.KERNEL,
            "repo_id": self.repo_id,
            "owner_id": self.owner_id,
            "pr": self.pr,
            "base": self.base,
            "head": self.head,
            "tree": self.tree,
            "changed_path_blob_manifest_sha256": self.manifest,
            "predecessor_epoch": 10,
            "successor_epoch": 11,
            "nonce": self.nonce,
            "expires": self.expires,
        }
        values.update(overrides)
        return AUTH.RootTransitionCommand(**values)

    def comment(self, comment_id=99, **overrides):
        value = {
            "id": comment_id,
            "url": f"https://api.github.com/repos/{self.repository}/issues/comments/{comment_id}",
            "issue_url": f"https://api.github.com/repos/{self.repository}/issues/{self.pr}",
            "html_url": f"https://github.com/{self.repository}/pull/{self.pr}#issuecomment-{comment_id}",
            "body": AUTH.format_exact_command(self.command()),
            "user": {"id": self.owner_id, "login": self.owner_login, "type": "User"},
            "author_association": "OWNER",
            "performed_via_github_app": None,
            "created_at": self.created,
            "updated_at": self.created,
        }
        value.update(overrides)
        return value

    def expected(self, **overrides):
        value = {
            "server_date": self.server_date,
            "repository": self.repository,
            "repo_id": self.repo_id,
            "owner_id": self.owner_id,
            "owner_login": self.owner_login,
            "owner_type": "User",
            "pr": self.pr,
            "base": self.base,
            "head": self.head,
            "tree": self.tree,
            "changed_path_blob_manifest_sha256": self.manifest,
            "predecessor_epoch": 10,
            "successor_epoch": 11,
        }
        value.update(overrides)
        return value

    def validate(self, comment=None, **overrides):
        return AUTH.validate_exact_owner_authorization(
            self.comment() if comment is None else comment,
            **self.expected(**overrides),
        )

    def test_exact_command_round_trip_and_no_extra_text(self):
        body = AUTH.format_exact_command(self.command())
        self.assertEqual(AUTH.parse_exact_command(body), self.command())
        self.assertNotIn("\n", body)
        bad = [
            " " + body,
            body + " ",
            body + "\n",
            body.replace(" kernel=", "  kernel=", 1),
            body.replace(f"repo_id={self.repo_id}", f"repo_id=0{self.repo_id}"),
            body.replace("base=" + self.base, "base=" + self.base.upper()),
            body.replace("owner_id=", "unknown=1 owner_id=", 1),
            body.replace("pr=235 base=", "base=" + self.base + " pr=235 base=", 1),
        ]
        for candidate in bad:
            with self.subTest(candidate=candidate), self.assertRaises(AUTH.AuthorizationError):
                AUTH.parse_exact_command(candidate)
        with self.assertRaises(AUTH.AuthorizationError):
            AUTH.parse_exact_command(AUTH.format_exact_command(self.command(head=self.base)))
        with self.assertRaises(AUTH.AuthorizationError):
            AUTH.parse_exact_command(AUTH.format_exact_command(self.command(successor_epoch=12)))

    def test_every_command_binding_is_load_bearing(self):
        mutations = {
            "repo_id": self.repo_id + 1,
            "owner_id": self.owner_id + 1,
            "pr": self.pr + 1,
            "base": "1" * 40,
            "head": "2" * 40,
            "tree": "3" * 40,
            "changed_path_blob_manifest_sha256": "4" * 64,
            "predecessor_epoch": 9,
            "successor_epoch": 12,
            "expires": "2026-08-23T20:31:00Z",
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                body = AUTH.format_exact_command(self.command(**{key: value}))
                changed = self.comment(body=body)
                with self.assertRaises(AUTH.AuthorizationError):
                    self.validate(changed)
        authorization = self.validate()
        self.assertEqual(authorization.comment_id, 99)
        self.assertEqual(authorization.html_url, self.comment()["html_url"])

    def test_exact_owner_and_immutable_comment_required(self):
        cases = [
            {"user": {"id": self.owner_id + 1, "login": self.owner_login, "type": "User"}},
            {"user": {"id": self.owner_id, "login": "kitahl", "type": "User"}},
            {"user": {"id": self.owner_id, "login": self.owner_login, "type": "Bot"}},
            {"author_association": "MEMBER"},
            {"performed_via_github_app": {"id": 1}},
            {"updated_at": "2026-08-23T20:00:01Z"},
            {"url": "https://example.invalid/comment"},
            {"issue_url": f"https://api.github.com/repos/{self.repository}/issues/236"},
            {"html_url": f"https://github.com/{self.repository}/pull/236#issuecomment-99"},
            {"id": True},
            {"body": None},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(AUTH.AuthorizationError):
                self.validate(self.comment(**overrides))
        with self.assertRaises(AUTH.AuthorizationError):
            self.validate(owner_type="Organization")

    def test_only_live_github_server_time_window_is_authoritative(self):
        cases = [
            ({"expires": "2026-08-23T20:30:01Z"}, self.server_date),
            ({"expires": self.created}, self.server_date),
            ({}, "Sun, 23 Aug 2026 20:20:00 GMT"),
            ({}, "Sun, 23 Aug 2026 19:59:59 GMT"),
            ({}, None),
            ({}, "not-a-date"),
        ]
        for command_overrides, server_date in cases:
            body = AUTH.format_exact_command(self.command(**command_overrides))
            with self.subTest(command=command_overrides, server_date=server_date), self.assertRaises(AUTH.AuthorizationError):
                self.validate(self.comment(body=body), server_date=server_date)
        self.assertEqual(
            AUTH.github_server_datetime(self.server_date),
            datetime(2026, 8, 23, 20, 10, tzinfo=timezone.utc),
        )

    def test_manifest_is_canonical_ordered_exact_and_duplicate_free(self):
        first = {"z/path.py": "1" * 40, "a/path.py": "2" * 40}
        second = [("a/path.py", "2" * 40), ("z/path.py", "1" * 40)]
        self.assertEqual(
            AUTH.canonical_changed_path_blob_manifest_sha256(first),
            AUTH.canonical_changed_path_blob_manifest_sha256(second),
        )
        payload = json.loads(AUTH.canonical_changed_path_blob_manifest(first))
        self.assertEqual([row["path"] for row in payload["changed_paths"]], ["a/path.py", "z/path.py"])
        bad = [
            [],
            [("a", "1" * 40), ("a", "2" * 40)],
            [("../a", "1" * 40)],
            [("a\\b", "1" * 40)],
            [("a\nb", "1" * 40)],
            [("a", "A" * 40)],
        ]
        for rows in bad:
            with self.subTest(rows=rows), self.assertRaises(AUTH.AuthorizationError):
                AUTH.canonical_changed_path_blob_manifest_sha256(rows)

    def contract_run(self, *, state_drift=False, wrong_predecessor=False, successor_mutation=None, successor_extra=None):
        trusted, head = self.base, self.head
        state = {
            "protocol_version": "2.5",
            "task_network_plan_id": RECON.PLAN,
            "calibration_streak": 0,
            "fresh_allowed_globally": False,
        }
        predecessor = {
            "protocol_version": "2.5",
            "task_network_plan_id": RECON.PLAN,
            "epoch": 10,
            "root_tcb_source": "ACCEPTED_MAIN_ADMISSION_AUTHORITY_PLUS_DEPENDENCY_LOCK_PLUS_STATIC_ROOTS_PLUS_VALIDATOR_ENVIRONMENT_PLUS_EPOCH6_THROUGH_EPOCH11_INDEPENDENT_ONE_SHOT_SEEDS_PLUS_ROOT11_SEED_COMPLETENESS_AMENDMENT",
            "root_change_rule": "NO_AUTOMATED_BOOTSTRAP_SELF_AMENDMENT; FUTURE_ROOT_CHANGE_REQUIRES_A_NEW_INDEPENDENTLY_INSTALLED_SEED",
            "root_epoch11_stageability_repair_marker": "config/root_epoch11_stageability_repair_epoch_v25.json",
        }
        predecessor_blob = "6" * 40
        successor = {
            "protocol_version": "2.5",
            "task_network_plan_id": RECON.PLAN,
            "epoch": 11,
            "previous_epoch_blob": ("7" * 40 if wrong_predecessor else predecessor_blob),
            "root_transition_authorization": AUTH.contract(),
            "status_writer_partition": {
                "open_main_pr_heads": "scripts/reconcile_open_prs.py",
                "non_pr_active_cohort_heads": "scripts/reconcile_v25_admission.py",
                "legacy_seed_programs": "RECEIPT_CONTEXT_ONLY",
            },
            "root_tcb_source": "ACCEPTED_MAIN_ADMISSION_AUTHORITY_PLUS_DEPENDENCY_LOCK_PLUS_STATIC_ROOTS_PLUS_VALIDATOR_ENVIRONMENT_PLUS_EPOCH6_THROUGH_EPOCH11_FROZEN_LINEAGE_SEEDS_PLUS_INSTALLED_OWNER_ROOT_TRANSITION_KERNEL",
            "root_change_rule": "NO_AUTOMATED_BOOTSTRAP_SELF_AMENDMENT; FUTURE_ROOT_CHANGE_REQUIRES_THE_EXACT_INSTALLED_OWNER_ROOT_TRANSITION_KERNEL_AND_SOURCE_BOUND_RECEIPT",
            "root_epoch11_stageability_repair_marker": "config/root_epoch11_stageability_repair_epoch_v25.json",
        }
        if successor_mutation:
            successor.update(successor_mutation)
        if successor_extra:
            successor.update(successor_extra)
        blobs = {
            trusted + ":state/CURRENT.json": "8" * 40,
            head + ":state/CURRENT.json": ("9" * 40 if state_drift else "8" * 40),
            trusted + ":" + RECON.ROOT_TCB_PATH: predecessor_blob,
            head + ":" + RECON.ROOT_TCB_PATH: "a" * 40,
        }
        docs = {
            trusted + ":state/CURRENT.json": state,
            trusted + ":" + RECON.ROOT_TCB_PATH: predecessor,
            head + ":" + RECON.ROOT_TCB_PATH: successor,
        }
        changed = [RECON.ROOT_TCB_PATH, "scripts/reconcile_open_prs.py"]
        path_blobs = {RECON.ROOT_TCB_PATH: "a" * 40, "scripts/reconcile_open_prs.py": "b" * 40}

        def fake(cmd, cwd, env=None):
            if cmd[:2] == ["git", "rev-parse"]:
                if cmd[2] == head + "^{tree}":
                    return 0, self.tree + "\n"
                value = blobs.get(cmd[2])
                return (0, value + "\n") if value else (1, "")
            if cmd[:2] == ["git", "show"]:
                value = docs.get(cmd[2])
                return (0, json.dumps(value)) if value else (1, "")
            if cmd[:2] == ["git", "ls-tree"]:
                path = cmd[-1]
                return 0, f"100644 blob {path_blobs[path]}\t{path}\n"
            raise AssertionError(cmd)

        return changed, fake

    def test_accepted_main_contract_binds_state_epoch_tree_manifest_and_exact_transform(self):
        changed, fake = self.contract_run()
        with mock.patch.object(RECON, "run", side_effect=fake):
            contract, errors = RECON.root_transition_candidate_contract(pathlib.Path("/repo"), self.base, self.head, changed)
        self.assertEqual(errors, [])
        self.assertEqual(contract["tree"], self.tree)
        expected = AUTH.canonical_changed_path_blob_manifest_sha256({
            RECON.ROOT_TCB_PATH: "a" * 40,
            "scripts/reconcile_open_prs.py": "b" * 40,
        })
        self.assertEqual(contract["changed_path_blob_manifest_sha256"], expected)
        for kwargs in (
            {"state_drift": True},
            {"wrong_predecessor": True},
            {"successor_mutation": {"status_writer_partition": {"legacy_seed_programs": "NORMAL_CONTEXTS"}}},
            {"successor_mutation": {"root_epoch11_stageability_repair_marker": "deleted"}},
            {"successor_extra": {"unallowlisted_safety_field": "changed"}},
        ):
            changed, fake = self.contract_run(**kwargs)
            with self.subTest(kwargs=kwargs), mock.patch.object(RECON, "run", side_effect=fake):
                self.assertTrue(RECON.root_transition_candidate_contract(pathlib.Path("/repo"), self.base, self.head, changed)[1])
        changed, fake = self.contract_run()
        with mock.patch.object(RECON, "run", side_effect=fake):
            self.assertTrue(RECON.root_transition_candidate_contract(pathlib.Path("/repo"), self.base, self.head, changed + ["state/OTHER.json"])[1])


    def test_history_derived_synthetic_successor_rejects_all_195_other_top_level_deltas(self):
        predecessor = RECON._git_json_at(
            ROOT,
            RECON.ROOT_TCB_PATH,
            "73ed5115689f9eeac18fcdcaed7068f86707bc2a",
        )
        successor = copy.deepcopy(predecessor)
        successor["epoch"] = predecessor["epoch"] + 1
        successor["previous_epoch_blob"] = "0" * 40
        successor["root_transition_authorization"] = AUTH.contract()
        successor["status_writer_partition"] = {
            "open_main_pr_heads": "scripts/reconcile_open_prs.py",
            "non_pr_active_cohort_heads": "scripts/reconcile_v25_admission.py",
            "legacy_seed_programs": "RECEIPT_CONTEXT_ONLY",
        }
        successor["root_tcb_source"] = (
            "ACCEPTED_MAIN_ADMISSION_AUTHORITY_PLUS_DEPENDENCY_LOCK_PLUS_STATIC_ROOTS_"
            "PLUS_VALIDATOR_ENVIRONMENT_PLUS_EPOCH6_THROUGH_EPOCH11_FROZEN_LINEAGE_"
            "SEEDS_PLUS_INSTALLED_OWNER_ROOT_TRANSITION_KERNEL"
        )
        successor["root_change_rule"] = (
            "NO_AUTOMATED_BOOTSTRAP_SELF_AMENDMENT; FUTURE_ROOT_CHANGE_REQUIRES_THE_"
            "EXACT_INSTALLED_OWNER_ROOT_TRANSITION_KERNEL_AND_SOURCE_BOUND_RECEIPT"
        )
        self.assertIsNone(
            RECON._root_tcb_successor_transform_errors(predecessor, successor)
        )

        def mutate(value):
            if isinstance(value, bool):
                return not value
            if isinstance(value, int):
                return value + 1
            if isinstance(value, str):
                return value + "__MUTATED"
            if isinstance(value, list):
                return value + ["__MUTATED"]
            if isinstance(value, dict):
                return {**value, "__mutated": True}
            return {"__mutated": True}

        allowed = set(
            RECON.ROOT_TCB_MUTABLE_SUCCESSOR_FIELDS
            + RECON.ROOT_TCB_SUCCESSOR_TRANSFORM_FIELDS
        )
        checked = 0
        for key in sorted(set(predecessor) | set(successor)):
            if key in allowed:
                continue
            removed = copy.deepcopy(successor)
            del removed[key]
            with self.subTest(operation="remove", key=key):
                self.assertIsNotNone(
                    RECON._root_tcb_successor_transform_errors(predecessor, removed)
                )
            checked += 1

            changed = copy.deepcopy(successor)
            changed[key] = mutate(changed[key])
            with self.subTest(operation="mutate", key=key):
                self.assertIsNotNone(
                    RECON._root_tcb_successor_transform_errors(predecessor, changed)
                )
            checked += 1

        extra = copy.deepcopy(successor)
        extra["unallowlisted_new_field"] = "changed"
        self.assertIsNotNone(
            RECON._root_tcb_successor_transform_errors(predecessor, extra)
        )
        checked += 1

        for key in RECON.ROOT_TCB_SUCCESSOR_TRANSFORM_FIELDS:
            changed = copy.deepcopy(successor)
            changed[key] = "wrong"
            with self.subTest(operation="transform-after", key=key):
                self.assertIsNotNone(
                    RECON._root_tcb_successor_transform_errors(predecessor, changed)
                )
            checked += 1

            changed_predecessor = copy.deepcopy(predecessor)
            changed_predecessor[key] = "unexpected-before"
            with self.subTest(operation="transform-before", key=key):
                self.assertIsNotNone(
                    RECON._root_tcb_successor_transform_errors(
                        changed_predecessor, successor
                    )
                )
            checked += 1

        self.assertEqual(checked, 195)

    def test_remote_main_validation_order_fails_before_identity_and_comments(self):
        contract = {
            "tree": self.tree,
            "changed_path_blob_manifest_sha256": self.manifest,
            "predecessor_epoch": 10,
            "successor_epoch": 11,
        }
        pr = {"number": self.pr, "base": {"sha": self.base}}
        cases = (
            (
                "date",
                {
                    "ref": "refs/heads/not-main",
                    "object": {"type": "tree", "sha": "not-a-sha"},
                },
                "not-a-date",
                "Date is invalid",
            ),
            (
                "ref",
                {
                    "ref": "refs/heads/not-main",
                    "object": {"type": "tree", "sha": "not-a-sha"},
                },
                self.server_date,
                "not refs/heads/main",
            ),
            (
                "type",
                {
                    "ref": "refs/heads/main",
                    "object": {"type": "tree", "sha": "not-a-sha"},
                },
                self.server_date,
                "not a commit",
            ),
            (
                "sha-shape",
                {
                    "ref": "refs/heads/main",
                    "object": {"type": "commit", "sha": "A" * 40},
                },
                self.server_date,
                "SHA is invalid",
            ),
            (
                "sha-value",
                {
                    "ref": "refs/heads/main",
                    "object": {"type": "commit", "sha": "f" * 40},
                },
                self.server_date,
                "moved away",
            ),
        )
        for label, response, date, message in cases:
            calls = []

            def api(path, method="GET", data=None):
                calls.append(path)
                if path == "/git/ref/heads/main":
                    return response, date
                raise AssertionError(path)

            with self.subTest(label=label), mock.patch.object(
                RECON,
                "root_transition_candidate_contract",
                return_value=(contract, []),
            ), mock.patch.object(RECON, "api_with_server_date", side_effect=api):
                _, errors = RECON.trusted_root_transition_authorization(
                    pathlib.Path("/repo"), pr, self.base, self.head, ["x"]
                )
            self.assertTrue(errors)
            self.assertIn(message, errors[0])
            self.assertEqual(calls, ["/git/ref/heads/main"])

        api = mock.Mock(side_effect=AssertionError("remote main must not be read"))
        wrong_base = {"number": self.pr, "base": {"sha": "f" * 40}}
        with mock.patch.object(
            RECON,
            "root_transition_candidate_contract",
            return_value=(contract, []),
        ), mock.patch.object(RECON, "api_with_server_date", api):
            _, errors = RECON.trusted_root_transition_authorization(
                pathlib.Path("/repo"), wrong_base, self.base, self.head, ["x"]
            )
        self.assertTrue(errors)
        self.assertIn("PR base is not the local trusted main", errors[0])
        api.assert_not_called()

    def test_paginated_inventory_exactly_one_and_api_reread(self):
        contract = {
            "tree": self.tree,
            "changed_path_blob_manifest_sha256": self.manifest,
            "predecessor_epoch": 10,
            "successor_epoch": 11,
        }
        repo = {
            "id": self.repo_id,
            "full_name": self.repository,
            "owner": {"id": self.owner_id, "login": self.owner_login, "type": "User"},
        }
        filler = [{"id": 1000 + index, "body": "ordinary"} for index in range(100)]
        exact = self.comment()
        calls = []

        def api(path, method="GET", data=None):
            calls.append(path)
            if path == "":
                return repo, self.server_date
            if path == "/git/ref/heads/main":
                return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": self.base}}, self.server_date
            if path.endswith("page=1"):
                return filler, self.server_date
            if path.endswith("page=2"):
                return [exact], self.server_date
            if path == "/issues/comments/99":
                return exact, self.server_date
            raise AssertionError(path)

        pr = {"number": self.pr, "base": {"sha": self.base}}
        with mock.patch.object(RECON, "root_transition_candidate_contract", return_value=(contract, [])), mock.patch.object(RECON, "api_with_server_date", side_effect=api):
            authorization, errors = RECON.trusted_root_transition_authorization(pathlib.Path("/repo"), pr, self.base, self.head, ["x"])
        self.assertEqual(errors, [])
        self.assertEqual(authorization.comment_id, 99)
        self.assertTrue(any(path.endswith("page=2") for path in calls))
        self.assertEqual(calls.count("/git/ref/heads/main"), 2)
        self.assertEqual(calls[0], "/git/ref/heads/main")
        first_comment = next(
            index for index, path in enumerate(calls)
            if path.startswith(f"/issues/{self.pr}/comments?")
        )
        self.assertLess(calls.index(""), first_comment)
        self.assertEqual(calls[-2:], ["/issues/comments/99", "/git/ref/heads/main"])

        def moved(path, method="GET", data=None):
            if path == "/git/ref/heads/main":
                return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": "f" * 40}}, self.server_date
            raise AssertionError(path)
        with mock.patch.object(RECON, "root_transition_candidate_contract", return_value=(contract, [])), mock.patch.object(RECON, "api_with_server_date", side_effect=moved):
            _, errors=RECON.trusted_root_transition_authorization(pathlib.Path("/repo"), pr, self.base, self.head, ["x"])
        self.assertTrue(errors)
        self.assertIn("moved away", errors[0])

        def wrong_type(path, method="GET", data=None):
            if path == "/git/ref/heads/main":
                return {"ref": "refs/heads/main", "object": {"type": "tree", "sha": self.base}}, self.server_date
            raise AssertionError(path)
        with mock.patch.object(RECON, "root_transition_candidate_contract", return_value=(contract, [])), mock.patch.object(RECON, "api_with_server_date", side_effect=wrong_type):
            _, errors=RECON.trusted_root_transition_authorization(pathlib.Path("/repo"), pr, self.base, self.head, ["x"])
        self.assertTrue(errors)
        self.assertIn("not a commit", errors[0])

        duplicate = self.comment(comment_id=100)
        def duplicated(path, method="GET", data=None):
            if path == "/git/ref/heads/main":
                return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": self.base}}, self.server_date
            if path == "":
                return repo, self.server_date
            if path.endswith("page=1"):
                return [exact, duplicate], self.server_date
            raise AssertionError(path)
        with mock.patch.object(RECON, "root_transition_candidate_contract", return_value=(contract, [])), mock.patch.object(RECON, "api_with_server_date", side_effect=duplicated):
            self.assertTrue(RECON.trusted_root_transition_authorization(pathlib.Path("/repo"), pr, self.base, self.head, ["x"])[1])

    def test_remote_main_advancing_between_reads_fails_after_final_comment_reread(self):
        contract = {
            "tree": self.tree,
            "changed_path_blob_manifest_sha256": self.manifest,
            "predecessor_epoch": 10,
            "successor_epoch": 11,
        }
        repo = {
            "id": self.repo_id,
            "full_name": self.repository,
            "owner": {"id": self.owner_id, "login": self.owner_login, "type": "User"},
        }
        exact = self.comment()
        calls = []
        main_reads = 0

        def api(path, method="GET", data=None):
            nonlocal main_reads
            calls.append(path)
            if path == "/git/ref/heads/main":
                main_reads += 1
                sha = self.base if main_reads == 1 else "f" * 40
                return {
                    "ref": "refs/heads/main",
                    "object": {"type": "commit", "sha": sha},
                }, self.server_date
            if path == "":
                return repo, self.server_date
            if path.endswith("page=1"):
                return [exact], self.server_date
            if path == "/issues/comments/99":
                return exact, self.server_date
            raise AssertionError(path)

        pr = {"number": self.pr, "base": {"sha": self.base}}
        with mock.patch.object(
            RECON,
            "root_transition_candidate_contract",
            return_value=(contract, []),
        ), mock.patch.object(RECON, "api_with_server_date", side_effect=api):
            authorization, errors = RECON.trusted_root_transition_authorization(
                pathlib.Path("/repo"), pr, self.base, self.head, ["x"]
            )
        self.assertIsNone(authorization)
        self.assertTrue(errors)
        self.assertIn("moved away", errors[0])
        self.assertEqual(main_reads, 2)
        self.assertEqual(calls[-2:], ["/issues/comments/99", "/git/ref/heads/main"])

    def test_reread_edit_or_missing_server_date_fails_closed(self):
        contract = {
            "tree": self.tree,
            "changed_path_blob_manifest_sha256": self.manifest,
            "predecessor_epoch": 10,
            "successor_epoch": 11,
        }
        repo = {
            "id": self.repo_id,
            "full_name": self.repository,
            "owner": {"id": self.owner_id, "login": self.owner_login, "type": "User"},
        }
        exact = self.comment()
        edited = self.comment(updated_at="2026-08-23T20:00:01Z")

        def api(path, method="GET", data=None):
            if path == "/git/ref/heads/main":
                return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": self.base}}, self.server_date
            if path == "":
                return repo, self.server_date
            if path.endswith("page=1"):
                return [exact], self.server_date
            if path == "/issues/comments/99":
                return edited, self.server_date
            raise AssertionError(path)
        with mock.patch.object(RECON, "root_transition_candidate_contract", return_value=(contract, [])), mock.patch.object(RECON, "api_with_server_date", side_effect=api):
            self.assertTrue(RECON.trusted_root_transition_authorization(pathlib.Path("/repo"), {"number": self.pr, "base": {"sha": self.base}}, self.base, self.head, ["x"])[1])

    def test_status_links_authorization_and_every_open_main_pr_is_delegated(self):
        with mock.patch.object(RECON, "status_api") as status_api:
            RECON.post_status(self.head, RECON.CONTEXTS[0], "success", "ok", target_url=self.comment()["html_url"])
        self.assertEqual(status_api.call_args.args[0], "/statuses/" + self.head)
        payload = status_api.call_args.args[1]
        self.assertEqual(payload["target_url"], self.comment()["html_url"])

        consolidate = {
            "number": 7,
            "draft": False,
            "head": {"ref": "ps/consolidate/C", "sha": self.head},
            "base": {"ref": "main", "sha": self.base},
        }
        with mock.patch.dict(RECON.os.environ, {"SUPERNOVA_STATUS_TOKEN": "test-app-status-token"}, clear=False), \
             mock.patch.object(RECON, "open_main_prs", return_value=([consolidate], [])), \
             mock.patch.object(RECON, "trusted_self_check", return_value=[]), \
             mock.patch.object(RECON, "validate_pr") as validate, \
             mock.patch.object(RECON, "status_api") as status_api:
            self.assertEqual(RECON.main(), 0)
            status_api.assert_not_called()
        validate.assert_called_once_with(pathlib.Path.cwd().resolve(), consolidate, trusted_errors=[])

    def test_authority_alternative_preserves_bootstrap_and_never_executes_candidate(self):
        source = RECONCILER_PATH.read_text(encoding="utf-8")
        self.assertIn("trusted_bootstrap_success(sha,base,n)", source)
        self.assertIn("trusted_root_transition_authorization(root,pr,trusted,sha,changed)", source)
        self.assertNotIn("ps/consolidate/", inspect.getsource(RECON.main))
        contract_source = inspect.getsource(RECON.root_transition_candidate_contract)
        self.assertNotIn("worktree", contract_source)
        self.assertNotIn("importlib", contract_source)
        parser_source = AUTH_PATH.read_text(encoding="utf-8")
        for forbidden in ("urllib", "subprocess", "pathlib", "importlib"):
            self.assertNotIn("import " + forbidden, parser_source)


if __name__ == "__main__":
    unittest.main()
