import json, pathlib, unittest
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[2]

class LivenessSchemaTests(unittest.TestCase):
    def test_zero_delta_receipt_is_explicit(self):
        s=json.loads((ROOT/'schemas/lane_liveness_observation.schema.json').read_text())
        o={"lane_id":"MF01","expected_window_start":"t0","expected_window_end":"t1","observation_time":"t1","receipt_status":"ZERO_DELTA_RECEIPT_OBSERVED","task_state":"ACTIVE","observation_source":"GITHUB_RECEIPT_MONITOR","receipt_ref":"reports/c/MF01.json","lateness_seconds":0,"notes":""}
        self.assertEqual(list(Draft202012Validator(s).iter_errors(o)),[])

    def test_silence_must_not_be_encoded_as_zero_delta(self):
        s=json.loads((ROOT/'schemas/lane_liveness_observation.schema.json').read_text())
        o={"lane_id":"MF01","expected_window_start":"t0","expected_window_end":"t1","observation_time":"t1","receipt_status":"NO_RECEIPT","task_state":"TASK_STATE_UNKNOWN","observation_source":"GITHUB_RECEIPT_MONITOR","receipt_ref":None,"lateness_seconds":1,"notes":"cause unknown"}
        self.assertEqual(list(Draft202012Validator(s).iter_errors(o)),[])
        self.assertNotEqual(o['receipt_status'],'ZERO_DELTA_RECEIPT_OBSERVED')

if __name__=='__main__': unittest.main()
