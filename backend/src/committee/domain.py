"""Domain models: the investor profile, what an agent proposes, and the resulting portfolio."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class InvestorProfile(BaseModel):
    capital_usd: float = Field(100_000, gt=0)
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    horizon_years: int = Field(5, gt=0)
    min_holdings: int = Field(8, ge=1)
    max_holdings: int = Field(15, ge=1)
    max_weight: float = Field(0.15, gt=0, le=1)
    markets: list[str] = Field(default_factory=lambda: ["US"])
    excluded_tickers: list[str] = Field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "InvestorProfile":
        return cls.model_validate(yaml.safe_load(path.read_text()))


class ProposedPosition(BaseModel):
    ticker: str
    weight: float = Field(gt=0, le=1, description="Fraction of capital, e.g. 0.12 for 12%")
    rationale: str = Field(description="Why this stock, at this weight")


class AllocationProposal(BaseModel):
    """What an agent submits. Weights only; code converts them into shares."""

    positions: list[ProposedPosition]
    summary: str = Field(description="Overall portfolio thesis in a few sentences")


class Holding(BaseModel):
    ticker: str
    target_weight: float
    price: float
    shares: int
    value: float


class Portfolio(BaseModel):
    holdings: list[Holding]
    cash: float
    total_value: float


def load_candidates(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text())
    return [str(t).upper() for t in data["candidates"]]
