import json, pathlib, unittest
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[2]

class Rev4InterfaceSchemaTests(unittest.TestCase):
    def test_all_rev4_interface_schemas_are_valid_draft202012(self):
        names=[
            'typed_event.schema.json','lane_liveness_observation.schema.json','cohort_liveness_contract.schema.json',
            'verifier_assurance.schema.json','query_spec.schema.json','horizon_bound.schema.json',
            'computation_selection_trace.schema.json','model_qualification_certificate.schema.json',
            'calibration_lifecycle_record.schema.json','worldline_sn_fork_record.schema.json'
        ]
        for name in names:
            with self.subTest(name=name):
                Draft202012Validator.check_schema(json.loads((ROOT/'schemas'/name).read_text()))

if __name__=='__main__': unittest.main()
