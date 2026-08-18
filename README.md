# Project Supernova — Scheduled Research Bus

This repository is the canonical persistent orchestration/evidence bus for the scheduled Math Foundry + Mastermind experiment network.

## Boundary

- **Math Foundry + Mastermind are the actual systems.** This scheduled network is external experiment/research/referee infrastructure, not Supernova runtime capability by itself.
- GitHub receipts, votes, summaries, research results, or task consensus cannot create canonical Foundry `ReactionRecord`, `VerifiedProduct`, selectors/controllers, or a runtime upgrade.
- Runtime identity changes only after an independently validated `RUNTIME_UPDATE_RECEIPT` with artifact hashes, validators, lineage/accounting, required diagnostics, and prospective evidence.

## Public-safe repository

This repository is public. Do **not** place hidden benchmark contents, protected item names/IDs, private source payloads, credentials, secrets, or confidential runtime artifacts here.

Protected/fresh evidence is referenced here only by opaque manifest IDs. The manifest payload itself lives in an approved private connector surface. Current private vault: `Kitahl/thoma` (never mirror private payloads into this public repository).

## Flow

`state/CURRENT.json` → immutable `assignments/` → immutable worker `reports/` → immutable `verification/` → immutable `integration/` → immutable `director/` → next assignment.

BIL-00 is the only scheduled task permitted to run the consolidated deep-research sweep, exactly twice daily at 00:58 and 12:58 America/Vancouver. Other workers may only emit structured `research_questions`.

Fresh/protected evidence is disabled until two consecutive replay-only calibration cohorts complete the full GitHub round trip cleanly.
