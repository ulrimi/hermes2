# Story-Driven Development Workflow

## Overview

Stories are the primary communication vehicle between planning and implementation phases. A complete story contains everything a dev agent needs for autonomous implementation.

## Story File as Context Vehicle

The story file must contain:

1. **Story Header** — metadata, priority, status
2. **User Story** — "As a / I want / So that"
3. **Business Context** — value and rationale
4. **Acceptance Criteria** — Given-When-Then format, specific and testable
5. **Technical Context** — architecture references, patterns to follow
6. **Implementation Guidance** — specific files, function signatures
7. **Testing Requirements** — what to test, edge cases
8. **Definition of Done** — quality gates

## Story Location and Naming

**Location**: `bmad/epics/{epic-name}/stories/`
**Naming**: `story-{epic-prefix}-{number}-{slug}.md`
**Example**: `story-dc-001-parquet-cache.md` (data-cache epic, story 001)

## Technical Context Sources

For each story, always reference:

- **`ARCHITECTURE.md`** — Target architecture, module map, milestones
- **Current source files** — Explore existing patterns before adding new ones
- **Specialist agent files** — For domain-specific patterns and quality criteria

## Dev/QA Agent Handoff

1. **Planning Agent** creates story with full context
2. **Dev Agent** reads story, loads specialist persona, implements
3. **QA Agent** validates acceptance criteria, reviews tests
4. Story status updated through lifecycle: `Draft` → `Ready` → `In Progress` → `Complete`

## Story Quality Standards

### Context Completeness
- Contains all context needed for autonomous implementation
- References relevant architecture decisions from ARCHITECTURE.md
- Includes business rationale
- Provides specific technical guidance with real file paths

### Specificity
- Acceptance criteria are specific and testable (Given-When-Then)
- Implementation guidance includes function signatures
- Testing requirements cover happy path and edge cases
- Definition of done is measurable

### Anti-Patterns to Avoid

- **Vague**: "Improve data loading" → **Specific**: "Add cache layer that stores fetched data to `data/cache/` and reads from cache on subsequent runs"
- **Missing context**: No mention of which files → **Complete**: "Modify `data_layer.py`, create `cache.py`"
- **Untestable**: "Data should load faster" → **Testable**: "Given cached data exists, when loading same date range, then no API calls are made"
