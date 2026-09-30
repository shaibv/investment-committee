# Roadmap

Each phase ends with something runnable and a short "what you learned" note.

| Phase | Deliverable | Learning focus | Needs from you |
|---|---|---|---|
| 0. Foundations | Monorepo, `uv` + `pnpm`, lint/format/typecheck, tests, pre-commit, Docker Compose, CI (GitHub Actions), CLAUDE.md | Modern dev-environment practice | Approve ADRs 0001–0004; create GitHub repo (optional) |
| 1. Single agent + tools | One agent with price/portfolio-math tools on the **mock provider**, CLI output | Tool-use loop by hand, structured output, no framework | — |
| 2. Multi-model | Provider-agnostic interface; mock + Ollama + first real API | Abstraction design, provider differences, retries, cost tracking | Choose providers, create API keys, set a spend cap |
| 3. Research agents | Sources (web search, Finnhub/Alpha Vantage, Reddit) → cited candidate dossier | Web research, grounding/citations, prompt-injection defense, caching, rate limits | Create news-API and Reddit app keys |
| 4. Debate engine | Committee: propose → critique → revise → converge; event store | Multi-agent protocols, convergence criteria, persistence | Approve debate-protocol ADR |
| 5. Frontend | Next.js: Decision view, Research Dossier with citations, Debate Explorer, convergence chart, live streaming | Full-stack typed contracts, SSE streaming | Review UI |
| 6. Quality & observability | Tracing (Langfuse), per-run cost, citation-accuracy checks, LLM-as-judge on reasoning quality | Measuring agents when there's no ground truth | Approve Langfuse (self-hosted, Docker) |
| 7. Framework comparison | Re-implement orchestrator in LangGraph / Claude Agent SDK, compare | When frameworks help vs hurt | — |
