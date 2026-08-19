import copy
import hashlib
import hmac
import json
import pathlib
import unittest

from scripts.validate_branch_bus_v251 import execution_mode_errors

ROOT = pathlib.Path(__file__).resolve().parents[1]
HMAC2 = "PS-HMAC-SHA256-CANONICAL-REPORT-2"


def canonical_payload(report):
    signed = copy.deepcopy(report)
    signed.pop("worker_auth_proof", None)
    return json.dumps(
        signed,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def proof(secret, report):
    return hmac.new(secret, canonical_payload(report), hashlib.sha256).hexdigest()


class V25ReportContractTests(unittest.TestCase):
    def test_auth_metadata_matches_hmac2(self):
        auth = json.loads((ROOT / "config" / "worker_auth.json").read_text(encoding="utf-8"))
        self.assertEqual(auth["scheme"], HMAC2)
        self.assertTrue(auth["raw_secrets_forbidden_in_repo"])
        self.assertEqual(auth["canonicalization"]["remove_field"], "worker_auth_proof")
        self.assertTrue(auth["canonicalization"]["sort_keys"])
        self.assertTrue(auth["canonicalization"]["compact_separators"])
        self.assertFalse(auth["canonicalization"]["ensure_ascii"])

    def test_mutation_of_any_signed_report_area_invalidates_hmac(self):
        secret = bytes.fromhex("11" * 32)
        base = {
            "task_network_plan_id": "p",
            "cohort_id": "c",
            "worker_id": "MF01",
            "mode": "SAFE_REPLAY_ONLY",
            "session_header": {"execution_mode": "SAFE_REPLAY_ONLY", "goal": "g"},
            "evidence_ledger": [{"id": "e1", "status": "ZERO_DELTA"}],
            "issue_ledger": [{"issue_id": "i1", "status": "OPEN"}],
            "cost_ledger": {"benchmark_executions": 0, "deep_research_runs": 0},
            "worker_auth_proof": None,
        }
        expected = proof(secret, base)
        base["worker_auth_proof"] = expected
        self.assertTrue(hmac.compare_digest(proof(secret, base), expected))

        mutations = []
        m = copy.deepcopy(base); m["cohort_id"] = "other"; mutations.append(m)
        m = copy.deepcopy(base); m["mode"] = "FRESH"; mutations.append(m)
        m = copy.deepcopy(base); m["session_header"]["execution_mode"] = "FRESH"; mutations.append(m)
        m = copy.deepcopy(base); m["evidence_ledger"][0]["status"] = "PASS"; mutations.append(m)
        m = copy.deepcopy(base); m["issue_ledger"][0]["status"] = "CLOSED"; mutations.append(m)
        m = copy.deepcopy(base); m["cost_ledger"]["benchmark_executions"] = 1; mutations.append(m)

        for mutated in mutations:
            self.assertFalse(
                hmac.compare_digest(proof(secret, mutated), expected),
                msg=f"stale HMAC accepted mutation: {mutated}",
            )

    def test_execution_mode_positive(self):
        report = {"mode": "SAFE_REPLAY_ONLY", "session_header": {"execution_mode": "SAFE_REPLAY_ONLY"}}
        assignment = {"network_mode": "GITHUB_BRANCH_CALIBRATION"}
        self.assertEqual(execution_mode_errors(report, assignment), [])

    def test_execution_mode_mismatch_rejected(self):
        report = {"mode": "SAFE_REPLAY_ONLY", "session_header": {"execution_mode": "FRESH"}}
        assignment = {"network_mode": "GITHUB_BRANCH_CALIBRATION"}
        errors = execution_mode_errors(report, assignment)
        self.assertIn("session_header.execution_mode != report.mode", errors)
        self.assertIn("calibration session execution_mode != SAFE_REPLAY_ONLY", errors)

    def test_calibration_fresh_mode_rejected_even_when_header_matches(self):
        report = {"mode": "FRESH", "session_header": {"execution_mode": "FRESH"}}
        assignment = {"network_mode": "GITHUB_BRANCH_CALIBRATION"}
        errors = execution_mode_errors(report, assignment)
        self.assertIn("calibration session execution_mode != SAFE_REPLAY_ONLY", errors)
        self.assertIn("calibration report mode != SAFE_REPLAY_ONLY", errors)

    def test_hourly_registry_has_exact_fifteen_staggered_lanes(self):
        reg = json.loads((ROOT / "config" / "task_registry_v25.json").read_text(encoding="utf-8"))
        self.assertEqual(reg["schedule_hours_local"], list(range(24)))
        self.assertEqual(reg["minimum_recurrence_per_task"], "PT1H")
        self.assertEqual(reg["active_task_count"], 15)
        self.assertTrue(reg["no_sixteenth_lane"])
        self.assertEqual(len(reg["tasks"]), 15)
        minutes = {x["role_id"]: x["minute"] for x in reg["tasks"]}
        workers = ["MF01","MF02","MF03","MF04","MF05","MM01","MM02","MM03","MM04","MM05","MM07","EXT01"]
        self.assertEqual([minutes[x] for x in workers], list(range(5, 17)))
        self.assertEqual(minutes["MM06"], 35)
        self.assertEqual(minutes["MF06"], 45)
        self.assertEqual(minutes["BIL00"], 58)


if __name__ == "__main__":
    unittest.main()
