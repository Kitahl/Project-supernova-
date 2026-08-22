from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROBE_BRANCH = "rev4/egb006-lean-runner-20260822"
TOOLCHAIN = "leanprover/lean4:v4.31.0"
LEAN_SOURCE_COMMIT = "68218e876d2a38b1985b8590fff244a83c321783"
SOURCES = {
    "mathlib": ("leanprover-community/mathlib4", "fabf563a7c95a166b8d7b6efca11c8b4dc9d911f"),
    "pantograph": ("leanprover/Pantograph", "d704b851542b1d2caf1287f65c49f5011f687c05"),
    "comparator": ("leanprover/comparator", "fd2e25de155523dbce1f35d410511f9f63998461"),
    "lean4export": ("leanprover/lean4export", "8554815c2dc6b7abe99ec1f08849c9759ba77947"),
}


def run(cmd: list[str], *, cwd: pathlib.Path | None = None, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    cp = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, text=True, capture_output=True, check=False)
    if cp.stdout:
        print(cp.stdout, end="" if cp.stdout.endswith("\n") else "\n", flush=True)
    if cp.stderr:
        print(cp.stderr, end="" if cp.stderr.endswith("\n") else "\n", flush=True)
    if check and cp.returncode != 0:
        raise AssertionError(f"command failed rc={cp.returncode}: {' '.join(cmd)}")
    return cp


def run_without_timeout(cmd: list[str], *, cwd: pathlib.Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    started = time.monotonic()
    while proc.poll() is None:
        print(f"EGB006_BUILD_HEARTBEAT elapsed_s={int(time.monotonic() - started)}", flush=True)
        time.sleep(60)
    stdout, stderr = proc.communicate()
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n", flush=True)
    if stderr:
        print(stderr, end="" if stderr.endswith("\n") else "\n", flush=True)
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def git_archive_sha256(path: pathlib.Path) -> str:
    proc = subprocess.Popen(["git", "archive", "--format=tar", "HEAD"], cwd=str(path), stdout=subprocess.PIPE)
    assert proc.stdout is not None
    h = hashlib.sha256()
    while True:
        chunk = proc.stdout.read(1024 * 1024)
        if not chunk:
            break
        h.update(chunk)
    rc = proc.wait()
    if rc != 0:
        raise AssertionError(f"git archive failed for {path}: rc={rc}")
    return h.hexdigest()


@unittest.skipUnless(os.environ.get("GITHUB_HEAD_REF") == PROBE_BRANCH, "one-shot EGB-006 live runner probe")
class EGB006LiveRunnerProbe(unittest.TestCase):
    def test_exact_source_build_matrix(self):
        self.assertEqual(os.environ.get("RUNNER_OS"), "Linux")
        self.assertEqual(os.environ.get("ImageOS"), "ubuntu24")

        with tempfile.TemporaryDirectory(prefix="egb006-") as td:
            work = pathlib.Path(td)
            home = pathlib.Path.home()
            env = dict(os.environ)
            elan_bin = home / ".elan" / "bin"
            env["PATH"] = f"{elan_bin}:{env.get('PATH', '')}"

            lean = shutil.which("lean", path=env["PATH"])
            lake = shutil.which("lake", path=env["PATH"])
            if not lean or not lake or "4.31.0" not in run([lean, "--version"], env=env).stdout:
                installer = work / "elan-init.sh"
                run(["curl", "-fsSL", "https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh", "-o", str(installer)], env=env)
                run(["sh", str(installer), "-y", "--no-modify-path", "--default-toolchain", TOOLCHAIN], env=env)
                run([str(elan_bin / "elan"), "toolchain", "install", TOOLCHAIN], env=env)
                run([str(elan_bin / "elan"), "default", TOOLCHAIN], env=env)

            lean = shutil.which("lean", path=env["PATH"])
            lake = shutil.which("lake", path=env["PATH"])
            elan = shutil.which("elan", path=env["PATH"])
            self.assertIsNotNone(lean)
            self.assertIsNotNone(lake)
            self.assertIsNotNone(elan)
            lean_version = run([lean, "--version"], env=env).stdout.strip()
            lake_version = run([lake, "--version"], env=env).stdout.strip()
            elan_version = run([elan, "--version"], env=env).stdout.strip()
            self.assertIn("4.31.0", lean_version)

            source_root = work / "sources"
            source_root.mkdir()
            paths: dict[str, pathlib.Path] = {}
            source_receipt: dict[str, dict[str, str]] = {}
            for name, (repo, commit) in SOURCES.items():
                path = source_root / name
                path.mkdir()
                run(["git", "init", "-q"], cwd=path, env=env)
                run(["git", "remote", "add", "origin", f"https://github.com/{repo}.git"], cwd=path, env=env)
                run(["git", "fetch", "--depth", "1", "origin", commit], cwd=path, env=env)
                run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=path, env=env)
                actual = run(["git", "rev-parse", "HEAD"], cwd=path, env=env).stdout.strip()
                tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=path, env=env).stdout.strip()
                declared_toolchain = (path / "lean-toolchain").read_text(encoding="utf-8").strip()
                self.assertEqual(actual, commit)
                self.assertEqual(declared_toolchain, TOOLCHAIN)
                paths[name] = path
                source_receipt[name] = {
                    "repository": repo,
                    "commit": actual,
                    "tree": tree,
                    "git_archive_sha256": git_archive_sha256(path),
                    "declared_toolchain": declared_toolchain,
                }

            environment_receipt = {
                "authority": "NONE_ENGINEERING_ONLY",
                "runner_os": os.environ.get("RUNNER_OS"),
                "image_os": os.environ.get("ImageOS"),
                "image_version": os.environ.get("ImageVersion"),
                "platform": platform.platform(),
                "python": platform.python_version(),
                "git": run(["git", "--version"], env=env).stdout.strip(),
                "elan": elan_version,
                "lean": lean_version,
                "lake": lake_version,
                "expected_lean_source_commit": LEAN_SOURCE_COMMIT,
                "sources": source_receipt,
            }
            print("EGB006_ENVIRONMENT_RECEIPT_BEGIN", flush=True)
            print(json.dumps(environment_receipt, indent=2, sort_keys=True), flush=True)
            print("EGB006_ENVIRONMENT_RECEIPT_END", flush=True)

            negative_out = work / "negative-control-receipt.json"
            negative_cmd = [
                "python", "scripts/formal_build_matrix.py", "--execute",
                "--source", f"mathlib={paths['pantograph']}",
                "--source", f"pantograph={paths['pantograph']}",
                "--source", f"comparator={paths['comparator']}",
                "--source", f"lean4export={paths['lean4export']}",
                "--out", str(negative_out),
            ]
            neg = run(negative_cmd, cwd=ROOT, env=env, check=False)
            negative_receipt = json.loads(negative_out.read_text(encoding="utf-8"))
            self.assertEqual(neg.returncode, 2)
            self.assertEqual(negative_receipt["status"], "BLOCKED")
            self.assertTrue(any(e.startswith("source_commit_mismatch:mathlib:") for e in negative_receipt["errors"]))
            self.assertTrue(all(row["build_status"] == "BLOCKED" for row in negative_receipt["components"].values()))
            print("EGB006_NEGATIVE_RECEIPT_BEGIN", flush=True)
            print(json.dumps(negative_receipt, indent=2, sort_keys=True), flush=True)
            print("EGB006_NEGATIVE_RECEIPT_END", flush=True)

            receipt_out = work / "formal-build-receipt.json"
            logs = work / "logs"
            cmd = [
                "python", "scripts/formal_build_matrix.py", "--execute",
                "--source", f"mathlib={paths['mathlib']}",
                "--source", f"pantograph={paths['pantograph']}",
                "--source", f"comparator={paths['comparator']}",
                "--source", f"lean4export={paths['lean4export']}",
                "--log-dir", str(logs),
                "--out", str(receipt_out),
            ]
            cp = run_without_timeout(cmd, cwd=ROOT, env=env)
            receipt = json.loads(receipt_out.read_text(encoding="utf-8"))
            print("EGB006_BUILD_RECEIPT_BEGIN", flush=True)
            print(json.dumps(receipt, indent=2, sort_keys=True), flush=True)
            print("EGB006_BUILD_RECEIPT_END", flush=True)
            if receipt["status"] != "PASS":
                for path in sorted(logs.glob("*.txt")):
                    text = path.read_text(encoding="utf-8", errors="replace")
                    print(f"EGB006_LOG_TAIL_BEGIN {path.name}", flush=True)
                    print("\n".join(text.splitlines()[-200:]), flush=True)
                    print(f"EGB006_LOG_TAIL_END {path.name}", flush=True)
            self.assertEqual(cp.returncode, 0, receipt)
            self.assertEqual(receipt["status"], "PASS")
            self.assertTrue(all(row["source_identity_status"] == "PASS" for row in receipt["components"].values()))
            self.assertTrue(all(row["toolchain_status"] == "PASS" for row in receipt["components"].values()))
            self.assertTrue(all(row["build_status"] == "PASS" for row in receipt["components"].values()))


if __name__ == "__main__":
    unittest.main()
