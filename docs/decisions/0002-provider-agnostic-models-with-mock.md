# 0002 — Provider-agnostic model layer, mock-first

**Status:** Accepted (2026-09-30)

## Decision

- Write our own thin `ModelProvider` interface (chat + tool calls + structured output +
  token/cost accounting). One adapter per provider using the **official SDKs directly** —
  no LangChain/LiteLLM in phases 1–5.
- Ship a **MockProvider** first: deterministic, persona-driven fake responses so the
  whole system (debate, storage, UI) runs with zero API keys and zero cost. It is also
  what tests run against.
- Add real providers one at a time as you provision keys (candidates: Anthropic, OpenAI,
  Google Gemini, local Llama/Qwen via Ollama).
- Each agent's model is set in config, so "which model plays which role" is a knob to
  experiment with.

## Why

Writing the adapter layer yourself is where you actually learn how providers differ
(tool-call formats, JSON reliability, streaming). Mock-first unblocks everything while
keys are undecided.

## Guardrails

- Keys only in `.env` (git-ignored); never committed.
- Per-run token budget and a hard cap on rounds, enforced in code.
