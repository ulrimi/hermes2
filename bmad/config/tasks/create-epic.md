# Create Epic

**Task Type**: Planning Task
**Agent Types**: BMAD Master
**Complexity**: Medium

## Purpose

Create an epic with business context, scope, and story breakdown.

## Prerequisites

- [ ] Feature area identified
- [ ] `ARCHITECTURE.md` reviewed for relevant milestones

## Task Instructions

### Step 1: Define Epic Scope

- Business objective and user value
- Success metrics (measurable outcomes)
- Boundaries (what's in scope, what's not)
- Relevant ARCHITECTURE.md milestone

### Step 2: Story Breakdown

- Identify discrete, implementable stories
- Define dependencies between stories
- Order stories for implementation (infrastructure → logic → UI/API surface)
- Estimate relative effort (Small / Medium / Large)

### Step 3: Create Epic Directory

```bash
mkdir -p bmad/epics/{epic-name}/stories
```

### Step 4: Create Epic Overview

Write `bmad/epics/{epic-name}/epic-overview.md` using `templates/epic-template.md`:

- Epic title and description
- Business value
- Story breakdown table
- Dependencies and sequencing
- Success metrics
- Technical considerations

### Step 5: Create Story Stubs

For each story in the breakdown, create a stub file:
`bmad/epics/{epic-name}/stories/story-{prefix}-{number}-{slug}.md`

Include at minimum: title, user story, and status (`Draft`).

## Naming Conventions

- Epic directories: `kebab-case` (e.g., `data-cache`, `auth-system`)
- Story files: `story-{epic-prefix}-{number}-{slug}.md`
- Epic prefix: 2-3 letter abbreviation (e.g., `dc` for data-cache, `au` for auth)
