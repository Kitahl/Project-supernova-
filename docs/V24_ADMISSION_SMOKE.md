# v2.4 Admission Smoke Probe

This documentation-only change exists solely to trigger the frozen v2.4 pull-request admission workflow after that workflow became part of `main`.

Expected result: static-control, report-admission, and transition-admission checks all execute. Because this PR does not mutate `state/CURRENT.json`, it is not a state transition and creates no calibration/scientific credit.
