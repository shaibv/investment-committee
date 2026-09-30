# Backend

## Run

```bash
uv sync                                    # install everything (like npm install)
uv run committee analyze                   # real prices from Yahoo Finance
uv run committee analyze --data synthetic  # offline, fake prices
uv run committee analyze --provider openai # real model (needs OPENAI_API_KEY in .env)
uv run committee serve                     # web UI at http://localhost:8000
```

The web UI is plain HTML/CSS/JS in `../web/`, served by the API. It's a stopgap until the
Next.js frontend (ADR 0001) is unblocked; npm is currently blocked on this machine.

## Secrets

Keys live in `backend/.env` (git-ignored). `.env.example` lists what can be set.

Edit `config/profile.yaml` (constraints, $100K capital) and `config/candidates.yaml`
(stocks to choose from; replaced by research agents in Phase 3).

## Check

```bash
uv run pytest            # tests
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy src tests    # types
```

## Layout

```
src/committee/
  llm/types.py        provider-neutral Message / ToolCall / ModelProvider interface
  llm/mock.py         deterministic fake model (no API key needed)
  llm/openai_provider.py  OpenAI adapter (Responses API)
  llm/pricing.py      per-model token prices, for cost reporting
  settings.py         reads .env
  agent.py            the hand-written agent loop
  tools/              tools the model can call; Pydantic models = JSON Schema + validation
  market/data.py      price data: Yahoo (cached) or synthetic
  portfolio/          metrics, capital allocation, proposal validation
  events.py           events emitted during a run (later: stored + streamed to UI)
  service.py          one analysis run, shared by CLI and API
  api.py              FastAPI: /api/config, /api/runs/stream (SSE), serves ../web
  cli.py              `committee analyze` / `committee serve`
```
