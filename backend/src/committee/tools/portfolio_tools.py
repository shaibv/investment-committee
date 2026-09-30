"""The tools a portfolio agent can call in Phase 1."""

import json

from pydantic import BaseModel, Field

from committee.domain import AllocationProposal, InvestorProfile
from committee.market.data import MarketData
from committee.portfolio.metrics import asset_stats, portfolio_stats
from committee.portfolio.validation import validate_proposal
from committee.tools.base import Tool, ToolError, ToolResult

SUBMIT_TOOL = "submit_allocation"


class PriceStatsArgs(BaseModel):
    tickers: list[str] = Field(description="Tickers to look up, e.g. ['AAPL', 'MSFT']")


class AnalyzeArgs(BaseModel):
    weights: dict[str, float] = Field(
        description="Ticker -> weight (fraction of capital). Should sum to 1."
    )


def build_tools(market: MarketData, profile: InvestorProfile, candidates: list[str]) -> list[Tool]:
    prices = market.price_history(candidates)
    available = set(map(str, prices.columns))

    def get_price_stats(args: PriceStatsArgs) -> dict[str, object]:
        requested = [t.upper() for t in args.tickers]
        found = [t for t in requested if t in available]
        return {
            "stats": asset_stats(prices[found]),
            "not_found": [t for t in requested if t not in available],
            "period": "trailing 1 year, daily prices",
        }

    def analyze_portfolio(args: AnalyzeArgs) -> dict[str, object]:
        weights = {t.upper(): w for t, w in args.weights.items()}
        missing = sorted(set(weights) - available)
        if missing:
            raise ToolError(f"No price data for: {', '.join(missing)}")
        return portfolio_stats(prices, weights)

    def submit_allocation(proposal: AllocationProposal) -> ToolResult:
        errors = validate_proposal(proposal, profile, available)
        if errors:
            raise ToolError(
                "Proposal rejected. Fix these and submit again:\n- " + "\n- ".join(errors)
            )
        return ToolResult(json.dumps({"status": "accepted"}), final=proposal)

    return [
        Tool(
            "get_price_stats",
            "Trailing-year statistics per ticker: last price, annualized return and "
            "volatility, max drawdown, Sharpe ratio.",
            PriceStatsArgs,
            get_price_stats,
        ),
        Tool(
            "analyze_portfolio",
            "Historical risk/return of a candidate set of weights, effective number of "
            "holdings, and the most correlated pairs. Use it to check a draft before submitting.",
            AnalyzeArgs,
            analyze_portfolio,
        ),
        Tool(
            SUBMIT_TOOL,
            "Submit your final allocation. It is validated against the investor profile; "
            "if rejected you'll get the reasons and can resubmit.",
            AllocationProposal,
            submit_allocation,
        ),
    ]
