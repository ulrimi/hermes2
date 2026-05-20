# Multi-Agent Coordination Workflow

## Overview

When multiple Claude instances work on the same project, use worktree-based isolation to prevent conflicts.

## Worktree-Based Isolation

Each agent works in a separate git worktree with its own branch:

```bash
# Terminal 1: Work on feature A
/feature feature-a
> /implement feature-a

# Terminal 2: Work on feature B (independent)
/feature feature-b
> /implement feature-b
```

### Branch Naming

- Feature branches: `feature/{epic-name}` (e.g., `feature/data-cache`, `feature/auth`)
- Worktree directory: `.claude/worktrees/{name}/`

## Coordination Mechanisms

### Via Story Status
- Stories track which agent is working on them
- Check `bmad/epics/*/stories/*.md` for status before claiming work
- Update story status when starting and completing

### Via Git
- Each agent works on its own branch
- Merge to main via PR when epic is complete
- Rebase on main before PR to pick up other agents' work

## Merge Conflict Resolution

1. Identify which files conflict
2. If conflict is in same module:
   - Agent with dependent changes rebases
   - Resolve conflicts preserving both changes
3. If conflict is in different modules:
   - Usually auto-resolves
   - Manual merge if necessary

## Dependencies Between Agents

If Agent 2's work depends on Agent 1's output:

1. Agent 1 completes and merges to main
2. Agent 2 rebases on main: `git rebase main`
3. Agent 2 continues implementation

For tightly coupled work, prefer sequential implementation over parallel.
