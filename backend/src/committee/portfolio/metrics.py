"""Deterministic portfolio math. Agents reason about these numbers; they never compute them."""

import math

import pandas as pd

from committee.domain import Holding, Portfolio

TRADING_DAYS = 252
RISK_FREE_RATE = 0.04


def _series_stats(prices: pd.Series) -> dict[str, float]:
    returns = prices.pct_change().dropna()
    years = len(returns) / TRADING_DAYS
    total_return = prices.iloc[-1] / prices.iloc[0] - 1
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
    annual_vol = float(returns.std() * math.sqrt(TRADING_DAYS))
    drawdown = prices / prices.cummax() - 1
    sharpe = (annual_return - RISK_FREE_RATE) / annual_vol if annual_vol > 0 else 0.0
    return {
        "annual_return": round(float(annual_return), 4),
        "annual_volatility": round(annual_vol, 4),
        "max_drawdown": round(float(drawdown.min()), 4),
        "sharpe": round(float(sharpe), 3),
    }


def asset_stats(prices: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Per-ticker last price, annualized return/volatility, max drawdown, Sharpe."""
    return {
        str(ticker): {"last_price": round(float(prices[ticker].iloc[-1]), 2)}
        | _series_stats(prices[ticker])
        for ticker in prices.columns
    }


def portfolio_stats(prices: pd.DataFrame, weights: dict[str, float]) -> dict[str, object]:
    """Historical behaviour of a weighted portfolio (daily-rebalanced approximation)."""
    tickers = list(weights)
    returns = prices[tickers].pct_change().dropna()
    w = pd.Series(weights)
    growth = (1 + returns @ w).cumprod()

    corr = returns.corr()
    pairs = [
        (a, b, float(corr.to_numpy()[i, j]))
        for i, a in enumerate(tickers)
        for j, b in enumerate(tickers)
        if j > i
    ]
    most_correlated = sorted(pairs, key=lambda p: p[2], reverse=True)[:3]
    hhi = float((w**2).sum())

    return _series_stats(growth) | {
        "weights_sum": round(float(w.sum()), 4),
        "effective_holdings": round(1 / hhi, 2) if hhi > 0 else 0.0,
        "most_correlated_pairs": [
            {"pair": f"{a}/{b}", "correlation": round(c, 3)} for a, b, c in most_correlated
        ],
    }


def allocate_capital(
    weights: dict[str, float], last_prices: dict[str, float], capital: float
) -> Portfolio:
    """Turn target weights into whole shares; whatever can't buy a full share stays cash."""
    holdings = []
    for ticker, weight in weights.items():
        price = last_prices[ticker]
        shares = int((capital * weight) // price)
        holdings.append(
            Holding(
                ticker=ticker,
                target_weight=weight,
                price=round(price, 2),
                shares=shares,
                value=round(shares * price, 2),
            )
        )
    invested = sum(h.value for h in holdings)
    return Portfolio(holdings=holdings, cash=round(capital - invested, 2), total_value=capital)
