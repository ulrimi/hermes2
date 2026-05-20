# Pre-Development Checklist

**Run before starting any development work.**

## Environment

- [ ] Environment activated: `source venv/bin/activate`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Runtime version verified

## Application Health

- [ ] App/service launches without errors: `python main.py  # or: streamlit run app.py / uvicorn app:app`
- [ ] Existing tests pass: `pytest`
- [ ] Linting clean: `ruff check .`

## Git Status

- [ ] Working directory clean: `git status`
- [ ] On correct branch for this work

## Story Context

- [ ] Story file loaded and read completely
- [ ] Acceptance criteria understood
- [ ] Technical context reviewed
- [ ] `ARCHITECTURE.md` consulted for relevant guidance
- [ ] Specialist persona loaded (if applicable)

---

**STOP if any check fails. Fix issues before proceeding.**
