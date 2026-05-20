# Implement Story

**Task Type**: Implementation Task
**Agent Types**: Dev Agents with specialist persona
**Complexity**: Varies by story

## Purpose

Implement a story following its specifications and specialist guidance.

## Prerequisites

- [ ] Story file exists and is status `Ready`
- [ ] Pre-work checklist completed
- [ ] Dependencies (blocked-by stories) are complete

## Task Instructions

### Step 1: Context Loading

1. Read story file completely
2. Identify specialist from story domain
3. Load specialist persona from `bmad/config/agents/active/`
4. Review referenced source files
5. Check `ARCHITECTURE.md` for architectural guidance

### Step 2: Implementation Planning

1. List files to create/modify in order
2. Identify insertion points in existing files
3. Plan test file changes
4. Get user approval on plan

### Step 3: Implementation

For each file in sequence:
1. Read current file (if modifying)
2. Write code following specialist patterns
3. Verify syntax is valid
4. Follow project code style (see CLAUDE.md)

### Step 4: Testing

```bash
# Run existing tests (no regression)
pytest

# Write and run new tests
pytest tests/test_[new] -v
```

### Step 5: Validation

```bash
# Linting
ruff check .

# App/service still works
python main.py  # or: streamlit run app.py / uvicorn app:app
```

### Step 6: Acceptance Criteria Verification

Go through each AC in the story:
- [ ] AC1: [description] — VERIFIED by [how]
- [ ] AC2: [description] — VERIFIED by [how]

### Step 7: Story Completion

Update story file:
```markdown
Status: ✅ Complete
**Completed**: [DATE]

## Completion Notes
- [What was implemented]
- [Files changed]
- [Tests added]
```
