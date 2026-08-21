# Scheduled repair loop policy — protocol 2.5

Status: operational guidance for the existing frozen 15-lane network. This does not add a sixteenth lane or change scientific authority.

Default per eligible scheduled run: **2 complete audit/verify/repair/re-audit loops**.

Hard maximum: **3 loops**, and only when work remains lightweight, deterministic, and the previous loop completed cleanly.

A loop must stop immediately on stale SHA, changed canonical state, merge conflict, failed or pending required CI, GitHub/API error, rate-limit condition, task disconnect, timeout, malformed receipt, authority mismatch, unexpected control change, or any other fail-closed condition.

Every loop starts from a fresh reread of canonical GitHub state. Cached authority from the previous loop is not reusable proof.

A loop should use a materially different verification/falsification angle where practical. Missing, unknown, timed-out, disconnected, or failed results never become PASS or ZERO_DELTA.

No loop may bypass repository rules, weaken validators, fabricate receipts, overwrite create-once evidence, or merge around failed checks.

If an authoritative frozen-control change occurs during a countable calibration cohort, the affected cohort receives no clean-cohort credit; the calibration sequence restarts at streak 0 under a new frozen generation before the network resumes countable execution.
