# 0003 — Research-driven stock picking

**Status:** Accepted (2026-09-30)

## Decision

The portfolio is built **entirely from individual stocks** that research agents discover
in news and social media. There is no predefined universe.

### Two-stage pipeline

1. **Research stage** — researcher agents scan sources and produce a
   **candidate dossier**: a shortlist of tickers, each with a thesis, bull/bear points,
   sentiment, and **citations** (URL, source, date, quote) for every claim.
2. **Committee stage** — the persona agents (on different models) debate the dossier and
   converge on a final set of stocks and weights.

### Sources (each behind a `Source` interface, pluggable)

| Source | What it gives | Cost / key |
|---|---|---|
| Model web search (Claude / GPT / Gemini built-in tool) | Broad news, analysis, blogs | Small per-search fee on the provider bill |
| Financial news APIs (Finnhub, Alpha Vantage) | Ticker-tagged headlines + sentiment scores | Free tiers; you create keys |
| Reddit (r/stocks, r/investing, r/wallstreetbets, …) | Retail sentiment, trending tickers | Free API app with rate limits; you create it |

Price data (`yfinance`, free, no key) is still used as a **tool**, not a source: it
verifies a ticker exists and computes volatility, correlation, and concentration for
the proposed portfolio. Agents reason; code does the math.

### Investor profile

`config/profile.yaml`: risk tolerance, horizon, number of holdings (e.g. 8–15),
max weight per stock, exclusions (sectors/tickers), markets allowed (e.g. US only).

### Validation

No performance tracking. The UI shows the reasoning: dossier, citations, debate, and
final rationale. You judge the picks. (Every run is still stored as events per ADR 0004,
so tracking can be added later without redesign if you change your mind.)

## Engineering concerns this introduces (the learning part)

- **Untrusted input / prompt injection.** Reddit posts and web pages are written by
  strangers and may contain text aimed at the agent. Researchers only have read-only
  tools, fetched content is wrapped and labeled as data, and the committee never sees
  raw pages, only the structured dossier.
- **Grounding.** Every claim in the dossier must carry a citation; a validator rejects
  claims without one. This is how we limit hallucinated "news".
- **Hype filtering.** Social sentiment is noisy and manipulable (pump-and-dumps). The
  Risk Manager persona is explicitly tasked with challenging social-only theses.
- **Cost and rate limits.** Caching of fetched content, per-run search budget, backoff.

## Alternatives considered

- Fixed ETF universe (v1) — rejected: you want discovery.
- Core + satellite — rejected: you chose pure stock picking.
