import json, pathlib, tempfile, unittest
from jsonschema import Draft202012Validator
from scripts.extract_typed_events import extract

ROOT=pathlib.Path(__file__).resolve().parents[2]

class TypedEventTests(unittest.TestCase):
    def test_schema_accepts_complete_cost_event(self):
        schema=json.loads((ROOT/'schemas/typed_event.schema.json').read_text())
        event={"event_id":"e1","event_type":"COST_EVENT","source_report_ref":"r","problem_id":"p","family_id":"f","pre_outcome_frozen":True,"payload":{"category":"execution","units":1.0,"exchange_rate_ref":"x"}}
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(event)),[])

    def test_extractor_does_not_invent_from_prose(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'r.json'; p.write_text(json.dumps({"executive_status":"mentions METHOD_CALL in prose"}))
            events,rejected=extract([p]); self.assertEqual(events,[]); self.assertEqual(rejected,[])

    def test_missing_preoutcome_freeze_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'r.json'; p.write_text(json.dumps({"typed_events":[{"event_id":"e","event_type":"VERIFICATION_OBLIGATION","source_report_ref":"r","problem_id":"p","family_id":"f","pre_outcome_frozen":False,"payload":{"obligation_id":"o","kind":"k","discharged_by":None}}]}))
            events,rejected=extract([p]); self.assertEqual(events,[]); self.assertEqual(len(rejected),1)

if __name__=='__main__': unittest.main()
