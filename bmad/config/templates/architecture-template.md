# Architecture: {{PROJECT_NAME}}

> This document describes the high-level architecture of {{PROJECT_NAME}}.
> If you want to familiarize yourself with the codebase, this is the place to start.

## Overview

{{PROJECT_DESCRIPTION}}

<!-- TODO: Replace with 2-3 sentences describing the system's purpose, primary
     users, and the core problem it solves. Keep it concrete. -->

## Codemap

<!-- Key modules and their responsibilities. Name each by its actual module/symbol
     name so agents can use symbol search to navigate. Do NOT use file-line links
     — they rot. Use the searchable name instead. -->

### <!-- TODO: Module/package name (e.g., `auth`) -->

<!-- TODO: What this module owns. 2-3 sentences. Key types and entry points. -->

### <!-- TODO: Module/package name (e.g., `api`) -->

<!-- TODO: What this module owns. 2-3 sentences. Key types and entry points. -->

### <!-- TODO: Module/package name (e.g., `models`) -->

<!-- TODO: What this module owns. 2-3 sentences. Key types and entry points. -->

## Architectural Invariants

<!-- Rules that MUST hold across the entire codebase. Phrase as constraints, not
     aspirations. Include absence-based invariants ("X never does Y") — these are
     the most valuable because they prevent the most expensive class of errors:
     structural violations that pass tests but degrade the codebase. -->

1. <!-- TODO: Example — "The `models` layer never imports from `api` or `views`. Data flows up, commands flow down." -->
2. <!-- TODO: Example — "All external input is validated at the boundary (API handlers, CLI parsers). Internal functions trust their callers." -->
3. <!-- TODO: Example — "No module outside `integrations/` makes direct HTTP calls to third-party services." -->
4. <!-- TODO: Add project-specific invariants. -->

## Layer Boundaries

<!-- Define the dependency direction between layers. Which layers can call which?
     What is the data flow? A simple ASCII diagram works well here. -->

```
<!-- TODO: Replace with your layer diagram. Example:

  ┌─────────────┐
  │   API / CLI  │   ← entry points, validation, serialization
  └──────┬───────┘
         │
  ┌──────▼───────┐
  │   Services   │   ← business logic, orchestration
  └──────┬───────┘
         │
  ┌──────▼───────┐
  │    Models    │   ← data structures, persistence
  └──────┬───────┘
         │
  ┌──────▼───────┐
  │ Integrations │   ← external APIs, file I/O
  └──────────────┘

  Arrow direction = allowed dependency direction.
  No layer may import from a layer above it.
-->
```

## Command Design Patterns

### Progressive Disclosure (Phase-Split Pattern)

Commands that exceed ~200 lines should follow the index + phase files pattern:

```
.claude/commands/
├── command.md                    (~50-120 lines — index/dispatcher)
└── command/
    ├── phase-1-name.md           (self-contained phase instructions)
    ├── phase-2-name.md
    └── ...
```

**Why**: Loading 1,000+ lines of instructions into context when only ~100 are needed at any moment wastes tokens. The index file handles argument parsing and phase dispatch. Each phase file is loaded via `Read` tool only when that phase begins.

**When to apply**: Commands over 200 lines. Below 200 lines, keep as a single file.

**Anti-patterns to avoid**:
- Don't inline entire command logic from one command inside another — reference it
- Don't load all phase files upfront — load each phase on demand
- Don't duplicate content across specialist stubs — use template + config

### Template Resolution

When `bmad/config/source.yaml` exists, shared files (workflows, tasks, templates, checklists) are resolved from the framework template directory rather than local copies. Local overrides take precedence.

## Cross-Cutting Concerns

<!-- Patterns that span multiple modules. Each concern should note WHERE it is
     implemented and HOW other modules should interact with it. -->

### Error Handling

<!-- TODO: Describe the error handling strategy. Where are errors caught vs propagated?
     What is the error type hierarchy? -->

### Logging & Observability

<!-- TODO: Describe logging conventions. What gets logged at what level?
     Where do structured logs go? -->

### Configuration

<!-- TODO: Where does configuration live? How is it loaded? Environment variables,
     config files, or both? -->

### Testing Strategy

<!-- TODO: Unit vs integration vs e2e split. Where do test fixtures live?
     What is mocked vs real in each tier? -->
