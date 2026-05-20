# Analyze Project

**Task Type**: Research Task
**Agent Types**: BMAD Master, Explore agents
**Complexity**: Low-Medium

## Purpose

Analyze current project state and recommend next development steps.

## Task Instructions

### Step 1: Code Inventory

Scan the current project structure using Glob, Grep, and Read:

- Identify all source modules and their purposes
- Note which modules are stubs vs. fully implemented
- Check test coverage by exploring `tests/`

### Step 2: Architecture Assessment

Compare current state against `ARCHITECTURE.md`:
- Which milestones are complete?
- Which modules exist vs. planned?
- What gaps are highest priority?

### Step 3: Gap Analysis

Identify gaps between current state and architecture target:
1. Missing modules/features
2. Incomplete implementations
3. Missing test coverage
4. Technical debt (hardcoded values, missing abstractions)

### Step 4: Recommendations

Output a prioritized list of:
- Recommended epics to create
- Implementation order (matching ARCHITECTURE.md milestones)
- Quick wins vs. larger efforts
- Dependencies between work items
