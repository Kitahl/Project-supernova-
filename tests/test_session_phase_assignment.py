import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STANDARD = ROOT / "SESSION_STANDARD.md"
STATE = ROOT / "state/CURRENT.json"


class SessionPhaseAssignmentTests(unittest.TestCase):
    def test_standard_requires_exact_frozen_assignment_phase(self):
        text = STANDARD.read_text(encoding="utf-8")
        self.assertIn("PHASE: <exact frozen assignment phase string>", text)
        self.assertIn("MUST equal the exact `phase` value in the frozen active assignment", text)
        self.assertNotIn("PHASE: <T0|E1|G1|C1|REACTION", text)

    def test_current_assignment_phase_is_representable_without_translation(self):
        state = json.loads(STATE.read_text(encoding="utf-8"))
        assignment = json.loads((ROOT / state["active_assignment_path"]).read_text(encoding="utf-8"))
        phase = assignment["phase"]
        self.assertIsInstance(phase, str)
        self.assertTrue(phase)
        header_phase = phase
        self.assertEqual(header_phase, assignment["phase"])


if __name__ == "__main__":
    unittest.main()
