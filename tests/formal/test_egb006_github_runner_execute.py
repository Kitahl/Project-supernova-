from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import tarfile
import tempfile
import unittest
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROBE_BRANCH = "rev4/egb006-github-runner-execute-20260822"
ELAN_VERSION = "v4.2.3"
ELAN_URL = (
    "https://github.com/leanprover/elan/releases/download/"
    f"{ELAN_VERSION}/elan-x86_64-unknown-linux-gnu.tar.gz"
)


def run(cmd: list[str], *, cwd: pathlib.Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("EGB006_CMD", json.dumps(cmd))
    cp = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        print("EGB006_CMD_RETURN", cp.returncode)
        if cp.stdout:
            print("EGB006_CMD_STDOUT_TAIL")
            print("\n".join(cp.stdout.splitlines()[-80:]))
        if cp.stderr:
            print("EGB006_CMD_STDERR_TAIL")
            print("\n".join(cp.stderr.splitlines()[-80:]))
    return cp


def fetch_exact_source(repository: str, commit: str, dest: pathlib.Path, env: dict[str, str]) -> str:
    dest.mkdir(parents=True, exist_ok=False)
    for cmd in (
        ["git", "init", "-q", str(dest)],
        ["git", "-C", str(dest), "remote", "add", "origin", f"https://github.com/{repository}.git"],
        ["git", "-C", str(dest), "fetch", "--no-tags", "--depth", "1", "origin", commit],
        ["git", "-C", str(dest), "checkout", "-q", "--detach", "FETCH_HEAD"],
    ):
        cp = run(cmd, env=env)
        if cp.returncode != 0:
            raise AssertionError(f"source materialization failed for {repository}@{commit}: {cmd}")
    cp = run(["git", "-C", str(dest), "rev-parse", "HEAD"], env=env)
    if cp.returncode != 0:
        raise AssertionError(f"cannot resolve materialized HEAD for {repository}")
    actual = cp.stdout.strip()
    if actual != commit:
        raise AssertionError(f"source identity mismatch {repository}: {actual} != {commit}")
    return actual


class EGB006GitHubRunnerExecute(unittest.TestCase):
    def test_exact_pinned_combined_build_matrix(self) -> None:
        # This is an execution probe, not a permanent regression.  It runs only
        # on the dedicated rev4 PR head and skips everywhere else.
        if os.environ.get("GITHUB_ACTIONS") != "true":
            self.skipTest("EGB-006 execution probe requires GitHub-hosted Actions")
        if os.environ.get("GITHUB_HEAD_REF") != PROBE_BRANCH:
            self.skipTest("EGB-006 execution probe is confined to its dedicated rev4 branch")

        manifest = json.loads((ROOT / "docs/formal/FORMAL_TOOLCHAIN_CANDIDATE_V1.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["lean_toolchain"], "leanprover/lean4:v4.31.0")

        work = pathlib.Path(tempfile.mkdtemp(prefix="egb006-github-runner-"))
        env = dict(os.environ)
        env["ELAN_HOME"] = str(work / "elan-home")
        env["ELAN_NO_OVERRIDE_NOTICE"] = "1"

        # Pin the Elan release URL used only to materialize the exact Lean
        # toolchain.  EGB-006 evidence authority remains the observed Lean
        # version plus exact source commits and the existing build matrix.
        archive = work / "elan.tar.gz"
        req = urllib.request.Request(ELAN_URL, headers={"User-Agent": "Project-Supernova-EGB006/1"})
        with urllib.request.urlopen(req, timeout=120) as src, archive.open("wb") as dst:
            while True:
                block = src.read(1024 * 1024)
                if not block:
                    break
                dst.write(block)
        elan_archive_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()

        with tarfile.open(archive, "r:gz") as tf:
            member = next((m for m in tf.getmembers() if pathlib.PurePosixPath(m.name).name == "elan-init" and m.isfile()), None)
            self.assertIsNotNone(member, "pinned Elan release archive lacks elan-init")
            member.name = "elan-init"
            tf.extract(member, path=work, filter="data")
        elan_init = work / "elan-init"
        elan_init.chmod(0o755)

        cp = run(
            [str(elan_init), "-y", "--default-toolchain", manifest["lean_toolchain"]],
            env=env,
        )
        self.assertEqual(cp.returncode, 0, "Elan failed to install exact Lean 4.31.0 toolchain")
        env["PATH"] = str(work / "elan-home" / "bin") + os.pathsep + env.get("PATH", "")

        lean = run(["lean", "--version"], env=env)
        lake = run(["lake", "--version"], env=env)
        self.assertEqual(lean.returncode, 0)
        self.assertIn("version 4.31.0", lean.stdout + lean.stderr)
        self.assertEqual(lake.returncode, 0)

        sources: dict[str, pathlib.Path] = {}
        source_heads: dict[str, str] = {}
        for component in ("mathlib", "pantograph", "comparator", "lean4export"):
            row = manifest["components"][component]
            dest = work / "sources" / component
            actual = fetch_exact_source(row["repository"], row["source_commit"], dest, env)
            sources[component] = dest
            source_heads[component] = actual
            declared = (dest / "lean-toolchain").read_text(encoding="utf-8").strip()
            self.assertEqual(declared, manifest["lean_toolchain"], f"{component} toolchain drift")

        git_version = run(["git", "--version"], env=env)
        environment_receipt = {
            "authority": "NONE_ENGINEERING_ONLY",
            "probe_branch": PROBE_BRANCH,
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_sha": os.environ.get("GITHUB_SHA"),
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
            "image_os": os.environ.get("ImageOS"),
            "image_version": os.environ.get("ImageVersion"),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "git": (git_version.stdout or git_version.stderr).strip(),
            "elan_release": ELAN_VERSION,
            "elan_asset_url": ELAN_URL,
            "elan_asset_sha256_observed": elan_archive_sha256,
            "lean": (lean.stdout or lean.stderr).strip(),
            "lake": (lake.stdout or lake.stderr).strip(),
            "source_heads": source_heads,
            "supernova_credit": {"calibration": 0, "fresh": False, "scientific": False, "authority": "NONE"},
        }
        print("EGB006_ENVIRONMENT_RECEIPT_BEGIN")
        print(json.dumps(environment_receipt, sort_keys=True, indent=2))
        print("EGB006_ENVIRONMENT_RECEIPT_END")

        receipt_path = work / "formal-build-receipt.json"
        log_dir = work / "logs"
        cmd = [
            sys.executable,
            str(ROOT / "scripts/formal_build_matrix.py"),
            "--root", str(ROOT),
            "--execute",
        ]
        for component in ("mathlib", "pantograph", "comparator", "lean4export"):
            cmd += ["--source", f"{component}={sources[component]}"]
        cmd += ["--log-dir", str(log_dir), "--out", str(receipt_path)]
        matrix = run(cmd, cwd=ROOT, env=env)

        self.assertTrue(receipt_path.is_file(), "formal build matrix did not emit a receipt")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        print("EGB006_BUILD_RECEIPT_BEGIN")
        print(json.dumps(receipt, sort_keys=True, indent=2))
        print("EGB006_BUILD_RECEIPT_END")

        if matrix.returncode != 0 or receipt.get("status") != "PASS":
            for component in ("mathlib", "pantograph", "comparator", "lean4export"):
                for stream in ("stdout", "stderr"):
                    path = log_dir / f"{component}.{stream}.txt"
                    if path.is_file():
                        print(f"EGB006_{component.upper()}_{stream.upper()}_TAIL_BEGIN")
                        print("\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-120:]))
                        print(f"EGB006_{component.upper()}_{stream.upper()}_TAIL_END")
        self.assertEqual(matrix.returncode, 0, "existing formal build matrix returned a non-PASS exit")
        self.assertEqual(receipt.get("status"), "PASS", "EGB-006 combined build matrix did not pass")


if __name__ == "__main__":
    unittest.main()
