# 0001 — Tech stack

**Status:** Accepted (2026-09-30)

## Decision

- **Monorepo** with `backend/` and `frontend/`.
- **Backend:** Python 3.12, `uv` for deps, FastAPI, Pydantic v2, SQLite (via SQLModel) to start.
  Tooling: `ruff` (lint+format), `mypy`/`pyright` (types), `pytest`.
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + Recharts, `pnpm`.
- **Contracts:** Backend Pydantic models → OpenAPI → generated TypeScript types, so UI and
  API can't silently drift.
- **Local env:** Docker Compose for services (later: Postgres, Langfuse). Pre-commit hooks.
  GitHub Actions CI running lint, typecheck, tests for both halves.

## Why

Python has the best AI/finance ecosystem (provider SDKs, pandas, numpy); Next.js is the
industry-standard frontend and good practice. Generated types are a real-world practice
worth learning.

## Alternatives considered

- All-TypeScript: fine for agents, weaker for portfolio math/backtesting.
- Streamlit: faster but no full-stack practice.
