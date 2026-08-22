# FOIL + Mastermind non-authoritative build review rules

Status: engineering/review guidance only. No admission, scientific, runtime, calibration or Revision-5 authority.

For every non-authoritative engineering tranche:

1. FOIL evidence pass: inspect the raw target artifact, current repository state and exact blocker before proposing work. Distinguish observed failure from competing explanations and choose the smallest evidence-producing route.
2. Mastermind mechanism pass: state the proposed mechanism, alternative explanation, negative control, ablation and regression. Do not call a mechanism an improvement from design plausibility alone.
3. Implementation pass: make the smallest bounded change on an allowed engineering branch. Frozen/control/scientific paths stay untouched unless a separately admitted protocol repair explicitly authorizes them.
4. FOIL adversarial pass: attack assumption drift, hidden dependencies, representation aliases, missing-source claims, evaluator leakage and authority confusion.
5. Mastermind acceptance pass: require causal adequacy, identifier independence where relevant, representation transformation evidence, negative control, cross-domain transfer when claimed, existing-mechanism compression, ablation and regression.
6. Evidence receipt: separate IMPLEMENTED_UNQUALIFIED, QUALIFIED and PROSPECTIVELY_VALIDATED. Missing execution capability remains NOT_MEASURED/BLOCKED, never PASS.

FOIL and Mastermind may propose, falsify and review. They may not replace Math Foundry execution authority, MM06 verification, MF06 integration, BIL00 protected repair authority, or Tribunal/Court scientific admission.
