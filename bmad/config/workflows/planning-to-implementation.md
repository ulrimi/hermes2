# Planning-to-Implementation Transition

## Overview

This workflow defines how planning outputs (epics, stories) feed into implementation execution.

## Transition Flow

```
Epic Overview → Story Files → Specialist Routing → Context Loading → Implementation
```

### Step 1: Epic Review

Before implementing, review the epic overview:
- Understand the business goal
- Review all stories and their dependencies
- Identify the implementation order

### Step 2: Story Queue Building

Build a prioritized queue of stories:
1. Stories with no dependencies first
2. Foundation stories before dependent ones
3. Data/infrastructure before application logic
4. Application logic before UI/API surface
5. UI/API changes last (they consume all other outputs)

### Step 3: Specialist Routing

Match each story to the appropriate specialist agent in `bmad/config/agents/active/`.

Each specialist file defines:
- Domain expertise
- Code patterns to enforce
- Quality criteria for their area

### Step 4: Context Loading

For each story, the implementing agent:
1. Reads the story file completely
2. Loads the specialist persona from `bmad/config/agents/active/`
3. Reviews referenced source files
4. Checks `ARCHITECTURE.md` for architectural guidance
5. Runs pre-work checklist

### Step 5: Quality Gate Checkpoints

| Checkpoint | When | Gate |
|---|---|---|
| Pre-flight | Before any code changes | env active, app launches, tests pass, lint clean |
| Mid-implementation | After each file change | File is syntactically valid, imports resolve |
| Post-implementation | After all changes | Tests pass, lint clean, app launches |
| Story completion | After validation | All acceptance criteria met, story status updated |
