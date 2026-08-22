from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import unittest
import urllib.request

TOOLCHAIN = "leanprover/lean4:v4.31.0"
LEAN_COMMIT = "68218e876d2a38b1985b8590fff244a83c321783"
SOURCES = {
    "mathlib": ("leanprover-community/mathlib4", "fabf563a7c95a166b8d7b6efca11c8b4dc9d911f"),
    "pantograph": ("leanprover/Pantograph", "d704b851542b1d2caf1287f65c49f5011f687c05"),
    "comparator": ("leanprover/comparator", "fd2e25de155523dbce1f35d410511f9f63998461"),
    "lean4export": ("leanprover/lean4export", "8554815c2dc6b7abe99ec1f08849c9759ba77947"),
}


def run(cmd: list[str], *, cwd: pathlib.Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print("$", " ".join(cmd))
    print(cp.stdout)
    return cp


class EGB006CIExecutorProbe(unittest.TestCase):
    def test_github_runner_can_materialize_exact_lean_toolchain_and_sources(self) -> None:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            self.skipTest("branch-local EGB-006 executor probe runs only in GitHub Actions")

        with tempfile.TemporaryDirectory(prefix="egb006-probe-") as td:
            root = pathlib.Path(td)
            elan_script = root / "elan-init.sh"
            with urllib.request.urlopen(
                "https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh",
                timeout=60,
            ) as response:
                elan_script.write_bytes(response.read())

            install = run(["sh", str(elan_script), "-y", "--default-toolchain", TOOLCHAIN])
            self.assertEqual(install.returncode, 0, install.stdout)

            env = os.environ.copy()
            env["PATH"] = str(pathlib.Path.home() / ".elan" / "bin") + os.pathsep + env.get("PATH", "")

            lean = run(["lean", "--version"], env=env)
            lake = run(["lake", "--version"], env=env)
            self.assertEqual(lean.returncode, 0, lean.stdout)
            self.assertEqual(lake.returncode, 0, lake.stdout)
            self.assertIn("4.31.0", lean.stdout)
            self.assertIn(LEAN_COMMIT[:10], lean.stdout)

            observed: dict[str, object] = {
                "toolchain": TOOLCHAIN,
                "lean_commit": LEAN_COMMIT,
                "lean_version": lean.stdout.strip(),
                "lake_version": lake.stdout.strip(),
                "components": {},
            }

            for name, (repo, commit) in SOURCES.items():
                dst = root / name
                self.assertEqual(run(["git", "init", str(dst)]).returncode, 0)
                self.assertEqual(run(["git", "-C", str(dst), "remote", "add", "origin", f"https://github.com/{repo}.git"]).returncode, 0)
                fetched = run(["git", "-C", str(dst), "fetch", "--depth", "1", "origin", commit])
                self.assertEqual(fetched.returncode, 0, fetched.stdout)
                checked = run(["git", "-C", str(dst), "checkout", "--detach", "FETCH_HEAD"])
                self.assertEqual(checked.returncode, 0, checked.stdout)
                head = run(["git", "-C", str(dst), "rev-parse", "HEAD"])
                self.assertEqual(head.returncode, 0, head.stdout)
                self.assertEqual(head.stdout.strip(), commit)
                declared = (dst / "lean-toolchain").read_text(encoding="utf-8").strip()
                self.assertEqual(declared, TOOLCHAIN)
                observed["components"][name] = {
                    "repository": repo,
                    "expected_commit": commit,
                    "observed_commit": head.stdout.strip(),
                    "lean_toolchain": declared,
                }

            print("EGB006_EXECUTOR_PROBE_RECEIPT=" + json.dumps(observed, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
