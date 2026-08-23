import ast
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REST = ROOT / "scripts/reconcile_branch_rest.py"
ADMISSION = ROOT / "scripts/reconcile_v25_admission.py"
STRUCTURAL = ROOT / "scripts/reconcile_branch_statuses.py"
REST_WORKFLOW = ROOT / ".github/workflows/supernova-rest-branch-reconciler.yml"
AUTHORITY = ROOT / "config/admission_authority.json"
BRANCH_CONFIG = ROOT / "branch/CONFIG.json"
EPOCH = ROOT / "config/structural_status_rotation_epoch_v25.json"
STRUCTURAL_CONTEXTS = {"supernova/branch-generation","supernova/branch-worker","supernova/branch-verify","supernova/branch-integrate","supernova/branch-consolidate"}
STATUS_CALL_NAMES = {"status", "post", "post_status", "publish_status"}


def published_structural_contexts(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path));found=set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call): continue
        name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else None
        if name not in STATUS_CALL_NAMES: continue
        for arg in list(node.args)+[kw.value for kw in node.keywords]:
            if isinstance(arg,ast.Constant) and isinstance(arg.value,str) and arg.value in STRUCTURAL_CONTEXTS: found.add(arg.value)
            if isinstance(arg,ast.Dict):
                for key,value in zip(arg.keys,arg.values):
                    if isinstance(key,ast.Constant) and key.value=="context" and isinstance(value,ast.Constant) and value.value in STRUCTURAL_CONTEXTS: found.add(value.value)
    return found


class StructuralStatusSingleWriterTests(unittest.TestCase):
    def test_rest_helper_has_no_status_write_capability(self):
        text=REST.read_text(encoding="utf-8");tree=ast.parse(text)
        self.assertNotIn("/statuses/",text);self.assertNotIn("method=\"POST\"",text);self.assertNotIn("method='POST'",text)
        self.assertNotIn('"supernova/branch-generation"',text);self.assertNotIn("'supernova/branch-generation'",text)
        self.assertNotIn('"supernova/branch-worker"',text);self.assertNotIn("'supernova/branch-worker'",text)
        functions={node.name for node in ast.walk(tree) if isinstance(node,ast.FunctionDef)}
        self.assertFalse({"status","post_status","publish_status"}&functions)

    def test_rest_diagnostics_use_distinct_non_authoritative_names(self):
        text=REST.read_text(encoding="utf-8")
        self.assertIn("supernova/rest-branch-generation-diagnostic",text);self.assertIn("supernova/rest-branch-worker-diagnostic",text)
        self.assertIn('"authoritative": False',text);self.assertIn('AUTHORITATIVE_WRITER = "scripts/reconcile_branch_statuses.py"',text)

    def test_rest_workflow_separates_diagnostics_from_status_writing_admission(self):
        text=REST_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("actions/checkout@",text);self.assertIn("python-version: '3.13.15'",text)
        self.assertIn("requirements-validation.lock",text);self.assertIn("scripts/assert_validator_environment.py",text)
        self.assertIn("python scripts/reconcile_branch_rest.py",text);self.assertIn("python scripts/reconcile_v25_admission.py",text)
        self.assertNotIn("/tmp/reconcile_v25_admission.py",text)
        self.assertIn("GET-only",text);self.assertIn("only status-writing program",text)
        self.assertLess(text.index("python scripts/reconcile_branch_rest.py"),text.index("python scripts/reconcile_v25_admission.py"))

    def test_admission_helper_preserves_fan_in_but_never_publishes_structural_context(self):
        text=ADMISSION.read_text(encoding="utf-8")
        self.assertIn("ih,ie=integration_check(state,vh)",text);self.assertIn("rs=result_state(ve+ie,ri_wait)",text)
        self.assertIn("integration_semantic_errors",text);self.assertIn("supernova/report-admission",text)
        self.assertNotIn("supernova/branch-integrate",text);self.assertEqual(published_structural_contexts(ADMISSION),set())

    def test_all_non_structural_reconcilers_are_rejected_if_they_publish_structural_contexts(self):
        offenders={}
        for path in sorted((ROOT/"scripts").glob("reconcile*.py")):
            if path==STRUCTURAL: continue
            contexts=published_structural_contexts(path)
            if contexts: offenders[path.name]=sorted(contexts)
        self.assertEqual(offenders,{},offenders)

    def test_authoritative_structural_writer_contains_the_structural_contexts(self):
        text=STRUCTURAL.read_text(encoding="utf-8")
        for context in STRUCTURAL_CONTEXTS:self.assertIn(context,text)

    def test_root11_authority_and_branch_config_name_exactly_one_structural_writer(self):
        authority=json.loads(AUTHORITY.read_text(encoding="utf-8"));cfg=json.loads(BRANCH_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(authority["root_tcb_epoch"],11)
        self.assertEqual(authority["structural_status_writer_cardinality"],1)
        self.assertEqual(authority["authoritative_structural_status_writer"],"scripts/reconcile_branch_statuses.py")
        self.assertEqual(authority["non_authoritative_rest_diagnostic"],"scripts/reconcile_branch_rest.py")
        self.assertEqual(cfg["structural_reconciler"]["authoritative"],"scripts/reconcile_branch_statuses.py via supernova-branch-reconciler.yml")
        self.assertIn("non-authoritative",cfg["structural_reconciler"]["diagnostic"])
        self.assertIn("Exactly one authoritative structural writer",cfg["structural_reconciler"]["rule"])

    def test_historical_epoch_makes_old_seed_inert_and_records_zero_credit(self):
        epoch=json.loads(EPOCH.read_text(encoding="utf-8"))
        self.assertEqual(epoch["authoritative_writer_cardinality"],1);self.assertEqual(epoch["authoritative_writer"],"scripts/reconcile_branch_statuses.py")
        self.assertEqual(epoch["former_rest_writer_disposition"],"READ_ONLY_NON_AUTHORITATIVE_DIAGNOSTIC")
        self.assertEqual(epoch["one_shot_seed_disposition"],"PERMANENTLY_INERT_AFTER_THIS_MARKER_IS_ACCEPTED")
        self.assertIn("GEN9_REMAINS_ZERO_CREDIT",epoch["calibration_effect"])


if __name__ == "__main__":unittest.main()
