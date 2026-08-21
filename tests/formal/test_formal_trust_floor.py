from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "formal_toolchain_preflight.py"
SPEC = importlib.util.spec_from_file_location("formal_toolchain_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(preflight)


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class FormalToolchainPreflightTests(unittest.TestCase):
    def candidate(self):
        return load("docs/formal/FORMAL_TOOLCHAIN_CANDIDATE_V1.json")

    def errors_for(self, manifest):
        schema = load("schemas/formal_toolchain_manifest.schema.json")
        errors = preflight._schema_errors(schema, manifest)
        if errors:
            return errors
        # Exercise the full validator through a temporary manifest.
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(manifest, f)
            path = pathlib.Path(f.name)
        try:
            errors, _warnings, _receipt = preflight.validate_manifest(ROOT, path)
            return errors
        finally:
            path.unlink(missing_ok=True)

    def test_candidate_is_valid_engineering_only_with_resolved_lean_source(self):
        errors, warnings, receipt = preflight.validate_manifest(
            ROOT, ROOT / "docs/formal/FORMAL_TOOLCHAIN_CANDIDATE_V1.json"
        )
        m = self.candidate()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["authority"], "NONE_ENGINEERING_ONLY")
        self.assertEqual(receipt["supernova_credit"]["calibration"], 0)
        self.assertFalse(receipt["supernova_credit"]["fresh"])
        self.assertEqual(m["components"]["lean4"]["source_commit"], "68218e876d2a38b1985b8590fff244a83c321783")
        self.assertTrue(all(x["license_status"] == "VERIFIED" for x in m["components"].values()))

    def test_declared_toolchain_mismatch_fails(self):
        m = self.candidate()
        m["components"]["pantograph"]["declared_lean_toolchain"] = "leanprover/lean4:v4.18.0"
        self.assertTrue(any("component_toolchain_mismatch:pantograph" in x for x in self.errors_for(m)))

    def test_commit_ref_must_equal_source_commit(self):
        m = self.candidate()
        m["components"]["comparator"]["source_commit"] = "0" * 40
        self.assertTrue(any("source_commit_mismatch:comparator" in x for x in self.errors_for(m)))

    def test_candidate_cannot_claim_supernova_effect(self):
        m = self.candidate()
        m["supernova_effects"]["modifies_state"] = True
        self.assertTrue(any(x.startswith("schema:supernova_effects.modifies_state:") for x in self.errors_for(m)))

    def test_qualified_manifest_fails_closed_until_build_and_component_gates_close(self):
        m = self.candidate()
        m["admission_status"] = "QUALIFIED"
        m["compatibility_status"] = "VERIFIED"
        m["environment"]["sandbox_status"] = "QUALIFIED"
        m["missing_requirements"] = []
        errors = self.errors_for(m)
        self.assertTrue(any("qualified_manifest_contains_unqualified_component" in x for x in errors))
        self.assertTrue(any("qualified_manifest_contains_unbuilt_component" in x for x in errors))

    def test_component_qualification_requires_verified_license(self):
        m = self.candidate()
        m["components"]["pantograph"]["qualification_status"] = "QUALIFIED"
        m["components"]["pantograph"]["build_status"] = "PASS"
        m["components"]["pantograph"]["license_status"] = "UNVERIFIED"
        self.assertTrue(any("qualified_component_without_license_verification:pantograph" in x for x in self.errors_for(m)))


class FormalVerificationReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load("schemas/formal_verification_receipt.schema.json")
        cls.validator = Draft202012Validator(cls.schema)

    def exact_receipt(self):
        return {
            "schema_version": "PS-FORMAL-VERIFICATION-RECEIPT-1",
            "task_id": "fixture/exact",
            "statement_identity": {
                "repository": "owner/repo",
                "commit": "1" * 40,
                "declaration_name": "Fixture.theorem",
                "normalized_type_sha256": "2" * 64
            },
            "toolchain_manifest_sha256": "3" * 64,
            "validity_status": "COMPARATOR_ACCEPTED",
            "statement_fidelity_status": "VERIFIED",
            "axiom_policy_status": "VERIFIED",
            "source_toolchain_status": "VERIFIED",
            "verifier_assurance_status": "SAME_KERNEL_REPLAY",
            "derived_exact_formal_proof": True,
            "authority": "EXACT_FORMAL_PROOF"
        }

    def errors(self, row):
        return list(self.validator.iter_errors(row))

    def test_exact_receipt_requires_all_typed_predicates(self):
        self.assertEqual(self.errors(self.exact_receipt()), [])

    def test_exact_receipt_rejects_unverified_statement_fidelity(self):
        r = self.exact_receipt()
        r["statement_fidelity_status"] = "UNVERIFIED"
        self.assertTrue(self.errors(r))

    def test_nonexact_receipt_cannot_claim_exact_authority(self):
        r = self.exact_receipt()
        r["derived_exact_formal_proof"] = False
        self.assertTrue(self.errors(r))

    def test_same_kernel_replay_is_not_relabelled_different_implementation(self):
        r = self.exact_receipt()
        r["verifier_assurance_status"] = "SAME_KERNEL_REPLAY"
        self.assertEqual(self.errors(r), [])
        self.assertNotEqual(r["verifier_assurance_status"], "DIFFERENT_IMPLEMENTATION_REPLAY")


if __name__ == "__main__":
    unittest.main()
