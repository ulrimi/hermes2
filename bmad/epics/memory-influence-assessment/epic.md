---
id: memory-influence-assessment
status: In Progress
created: 2026-05-19
---

# Epic: Memory Influence Self-Assessment

## Problem

`_emit_influence_assessment()` in `run_agent.py:2062-2137` is a placeholder. Every turn
emits `overall_utility="unassessed"`, `overall_confidence="low"`,
`assessment_method="pattern_matching"`. Per-entry `entries_cited`/`entries_present_but_unused`
lists populate from a 40-char prefix substring match, but no overall verdict is derived.

Result: 110/111 influence reports across 2.5 days of data are unassessed. The dead-weight
analysis the instrumentation was built for cannot run because there is no per-turn utility
signal to correlate against write classifications.

## Goal

Make `memory_influence_self_assessment` reports carry a useful overall_utility value with
honest epistemic tagging (`method`, `confidence`). Once real signal exists, downstream
analysis can correlate write_category → utility, identify dead entries, and validate the
nudge interval.

## Stories

| # | Title | Status | Effort | Risk |
|---|-------|--------|--------|------|
| 001 | Heuristic-derived overall utility from existing per-entry signal | ✅ Complete | S | Low |
| 002 | Inline LLM self-assessment in same turn | ✅ Complete | M | Medium |
| 003 | Auxiliary-agent self-assessment (mirrors `background_review`) | ✅ Complete | L | Medium |

Stories are alternatives along a fidelity/cost ladder. Recommended path: ship 001 first,
collect a few sessions of data, decide whether to escalate to 002 or 003 based on
whether the substring heuristic correlates with anything analytically useful.

## Out of Scope

- Token-count integration (provider API surfaces it; separate effort)
- Cross-session influence verification (requires Phase 2 analysis tooling — see design doc)
- Background-fork reasoning extraction
