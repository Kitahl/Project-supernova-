#!/usr/bin/env python3
"""Offline public-safe typed-event extractor.

Reads consumed reports and emits only explicitly present typed events. It never
creates events from prose, mutates source reports, or writes scientific state.
"""
from __future__ import annotations
import argparse, json, pathlib

ALLOWED={"STATE_DELTA","METHOD_CALL","TOOL_RESULT","PRODUCT_CANDIDATE","VERIFIER_RESULT","OBSTRUCTION","COST_EVENT","FORK","VERIFICATION_OBLIGATION"}
BASE_REQUIRED={"event_id","event_type","source_report_ref","problem_id","family_id","pre_outcome_frozen"}
PAYLOAD_REQUIRED={
 "STATE_DELTA":{"before_ref","after_ref","obligations_delta","products_delta","legal_ops_delta"},
 "METHOD_CALL":{"operator_id","contract_version","inputs","fidelity","budget"},
 "TOOL_RESULT":{"tool","outcome_class","cost","exogenous_input_ref"},
 "PRODUCT_CANDIDATE":{"product_id","type","producing_op","certificate_ref"},
 "VERIFIER_RESULT":{"checker_id","status","statement_fidelity_status"},
 "OBSTRUCTION":{"kind","certificate_ref","depth"},
 "COST_EVENT":{"category","units","exchange_rate_ref"},
 "FORK":{"parent_ref","sibling_ids","coupling_semantics","placebo_class"},
 "VERIFICATION_OBLIGATION":{"obligation_id","kind","discharged_by"},
}

def candidate_events(report: dict):
    if isinstance(report.get("typed_events"),list): return report["typed_events"]
    rp=report.get("role_payload")
    if isinstance(rp,dict) and isinstance(rp.get("typed_events"),list): return rp["typed_events"]
    return []

def validate_event(event: dict) -> list[str]:
    errors=[]
    if not isinstance(event,dict): return ["event is not an object"]
    missing=sorted(BASE_REQUIRED-set(event))
    if missing: errors.append("missing base fields: "+",".join(missing))
    et=event.get("event_type")
    if et not in ALLOWED: errors.append("unknown event_type")
    if event.get("pre_outcome_frozen") is not True: errors.append("pre_outcome_frozen must be true for extracted decision/event evidence")
    payload=event.get("payload")
    if et in PAYLOAD_REQUIRED:
        if not isinstance(payload,dict): errors.append("payload missing/not object")
        else:
            missing_payload=sorted(PAYLOAD_REQUIRED[et]-set(payload))
            if missing_payload: errors.append("missing payload fields: "+",".join(missing_payload))
    return errors

def extract(paths):
    out=[]; rejected=[]
    for p in paths:
        obj=json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        for i,event in enumerate(candidate_events(obj)):
            e=dict(event) if isinstance(event,dict) else event
            errs=validate_event(e)
            if errs: rejected.append({"source":str(p),"index":i,"errors":errs})
            else: out.append(e)
    return out,rejected

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("reports",nargs="+"); ap.add_argument("--out",required=True); ap.add_argument("--receipt",required=True); ns=ap.parse_args()
    events,rejected=extract(ns.reports)
    outp=pathlib.Path(ns.out); outp.parent.mkdir(parents=True,exist_ok=True)
    outp.write_text("".join(json.dumps(e,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n" for e in events),encoding="utf-8")
    receipt={"schema_version":"PS-TYPED-EVENT-EXTRACTION-1","execution_class":"OFFLINE_NON_ADMISSIBLE","source_report_count":len(ns.reports),"event_count":len(events),"rejected_event_count":len(rejected),"rejected":rejected,"scientific_status_changed":False}
    pathlib.Path(ns.receipt).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True)); return 0 if not rejected else 2

if __name__=="__main__": raise SystemExit(main())
