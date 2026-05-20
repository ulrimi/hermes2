# Post-Development Checklist

**Run after completing any development work.**

## Tests

- [ ] All tests pass: `pytest`
- [ ] New tests written for new/changed functionality
- [ ] Edge cases covered (empty inputs, boundary values, error paths)

## Code Quality

- [ ] Linting passes: `ruff check .`
- [ ] Formatting passes: `ruff format --check .`
- [ ] Code style follows project standards (see CLAUDE.md)
- [ ] Functions are focused and appropriately sized
- [ ] Docstrings on new/modified public functions

## Application Health

- [ ] App/service still launches: `python main.py  # or: streamlit run app.py / uvicorn app:app`
- [ ] No broken imports or missing modules

## Story Completion

- [ ] All acceptance criteria verified
- [ ] Story status updated to `✅ Complete`
- [ ] Completion date added
- [ ] Definition of Done checkboxes marked
- [ ] Completion Notes section added with:
  - Files changed
  - Tests added
  - Implementation decisions

## Git

- [ ] Changes committed with story reference
- [ ] Commit message follows convention: `feat(epic): story description`

---

**Work is NOT complete until all checks pass.**
