---
id: memory-influence-assessment-001
epic: memory-influence-assessment
specialist: backend
status: ✅ Complete
scope:
  - run_agent.py
  - tests/agent/test_memory_instrumentation.py
depends_on: []
---

# Story: Derive overall_utility from existing per-entry heuristic counts

**Story ID**: memory-influence-assessment-001
**Epic**: memory-influence-assessment
**Priority**: High
**Estimated Effort**: Small (~30 min)
**Status**: ✅ Complete
**Created**: 2026-05-19
**Completed**: 2026-05-19

## User Story

**As a** memory-instrumentation analyst
**I want** every `memory_influence_self_assessment` report to carry a non-placeholder
`overall_utility` value derived from the per-entry cited/unused counts already computed
**So that** I can correlate write classifications against per-turn utility without
adding LLM cost or latency, and decide whether real assessment is worth the investment.

## Business Context

### Problem Statement

`run_agent.py:2062-2137` computes `entries_cited` and `entries_present_but_unused` lists
via 40-char prefix matching, but hardcodes `overall_utility="unassessed"`. The signal
needed for dead-weight analysis is silently discarded.

### Business Value

Unblocks Phase 2 correlational analysis immediately. Honest about epistemic limits —
keeps `method="pattern_matching"` and `confidence="low"`, just gives analysts a
populated field to filter on.

## Acceptance Criteria

**AC1:** Overall utility derived from per-entry counts
- **Given** a turn has ≥1 entry in `entries_explicitly_cited`
- **When** `_emit_influence_assessment()` runs
- **Then** `overall_memory_utility_this_turn` is `"some_heuristic_evidence"` (not `"unassessed"`)

**AC2:** Unused turn classified as such
- **Given** memory entries exist but none matched the substring heuristic
- **When** `_emit_influence_assessment()` runs
- **Then** `overall_memory_utility_this_turn` is `"no_heuristic_evidence"`

**AC3:** Empty-memory case distinguished
- **Given** memory entries list is empty
- **When** `_emit_influence_assessment()` runs
- **Then** `overall_memory_utility_this_turn` is `"n_a_no_entries"` and per-entry lists are empty

**AC4:** Honest epistemic tagging preserved
- **Given** any of the above
- **When** the report is emitted
- **Then** `assessment_method` remains `"pattern_matching"` and `overall_confidence` remains `"low"`
- **And** `reasoning` explicitly states this is a heuristic-derived overall, not model introspection

**AC5:** Backwards-compatible report schema
- **Given** existing NDJSON consumers
- **When** they parse the new reports
- **Then** the `category_B_self_assessed` shape is unchanged (only the values of three string fields change)

## Technical Context

### Architecture Reference

`docs/plans/hermes-memory-instrumentation-design-v2.md` §5 (memory_influence_self_assessment)
covers schema. The stub being replaced is intentional placeholder noted in the docstring at
`run_agent.py:2065-2069`.

### Existing Patterns to Follow

`run_agent.py:2082-2105` already computes `entries_cited` and `entries_unused` lists in the
same function. Story re-uses these — no new instrumentation surface.

### Dependencies

None. Self-contained change inside `_emit_influence_assessment()`.

## Implementation Guidance

### Files to Modify/Create

- `run_agent.py` — replace hardcoded `overall_utility`, `overall_confidence` (kept low),
  and `reasoning` strings with a derivation block that inspects `entries_cited` and
  `entries_unused` lengths.
- `tests/agent/test_memory_instrumentation.py` — new test file (or extend existing if
  one exists) covering AC1–AC4 by invoking the report builder with synthetic inputs.

### Derivation Logic

```python
# After the existing per-entry loop populates entries_cited / entries_unused:
if not live_entries:
    overall_utility = "n_a_no_entries"
elif entries_cited:
    overall_utility = "some_heuristic_evidence"
else:
    overall_utility = "no_heuristic_evidence"

reasoning = (
    f"Heuristic-derived: {len(entries_cited)} of {len(live_entries)} entries had a "
    "40-char prefix appear in response. Method remains pattern_matching; subliminal "
    "and paraphrased influence undetected."
)
```

`overall_confidence` stays `"low"`. `assessment_method` stays `"pattern_matching"`.

## Testing Requirements

### Unit Tests

- Cited-entries case yields `some_heuristic_evidence`
- No-cited-entries case (entries present, none matched) yields `no_heuristic_evidence`
- Empty memory case yields `n_a_no_entries`
- `assessment_method` and `overall_confidence` unchanged from prior behavior
- `reasoning` string contains the count of cited entries

### Test Patterns

```python
def test_overall_utility_some_heuristic_evidence(agent_with_memory):
    agent_with_memory._memory_store.memory_entries = ["pytest-xdist convention"]
    final_response = "use pytest-xdist convention for parallel runs"
    agent_with_memory._emit_influence_assessment(final_response)
    report = read_last_report(agent_with_memory.session_id)
    assert report["category_B_self_assessed"]["overall_memory_utility_this_turn"] == "some_heuristic_evidence"
    assert report["category_B_self_assessed"]["assessment_method"] == "pattern_matching"
    assert report["category_B_self_assessed"]["overall_confidence"] == "low"
```

## Definition of Done

- [x] Type hints on modified function (already present — verified)
- [x] Lint check passes (`ruff check .`) — `run_agent.py` and new test file clean
- [x] Unit tests cover AC1–AC5 and pass (6/6 in `tests/agent/test_memory_instrumentation.py`)
- [x] One manual end-to-end run produces an NDJSON line with a non-`unassessed` overall_utility
- [x] Story status updated to ✅ Complete with completion notes
- [x] Epic overview status table updated

## Development Notes

### Dev Agent Notes

**Files changed:**
- `run_agent.py:2062-2147` — `_emit_influence_assessment()` derives `overall_utility`
  from `entries_cited`/`live_entries` counts: empty → `n_a_no_entries`, ≥1 cited →
  `some_heuristic_evidence`, otherwise `no_heuristic_evidence`. Docstring updated to
  reflect the derivation and reference follow-on stories 002/003. `assessment_method`
  stays `pattern_matching`, `overall_confidence` stays `low` (honest tagging — substring
  match is still the underlying signal).
- `tests/agent/test_memory_instrumentation.py` (new) — 6 tests covering AC1–AC5 plus
  the `entries_likely_influenced` schema-stability check.

**Note on format check:** `ruff format --check run_agent.py` reports the file would be
reformatted, but this is pre-existing — confirmed by stashing the change and re-running.
Out of scope to format the whole file in this story.

**Pre-existing data:** Old NDJSON files in `~/.hermes2/instrumentation/memory/` retain
their `unassessed` overall_utility. Analyst tooling should filter by report timestamp
to distinguish pre- and post-derivation entries; the schema is unchanged so existing
parsers keep working.

### QA Agent Notes

- All 6 tests pass under pytest-xdist
- End-to-end smoke test against a tmp `HERMES_HOME` confirmed an actual NDJSON line
  carries `overall_memory_utility_this_turn: some_heuristic_evidence` with the new
  reasoning string
