from __future__ import annotations

import importlib.util
import inspect
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "formal_build_matrix.py"
SPEC = importlib.util.spec_from_file_location("formal_build_matrix", SCRIPT)
matrix = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(matrix)


def manifest():
    return json.loads((ROOT / "docs/formal/FORMAL_TOOLCHAIN_CANDIDATE_V1.json").read_text(encoding="utf-8"))


class FormalBuildMatrixTests(unittest.TestCase):
    def test_plan_is_zero_authority_and_no_timeout(self):
        r = matrix.base_receipt(manifest(), "PLAN_ONLY", {})
        self.assertEqual(r["status"], "PLAN_ONLY")
        self.assertEqual(r["authority"], "NONE_ENGINEERING_ONLY")
        self.assertEqual(r["wall_clock_limit"], "NONE")
        self.assertEqual(set(r["components"]), set(matrix.COMPONENT_ORDER))
        self.assertEqual(matrix.validate_receipt(ROOT, r), [])
        self.assertNotIn("timeout", inspect.signature(matrix.run_command).parameters)

    def test_execute_without_sources_is_blocked_not_failed_or_passed(self):
        r = matrix.execute_matrix(manifest(), {})
        self.assertEqual(r["status"], "BLOCKED")
        self.assertNotEqual(r["status"], "PASS")
        self.assertTrue(any(x.startswith("missing_source:") for x in r["errors"]))
        self.assertTrue(all(x["build_status"] == "BLOCKED" for x in r["components"].values()))
        self.assertEqual(r["supernova_credit"]["calibration"], 0)
        self.assertFalse(r["supernova_credit"]["fresh"])

    def _sources(self, root: pathlib.Path):
        out = {}
        for name in matrix.COMPONENT_ORDER:
            p = root / name
            p.mkdir()
            (p / "lean-toolchain").write_text("leanprover/lean4:v4.31.0\n", encoding="utf-8")
            out[name] = p
        return out

    def _run_factory(self, fail_component=None):
        def fake_run(cmd, cwd=None):
            if "--version" in cmd:
                if "lean" in str(cmd[0]):
                    return subprocess.CompletedProcess(cmd, 0, "Lean (version 4.31.0, x86_64)\n", "")
                return subprocess.CompletedProcess(cmd, 0, "Lake version 5.0.0\n", "")
            if len(cmd) >= 2 and cmd[-1] == "build":
                name = pathlib.Path(cwd).name if cwd else ""
                rc = 1 if name == fail_component else 0
                return subprocess.CompletedProcess(cmd, rc, f"build:{name}\n", "failure\n" if rc else "")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return fake_run

    def test_fully_bound_simulated_build_can_pass(self):
        m = manifest()
        with tempfile.TemporaryDirectory() as td:
            sources = self._sources(pathlib.Path(td))
            expected = {name: m["components"][name]["source_commit"] for name in matrix.COMPONENT_ORDER}
            with mock.patch.object(matrix.shutil, "which", side_effect=lambda x: f"/fake/{x}"), \
                 mock.patch.object(matrix, "_git_head", side_effect=lambda p: expected[p.name]), \
                 mock.patch.object(matrix, "run_command", side_effect=self._run_factory()):
                r = matrix.execute_matrix(m, sources)
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(matrix.validate_receipt(ROOT, r), [])
        self.assertTrue(all(x["source_identity_status"] == "PASS" for x in r["components"].values()))
        self.assertTrue(all(x["toolchain_status"] == "PASS" for x in r["components"].values()))
        self.assertTrue(all(x["build_status"] == "PASS" for x in r["components"].values()))

    def test_one_build_failure_fails_matrix(self):
        m = manifest()
        with tempfile.TemporaryDirectory() as td:
            sources = self._sources(pathlib.Path(td))
            expected = {name: m["components"][name]["source_commit"] for name in matrix.COMPONENT_ORDER}
            with mock.patch.object(matrix.shutil, "which", side_effect=lambda x: f"/fake/{x}"), \
                 mock.patch.object(matrix, "_git_head", side_effect=lambda p: expected[p.name]), \
                 mock.patch.object(matrix, "run_command", side_effect=self._run_factory("comparator")):
                r = matrix.execute_matrix(m, sources)
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["components"]["comparator"]["build_status"], "FAIL")
        self.assertNotEqual(r["status"], "PASS")

    def test_source_mismatch_blocks_before_build(self):
        m = manifest()
        with tempfile.TemporaryDirectory() as td:
            sources = self._sources(pathlib.Path(td))
            with mock.patch.object(matrix.shutil, "which", side_effect=lambda x: f"/fake/{x}"), \
                 mock.patch.object(matrix, "_git_head", return_value="0" * 40), \
                 mock.patch.object(matrix, "run_command", side_effect=self._run_factory()):
                r = matrix.execute_matrix(m, sources)
        self.assertEqual(r["status"], "BLOCKED")
        self.assertTrue(any(x.startswith("source_commit_mismatch:") for x in r["errors"]))
        self.assertTrue(all(x["build_status"] == "BLOCKED" for x in r["components"].values()))


if __name__ == "__main__":
    unittest.main()
