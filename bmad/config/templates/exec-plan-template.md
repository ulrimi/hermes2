# [Short, Action-Oriented Title]

> **Self-Containment Principle**: This plan must be implementable by an agent with no prior context — only the working tree and this plan. Do not point to external docs; embed all required knowledge. State every assumption explicitly. A complete novice reading only this document and the repository must be able to implement the work end-to-end.

## Purpose / Big Picture

Why this work matters from a user's perspective. What becomes possible after this change lands. Write in prose — prefer sentences over bullet lists.

## Progress

<!-- Updated at every stopping point. Use ISO-format timestamps. -->

- [ ] (YYYY-MM-DD HH:MMZ) Plan created and reviewed
- [ ] (YYYY-MM-DD HH:MMZ) [Next milestone]
<!-- Add rows as work progresses. Mark partially completed items:
     - [ ] (YYYY-MM-DD HH:MMZ) Partially completed (done: X; remaining: Y) -->

## Surprises & Discoveries

<!-- Unexpected behaviors, bugs, performance tradeoffs, API quirks discovered during work.
     Future agent sessions will read this to avoid repeating mistakes. -->

_None yet._

## Decision Log

<!-- Every design decision with rationale and date. When a choice isn't obvious,
     record it here so future sessions understand WHY. -->

| Date | Decision | Rationale | Alternatives Considered |
|------|----------|-----------|------------------------|
| | | | |

## Outcomes & Retrospective

<!-- Summary at major milestones or completion. Compare the actual result against
     the original Purpose / Big Picture. What worked? What would you do differently? -->

_To be filled at completion._

## Context and Orientation

Describe the current state as if the reader knows nothing about this area of the codebase. Name every key file and module by its full repository-relative path. Explain what each does and how they relate.

Write in prose. The agent executing this plan has no memory of prior sessions — embed all context here rather than pointing to external documentation.

## Plan of Work

Describe the sequence of edits and additions in prose. Explain the reasoning behind the ordering — why certain changes must come before others, what each phase unlocks.

### Prototyping Milestones

When the work involves significant unknowns, include explicit proof-of-concept milestones to de-risk before committing to the full implementation. Keep prototypes additive and testable — each milestone should produce something that can be validated independently.

## Concrete Steps

Exact commands, working directories, and expected output. Name files with full repository-relative paths. Name functions and modules exactly. Describe where new files go and what they contain.

Each step should be idempotent — running it a second time produces the same result without damage.

## Validation and Acceptance

How to exercise the system and what to observe. Phrase acceptance as observable behavior ("navigating to /health returns HTTP 200") not internal attributes ("added a HealthCheck struct"). Include the exact commands to run and the expected output.

## Idempotence and Recovery

Describe how each step can be safely re-run. For risky operations, include explicit rollback paths. If a step fails partway through, explain how to detect the partial state and resume or revert.

## Interfaces and Dependencies

Prescribed libraries, types, function signatures, and external services this plan depends on. Include version constraints where they matter. If this work produces interfaces that other plans or stories consume, document them here.
