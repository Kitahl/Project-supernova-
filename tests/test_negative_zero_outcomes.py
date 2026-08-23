import json, pathlib, unittest
from jsonschema import Draft202012Validator

ROOT=pathlib.Path(__file__).resolve().parents[1]

class NegativeZeroOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.schema=json.loads((ROOT/'schemas/branch_report.schema.json').read_text())
        self.item=self.schema['$defs']['negative_zero_record']
        self.validator=Draft202012Validator(self.item)

    def errors(self,obj):
        return list(self.validator.iter_errors(obj))

    def test_schema_is_bound_to_top_level_array(self):
        self.assertEqual(self.schema['properties']['negative_zero_outcomes']['items']['$ref'],'#/$defs/negative_zero_record')

    def test_scientific_not_measured_null_passes(self):
        obj={'meaning':'No fresh measurement.','quantity':'scientific_metric','status':'NOT_MEASURED','value':None}
        self.assertEqual(self.errors(obj),[])

    def test_scientific_not_measured_numeric_zero_fails(self):
        obj={'meaning':'Shadow zero.','quantity':'scientific_metric','status':'NOT_MEASURED','value':0}
        self.assertTrue(self.errors(obj))

    def test_accounting_zero_passes(self):
        obj={'meaning':'Resource counter.','quantity':'benchmark_executions','status':'ACCOUNTING_ZERO','value':0}
        self.assertEqual(self.errors(obj),[])

    def test_accounting_nonzero_fails(self):
        obj={'meaning':'Resource counter.','quantity':'benchmark_executions','status':'ACCOUNTING_ZERO','value':1}
        self.assertTrue(self.errors(obj))

    def test_scientific_metric_cannot_be_accounting_zero(self):
        obj={'meaning':'Scientific result must remain typed missing.','quantity':'scientific_metric','status':'ACCOUNTING_ZERO','value':0}
        self.assertTrue(self.errors(obj))

    def test_arbitrary_untyped_item_fails(self):
        self.assertTrue(self.errors({'status':'NOT_MEASURED','value':None,'shadow_metric':0}))

if __name__=='__main__': unittest.main()
