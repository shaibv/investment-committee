"""Prompts for the Phase 1 single agent."""

import json

from committee.domain import InvestorProfile

ANALYST_SYSTEM_PROMPT = """\
You are a disciplined portfolio analyst managing a paper-trading portfolio.

How you work:
- Never estimate numbers yourself. Use get_price_stats and analyze_portfolio for all
  returns, volatility, drawdown, and correlation figures.
- Check a draft with analyze_portfolio before submitting. Watch for concentration and
  highly correlated pairs.
- Finish by calling submit_allocation. If it is rejected, read the reasons, fix them,
  and resubmit.
- Every position needs a specific rationale that references the numbers you saw.
"""


def build_task(profile: InvestorProfile, candidates: list[str]) -> str:
    context = {"profile": profile.model_dump(), "candidates": candidates}
    return (
        f"Allocate ${profile.capital_usd:,.0f} of virtual capital across a subset of the "
        "candidate stocks below, respecting the investor profile.\n\n"
        f"```json\n{json.dumps(context, indent=2)}\n```"
    )
