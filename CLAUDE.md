# hermes2

hermes2

## Architecture

Monorepo python application. See `ARCHITECTURE.md` for codemap, invariants, and boundaries.

---

## BMAD Workflow (MANDATORY)

> [!IMPORTANT]
> Always use BMAD story-driven development. Never implement directly from high-level requests.

**Before work:** Read `bmad/config/workflows/bmad-flow.md` | Create/consume stories in `bmad/epics/<epic>/stories/`

**After completing any story:**
1. Update story `Status:` → `✅ Complete`, add `**Completed**: YYYY-MM-DD`
2. Mark Definition of Done checkboxes `[x]`, add Completion Notes
3. Update epic overview status table

> Work is NOT complete until story status is synchronized with code state.

---

## Code Quality & QA Standards

### Proactive Collaboration
If you notice the user's request is based on a misconception, or spot a bug adjacent to what
they asked about, say so. You're a collaborator, not just an executor — users benefit from
your judgment, not just your compliance.

### Comment Discipline
Default to writing no comments. Only add one when the WHY is non-obvious: a hidden constraint,
a subtle invariant, a workaround for a specific bug, behavior that would surprise a reader.
If removing the comment wouldn't confuse a future reader, don't write it.
See Golden Principles rule #14 for the full rationale.

Do NOT explain WHAT the code does — well-named identifiers already do that. Do NOT reference the
current task, fix, or callers — those belong in the PR description and rot as the codebase evolves.

Do NOT remove existing comments unless you're removing the code they describe or you know they're wrong.

### Epistemic Honesty
Report outcomes faithfully: if tests fail, say so with the relevant output; if you did not run
a verification step, say that rather than implying it succeeded. Do NOT claim "all tests pass"
when output shows failures, do NOT suppress or simplify failing checks to manufacture a green
result, and do NOT characterize incomplete or broken work as done. Equally, when a check did pass
or a task is complete, state it plainly — do not hedge confirmed results with unnecessary
disclaimers. The goal is an accurate report, not a defensive one.

### Verification Before Completion
Before reporting a task complete, ALWAYS verify it actually works: run the test, execute the script,
check the output. If you can't verify (no test exists, can't run the code), say so explicitly
rather than claiming success.

### Output Efficiency
Keep text between tool calls to 25 words or fewer. Keep final responses to 100 words unless
the task requires more detail. Lead with the action, not the reasoning.

### Communication Style
Write for a person, not logging to a console. Before your first tool call, briefly state what
you're about to do. While working, give short updates at key moments: when you find something
load-bearing, when changing direction, when you've made progress without an update. Write in
flowing prose. Avoid fragments and excessive em dashes. Match responses to the task: a simple
question gets a direct prose answer, not headers and numbered sections.

---

## Quick Commands

| Command | Purpose |
|---------|---------|
| `/bmad <topic>` | Full 5-phase orchestration with parallel agents |
| `/epic <name>` | Create new epic with context gathering |
| `/refine <epic>` | Gap analysis on existing epic |
| `/story <path>` | Create or implement a story |
| `/feature <name>` | Create isolated worktree for parallel work |
| `/implement <path>` | Full implementation of epic or stories |
| `/think <question>` | Sequential reasoning without BMAD structure |
| `/explore <topic>` | Max-compute codebase exploration |
| `/review [depth]` | Code review with auto-detected depth |
| `/configure` | Auto-detect project settings from codebase |
| `/simplify [path]` | Analyze and reduce code complexity |
| `/maintain` | Repository-wide quality and consistency checks |
| `/score [domain]` | Per-domain quality scoring and tracking |
| `/plan <name>` | Create execution plans for complex work |

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Language | python |
| Backend  | Python |

---

## Development Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run app
python main.py  # or: streamlit run app.py / uvicorn app:app

# Lint (run before every commit)
ruff check . && ruff format --check .

# Tests
pytest              # full suite
```

---

## Code Style & Testing

<!-- TODO: Run /configure to auto-detect, or define code style rules manually. -->

**Lint:** `ruff check . && ruff format --check .`
**Test:** `pytest` — mock external services, never hit real APIs.

See `bmad/config/golden-principles.md` for project taste rules and style invariants.

---

## Template Resolution

When reading files from `bmad/config/` that don't exist locally (workflows, tasks, templates, checklists):
1. Read `bmad/config/source.yaml` for `framework.template_dir`
2. Read the file from `{template_dir}/{path_relative_to_bmad/config/}`
3. Substitute only `<!-- TODO: Fill in VAR. Run /configure to auto-detect. -->` placeholders whose keys exist in `bmad/config/source.yaml` `project_values` section (e.g., `hermes2`). Leave any `<!-- TODO: Fill in VAR. Run /configure to auto-detect. -->` tokens not present in `project_values` unchanged in the output.
4. If `source.yaml` doesn't exist, files were copied locally (portable mode) — use local paths only

---

## Key References

| Doc | Path | Notes |
|-----|------|-------|
| Architecture | `ARCHITECTURE.md` | Codemap, invariants, boundaries |
| Golden Principles | `bmad/config/golden-principles.md` | Style rules and taste invariants |
| Core Beliefs | `docs/design-docs/core-beliefs.md` | Agent-first operating principles (create with `--full` or `--upgrade`) |
| Core Config | `bmad/config/core-config.yaml` | Project settings and specialist list |
| BMAD Workflow | `bmad/config/workflows/bmad-flow.md` | Orchestration phases |
| Specialist Agents | `bmad/config/agents/active/` | Domain-specific agent personas |
| Epics & Stories | `bmad/epics/` | All epics and their stories |
| Design Docs | `docs/design-docs/` | Technical design documents (create with `--full` or `--upgrade`) |
| Exec Plans | `docs/exec-plans/` | Execution plans for complex work (create with `--full` or `--upgrade`) |
| Product Specs | `docs/product-specs/` | Product specifications (create with `--full` or `--upgrade`) |
| References | `docs/references/` | LLM-friendly dependency docs (create with `--full` or `--upgrade`) |
| Web Frontend | `web/` |
| Tests | `tests/` |

---

## Checklist Before Completing Work

- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`ruff check .`)
- [ ] BMAD story updated to `✅ Complete` with completion notes
<!-- TODO: Add project-specific checklist items. Run /configure to auto-detect. -->
