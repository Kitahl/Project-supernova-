#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from typing import Any

from jsonschema import Draft202012Validator

HEX40 = re.compile(r"^[0-9a-f]{40}$")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _schema_errors(schema: dict[str, Any], obj: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    rows: list[str] = []
    for err in sorted(validator.iter_errors(obj), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(x) for x in err.absolute_path) or "$"
        rows.append(f"schema:{path}:{err.message}")
    return rows


def validate_manifest(root: pathlib.Path, manifest_path: pathlib.Path) -> tuple[list[str], list[str], dict[str, Any]]:
    schema = load_json(root / "schemas/formal_toolchain_manifest.schema.json")
    manifest = load_json(manifest_path)
    errors = _schema_errors(schema, manifest)
    warnings: list[str] = []

    if not errors:
        declared = manifest["lean_toolchain"]
        for component_id, row in manifest["components"].items():
            if row["declared_lean_toolchain"] != declared:
                errors.append(
                    f"component_toolchain_mismatch:{component_id}:{row['declared_lean_toolchain']}!={declared}"
                )

            ref = row["ref"]
            source_commit = row.get("source_commit")
            if row["ref_type"] == "commit":
                if not HEX40.fullmatch(ref):
                    errors.append(f"invalid_commit_ref:{component_id}:{ref}")
                if source_commit != ref:
                    errors.append(f"source_commit_mismatch:{component_id}")
            elif source_commit is None:
                warnings.append(f"unresolved_tag_source_commit:{component_id}:{ref}")
            elif not HEX40.fullmatch(source_commit):
                errors.append(f"invalid_source_commit:{component_id}:{source_commit}")

            if row["qualification_status"] == "QUALIFIED":
                if row["build_status"] != "PASS":
                    errors.append(f"qualified_component_without_build_pass:{component_id}")
                if row["license_status"] != "VERIFIED":
                    errors.append(f"qualified_component_without_license_verification:{component_id}")

        if manifest["admission_status"] == "QUALIFIED":
            if manifest["compatibility_status"] != "VERIFIED":
                errors.append("qualified_manifest_requires_verified_compatibility")
            if manifest["environment"]["sandbox_status"] != "QUALIFIED":
                errors.append("qualified_manifest_requires_qualified_sandbox")
            if manifest["missing_requirements"]:
                errors.append("qualified_manifest_requires_empty_missing_requirements")
            for component_id, row in manifest["components"].items():
                if row["qualification_status"] != "QUALIFIED":
                    errors.append(f"qualified_manifest_contains_unqualified_component:{component_id}")
                if row["build_status"] != "PASS":
                    errors.append(f"qualified_manifest_contains_unbuilt_component:{component_id}")
                if row["license_status"] != "VERIFIED":
                    errors.append(f"qualified_manifest_contains_unverified_license:{component_id}")

    receipt = {
        "schema_version": "PS-FORMAL-TOOLCHAIN-PREFLIGHT-1",
        "authority": "NONE_ENGINEERING_ONLY",
        "status": "PASS" if not errors else "FAIL",
        "manifest_sha256": canonical_sha256(manifest),
        "errors": errors,
        "warnings": warnings,
        "supernova_credit": {
            "calibration": 0,
            "fresh": False,
            "scientific": False,
            "authority": "NONE"
        }
    }
    return errors, warnings, receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a non-admissible formal toolchain candidate manifest.")
    parser.add_argument("manifest")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    manifest_path = pathlib.Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (root / manifest_path).resolve()

    errors, _warnings, receipt = validate_manifest(root, manifest_path)
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = pathlib.Path(args.out)
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
