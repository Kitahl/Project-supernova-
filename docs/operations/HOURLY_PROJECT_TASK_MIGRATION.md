# Project Supernova hourly task migration — protocol 2.5 operational amendment

**Change class:** scheduled-task deployment/cadence only  
**Protocol:** 2.5 frozen  
**Revision:** 4 frozen  
**Scientific evidence change:** none  
**Active generation 6 change:** none  

## Target deployment

All fifteen persistent Project Supernova lanes run once per local hour in `America/Vancouver`, with the existing staggered fan-in:

- workers `MF01..MF05`, `MM01..MM05`, `MM07`, `EXT01`: minutes `:05..:16`;
- `MM06`: `:35`;
- `MF06`: `:45`;
- `BIL00`: `:58`.

This is one recurrence per hour per task. It does not add a sixteenth lane or create sub-hourly recurrence. BIL00 performs Deep Research only at `00:58` and `12:58`; its other hourly runs are limited to director, liveness, issue-consolidation and guarded protocol-2.5 repair work.

## Project placement

Each lane must be created or recreated from inside the ChatGPT project named **Project Supernova** and retain one persistent associated chat. The deployment is not considered project-local until every associated chat is visibly present in that project.

Scheduled tasks must not assume access to project files. Every lane reads canonical material from `Kitahl/Project-supernova-` through the approved GitHub connector, using `main:state/CURRENT.json` only as the pointer to immutable generation material.

## Activation procedure

1. Keep protocol 2.5 and Revision 4 frozen.
2. Pause the old non-project task instance before activating its replacement so the active-task count never exceeds fifteen.
3. From inside **Project Supernova**, create the replacement with the same stable title and prompt from the canonical registry.
4. Set its hourly schedule at the registered minute in `America/Vancouver`.
5. Confirm its associated chat appears inside Project Supernova and record the native task/chat identity in the private deployment ledger.
6. Run a replay-only bootstrap. Require a terminal receipt, including ZERO_DELTA when nothing changed.
7. Only after the replacement passes bootstrap may the old instance be deleted.
8. Do not start countable cohort 1 until all fifteen replacements have passed this activation procedure and the fully hardened control set is frozen in a new generation.

## Fail-closed rules

- Native schedule not observed: `TASK_SCHEDULE_UNVERIFIED`.
- Associated chat not visibly in Project Supernova: `PROJECT_BINDING_UNVERIFIED`.
- Missing receipt by the frozen deadline: `NO_RECEIPT`, never ZERO_DELTA.
- Paused/deleted/unknown task state: lane unavailable; MM06 cannot complete the partition.
- The registry or this document cannot self-attest native ChatGPT task state.
- No task may consume fresh evidence until repository source binding, two clean countable cohorts and the relevant private frozen pre-outcome manifest all pass.

## Capacity note

Fifteen hourly lanes produce up to 360 scheduled executions per day. Task usage limits and automatic inactivity pauses remain operational risks; GitHub receipt-deadline monitoring remains the out-of-band watchdog.
