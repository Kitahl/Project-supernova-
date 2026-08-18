# Deep Research Queue

There is **one** deep-research executor: BIL-00.

Workers, EXT-01, MM-06 and MF-06 may only emit or consolidate structured `research_questions` / `research_needs`. They must not run broad/deep prior-art sweeps themselves.

BIL-00 runs the consolidated research sweep only at 00:58 and 12:58 America/Vancouver. Each slot is idempotent: `research/results/DR-<YYYYMMDD-HH>.json`. If the receipt already exists, the sweep is not repeated.

The sweep consumes only safe verified/integrated questions and prior unresolved research, deduplicates/ranks by end-game impact, searches primary/current sources and independent query families, records negative/corrective evidence and residual gaps, then feeds supported findings into later assignments. Research cannot promote runtime state or expose protected holdouts.
