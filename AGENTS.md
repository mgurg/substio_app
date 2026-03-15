# Agent Instructions

### For AI Agents

When working on this codebase:

1. **Always use `uv`** instead of `pip` or `python -m venv`
2. **Use `uv run`** to execute Python scripts (no activation needed)

## Project Conventions

- Dependencies are managed in `pyproject.toml`
- Lock file is `uv.lock` (committed to repo)
- Virtual environment is `.venv/` (gitignored)

## Coding

- Study related code before making changes to fully **understand the context**
- Try to **remove all unavoidable complexity** from the task before you start coding, **ask challenging questions if needed**
- Do everything to **simplify** solutions and remove all unnecessary complexity from the produced code
- Write clean, modular, readable code
- Prefer composition, dependency injection
- Look for general, powerful, clear abstractions
- Remember the **Zen of Python**