# Investment Committee

A committee of AI agents — each on a different model, each with a different investing
philosophy — debates a portfolio built from a defined universe of ETFs/stocks until it
converges on a balanced allocation. A web UI shows the decision, the reasoning, and lets
you drill into every round of the debate.

## Goals

1. **Learn** advanced AI engineering (multi-agent orchestration, tool use, structured
   output, evals, observability, cost control) and modern dev-environment practice.
2. **Improve my portfolio thinking** — the committee's output is an input to my own
   judgment, validated by backtests against simple benchmarks. Not financial advice.

## Working model

- Claude writes the code.
- I own every decision and all provisioning (keys, accounts, spend, installs).
- Significant choices are recorded as ADRs in [`docs/decisions/`](docs/decisions/) and stay
  `Proposed` until I approve them.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for phases.
