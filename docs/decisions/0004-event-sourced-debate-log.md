# 0004 — Every debate step is a stored event

**Status:** Accepted (2026-09-30)

## Decision

A debate run is an append-only list of typed events:

`run_started`, `round_started`, `agent_proposal` (allocation JSON + rationale),
`agent_critique` (target agent, points), `tool_call` / `tool_result`,
`agent_revision` (old → new allocation + what changed its mind),
`consensus_check` (distance metric), `run_completed` (final allocation, summary,
tokens, cost).

- Stored in SQLite, streamed to the UI over **Server-Sent Events** while running.
- The UI renders both live runs and history from the same events — replay is free.

## Why

This is what makes the "dive into the debate" UI possible, and it doubles as the
dataset for evals (phase 5). It's also a transferable pattern (event sourcing).
