"""Market data sources behind one interface.

- YahooMarketData: real prices via yfinance, cached to parquet (one file per request per day).
- SyntheticMarketData: deterministic fake prices, for offline runs and tests.
"""

import hashlib
from datetime import date
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd


class MarketData(Protocol):
    def price_history(self, tickers: list[str], days: int = 365) -> pd.DataFrame:
        """Daily adjusted close prices. Index: dates. Columns: tickers that were found.

        Unknown tickers are silently omitted; callers compare columns to what they asked for.
        """
        ...


class YahooMarketData:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def price_history(self, tickers: list[str], days: int = 365) -> pd.DataFrame:
        tickers = sorted({t.upper() for t in tickers})
        key = hashlib.sha1(",".join(tickers).encode()).hexdigest()[:12]
        cache_file = self.cache_dir / f"{date.today()}_{days}d_{key}.parquet"
        if cache_file.exists():
            cached: pd.DataFrame = pd.read_parquet(cache_file)
            return cached

        import yfinance as yf  # imported lazily: slow import, only needed for live data

        raw = yf.download(
            tickers, period=f"{days}d", auto_adjust=True, progress=False, threads=True
        )
        closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
        if not isinstance(raw.columns, pd.MultiIndex):
            closes.columns = tickers
        result = pd.DataFrame(closes).dropna(axis=1, how="all").ffill().dropna()
        result.to_parquet(cache_file)
        return result


class SyntheticMarketData:
    """Geometric Brownian motion per ticker. Same ticker + seed -> same prices, always."""

    def __init__(self, seed: int = 7, unknown: set[str] | None = None) -> None:
        self.seed = seed
        self.unknown = unknown or set()

    def price_history(self, tickers: list[str], days: int = 365) -> pd.DataFrame:
        trading_days = int(days * 252 / 365)
        index = pd.bdate_range(end=pd.Timestamp("2026-09-30"), periods=trading_days)
        columns: dict[str, np.ndarray] = {}
        for ticker in sorted({t.upper() for t in tickers} - self.unknown):
            digest = int(hashlib.sha1(f"{ticker}:{self.seed}".encode()).hexdigest()[:8], 16)
            rng = np.random.default_rng(digest)
            annual_drift = rng.uniform(-0.10, 0.35)
            annual_vol = rng.uniform(0.15, 0.55)
            start_price = rng.uniform(20, 600)
            daily = rng.normal(
                annual_drift / 252 - annual_vol**2 / 504,
                annual_vol / np.sqrt(252),
                trading_days,
            )
            columns[ticker] = start_price * np.exp(np.cumsum(daily))
        return pd.DataFrame(columns, index=index)
