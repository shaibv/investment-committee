import pandas as pd
import pytest

from committee.portfolio.metrics import allocate_capital, asset_stats, portfolio_stats


def test_asset_stats_on_known_series() -> None:
    prices = pd.DataFrame({"X": [100.0, 110.0, 99.0, 121.0]})
    stats = asset_stats(prices)["X"]
    assert stats["last_price"] == 121.0
    assert stats["max_drawdown"] == pytest.approx(-0.10)  # 110 -> 99


def test_portfolio_stats_reports_concentration_and_correlation() -> None:
    prices = pd.DataFrame(
        {"A": [1.0, 1.1, 1.2, 1.1], "B": [1.0, 1.1, 1.21, 1.1], "C": [1.0, 0.9, 1.0, 1.05]}
    )
    stats = portfolio_stats(prices, {"A": 0.5, "B": 0.25, "C": 0.25})
    assert stats["weights_sum"] == 1.0
    assert stats["effective_holdings"] == pytest.approx(1 / (0.25 + 0.0625 + 0.0625), abs=0.01)
    top_pair = stats["most_correlated_pairs"][0]  # type: ignore[index]
    assert top_pair["pair"] == "A/B"


def test_allocate_capital_buys_whole_shares_and_keeps_remainder_as_cash() -> None:
    portfolio = allocate_capital({"A": 0.5, "B": 0.5}, {"A": 300.0, "B": 7.0}, 1000.0)
    shares = {h.ticker: h.shares for h in portfolio.holdings}
    assert shares == {"A": 1, "B": 71}
    assert portfolio.cash == pytest.approx(1000 - 300 - 497)
