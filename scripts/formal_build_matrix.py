#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
from typing import Any

from jsonschema import Draft202012Validator

COMPONENT_ORDER = ("mathlib", "pantograph", "comparator", "lean4export")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def run_command(cmd: list[str], cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    # Deliberately no timeout: Foundry's mathematical/runtime default is no
    # wall-clock stop, and this engineering build harness must not reintroduce
    # a hidden deadline. External orchestration may terminate infrastructure,
    # but such termination is not a build PASS or mathematical verdict.
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)


def parse_sources(rows: list[str]) -> dict[str, pathlib.Path]:
    out: dict[str, pathlib.Path] = {}
    for row in rows:
        if "=" not in row:
            raise ValueError(f"invalid --source {row!r}; expected component=/absolute/path")
        name, raw_path = row.split("=", 1)
        if name not in COMPONENT_ORDER:
            raise ValueError(f"unsupported source component: {name}")
        if name in out:
            raise ValueError(f"duplicate source component: {name}")
        path = pathlib.Path(raw_path).expanduser().resolve()
        out[name] = path
    return out


def component_plan(manifest: dict[str, Any], component_id: str, source_path: pathlib.Path | None) -> dict[str, Any]:
    source = manifest["components"][component_id]
    return {
        "repository": source["repository"],
        "source_commit": source["source_commit"],
        "source_path": str(source_path) if source_path else None,
        "source_identity_status": "NOT_CHECKED",
        "toolchain_status": "NOT_CHECKED",
        "build_command": ["lake", "build"],
        "build_status": "NOT_RUN",
        "returncode": None,
        "stdout_sha256": None,
        "stderr_sha256": None,
    }


def base_receipt(manifest: dict[str, Any], mode: str, sources: dict[str, pathlib.Path]) -> dict[str, Any]:
    return {
        "schema_version": "PS-FORMAL-BUILD-MATRIX-RECEIPT-1",
        "authority": "NONE_ENGINEERING_ONLY",
        "mode": mode,
        "status": "PLAN_ONLY" if mode == "PLAN_ONLY" else "BLOCKED",
        "toolchain_manifest_sha256": canonical_sha256(manifest),
        "wall_clock_limit": "NONE",
        "lean_version": None,
        "lake_version": None,
        "components": {
            name: component_plan(manifest, name, sources.get(name)) for name in COMPONENT_ORDER
        },
        "errors": [],
        "supernova_credit": {
            "calibration": 0,
            "fresh": False,
            "scientific": False,
            "authority": "NONE",
        },
    }


def _git_head(path: pathlib.Path) -> str | None:
    cp = run_command(["git", "rev-parse", "HEAD"], cwd=path)
    return cp.stdout.strip() if cp.returncode == 0 else None


def _declared_toolchain(path: pathlib.Path) -> str | None:
    p = path / "lean-toolchain"
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8").strip()


def execute_matrix(manifest: dict[str, Any], sources: dict[str, pathlib.Path], log_dir: pathlib.Path | None = None) -> dict[str, Any]:
    receipt = base_receipt(manifest, "EXECUTE", sources)
    errors: list[str] = receipt["errors"]

    lean = shutil.which("lean")
    lake = shutil.which("lake")
    if lean is None:
        errors.append("missing_executable:lean")
    if lake is None:
        errors.append("missing_executable:lake")

    if lean is not None:
        cp = run_command([lean, "--version"])
        receipt["lean_version"] = (cp.stdout or cp.stderr).strip()
        if cp.returncode != 0 or "4.31.0" not in receipt["lean_version"]:
            errors.append("lean_version_mismatch_or_failure")
    if lake is not None:
        cp = run_command([lake, "--version"])
        receipt["lake_version"] = (cp.stdout or cp.stderr).strip()
        if cp.returncode != 0:
            errors.append("lake_version_failure")

    for name in COMPONENT_ORDER:
        row = receipt["components"][name]
        path = sources.get(name)
        if path is None or not path.is_dir():
            row["source_identity_status"] = "FAIL"
            row["toolchain_status"] = "FAIL"
            errors.append(f"missing_source:{name}")
            continue

        expected_commit = manifest["components"][name]["source_commit"]
        actual_commit = _git_head(path)
        if actual_commit == expected_commit:
            row["source_identity_status"] = "PASS"
        else:
            row["source_identity_status"] = "FAIL"
            errors.append(f"source_commit_mismatch:{name}:{actual_commit}:{expected_commit}")

        expected_toolchain = manifest["lean_toolchain"]
        actual_toolchain = _declared_toolchain(path)
        if actual_toolchain == expected_toolchain:
            row["toolchain_status"] = "PASS"
        else:
            row["toolchain_status"] = "FAIL"
            errors.append(f"source_toolchain_mismatch:{name}:{actual_toolchain}:{expected_toolchain}")

    if errors:
        for row in receipt["components"].values():
            if row["build_status"] == "NOT_RUN":
                row["build_status"] = "BLOCKED"
        receipt["status"] = "BLOCKED"
        return receipt

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    failed = False
    for name in COMPONENT_ORDER:
        row = receipt["components"][name]
        path = sources[name]
        cp = run_command([lake or "lake", "build"], cwd=path)
        row["returncode"] = cp.returncode
        row["stdout_sha256"] = text_sha256(cp.stdout)
        row["stderr_sha256"] = text_sha256(cp.stderr)
        row["build_status"] = "PASS" if cp.returncode == 0 else "FAIL"
        failed = failed or cp.returncode != 0
        if log_dir:
            (log_dir / f"{name}.stdout.txt").write_text(cp.stdout, encoding="utf-8")
            (log_dir / f"{name}.stderr.txt").write_text(cp.stderr, encoding="utf-8")

    receipt["status"] = "FAIL" if failed else "PASS"
    return receipt


def validate_receipt(root: pathlib.Path, receipt: dict[str, Any]) -> list[str]:
    schema = load_json(root / "schemas/formal_build_matrix_receipt.schema.json")
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(x) for x in e.absolute_path) or '$'}:{e.message}"
        for e in sorted(validator.iter_errors(receipt), key=lambda e: list(e.absolute_path))
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan or execute the exact-source formal trust-floor build matrix.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="docs/formal/FORMAL_TOOLCHAIN_CANDIDATE_V1.json")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--source", action="append", default=[], help="component=/absolute/source/path")
    parser.add_argument("--log-dir")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    manifest_path = pathlib.Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    manifest = load_json(manifest_path)
    sources = parse_sources(args.source)

    if args.execute:
        log_dir = pathlib.Path(args.log_dir).resolve() if args.log_dir else None
        receipt = execute_matrix(manifest, sources, log_dir)
    else:
        receipt = base_receipt(manifest, "PLAN_ONLY", sources)

    schema_errors = validate_receipt(root, receipt)
    if schema_errors:
        raise RuntimeError("build receipt schema failure: " + "; ".join(schema_errors))

    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = pathlib.Path(args.out)
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")

    if receipt["status"] in {"PLAN_ONLY", "PASS"}:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
