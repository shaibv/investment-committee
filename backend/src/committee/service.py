"""One analysis run, shared by the CLI and the web API."""

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from committee.agent import Agent
from committee.domain import AllocationProposal, InvestorProfile, Portfolio, load_candidates
from committee.events import EventHandler
from committee.llm.mock import MockProvider
from committee.llm.openai_provider import OpenAIProvider
from committee.llm.pricing import cost_usd
from committee.llm.types import ModelProvider, Usage
from committee.market.data import MarketData, SyntheticMarketData, YahooMarketData
from committee.portfolio.metrics import allocate_capital, portfolio_stats
from committee.prompts import ANALYST_SYSTEM_PROMPT, build_task
from committee.settings import BACKEND_DIR, get_settings
from committee.tools.portfolio_tools import build_tools

CONFIG_DIR = BACKEND_DIR / "config"


class DataSource(StrEnum):
    yahoo = "yahoo"
    synthetic = "synthetic"


class ProviderName(StrEnum):
    mock = "mock"
    openai = "openai"


class ConfigError(Exception):
    """Something the user must fix (e.g. a missing API key)."""


class AnalysisResult(BaseModel):
    provider: str
    data_source: DataSource
    proposal: AllocationProposal
    portfolio: Portfolio
    stats: dict[str, object]
    turns: int
    usage: Usage
    cost_usd: float | None


def available_providers() -> list[ProviderName]:
    key = get_settings().openai_api_key
    has_openai = key is not None and bool(key.get_secret_value())
    return [ProviderName.mock] + ([ProviderName.openai] if has_openai else [])


def make_provider(name: ProviderName) -> ModelProvider:
    if name is ProviderName.mock:
        return MockProvider()
    settings = get_settings()
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
        raise ConfigError("OPENAI_API_KEY is not set. Add it to backend/.env.")
    return OpenAIProvider(settings.openai_api_key.get_secret_value(), settings.openai_model)


def make_market(source: DataSource) -> MarketData:
    if source is DataSource.yahoo:
        return YahooMarketData(BACKEND_DIR / ".cache" / "prices")
    return SyntheticMarketData()


def run_analysis(
    provider_name: ProviderName,
    data_source: DataSource,
    on_event: EventHandler | None = None,
    profile_path: Path = CONFIG_DIR / "profile.yaml",
    candidates_path: Path = CONFIG_DIR / "candidates.yaml",
) -> AnalysisResult:
    """Raises ConfigError for user-fixable problems and AgentError if the agent fails."""
    profile = InvestorProfile.load(profile_path)
    candidates = load_candidates(candidates_path)
    provider = make_provider(provider_name)
    market = make_market(data_source)
    tools = build_tools(market, profile, candidates)
    prices = market.price_history(candidates)  # cached, so this is not a second download

    agent = Agent("Portfolio Analyst", ANALYST_SYSTEM_PROMPT, provider, tools, on_event=on_event)
    result = agent.run(build_task(profile, candidates))
    assert isinstance(result.final, AllocationProposal)

    weights = {p.ticker.upper(): p.weight for p in result.final.positions}
    last_prices = {t: float(prices[t].iloc[-1]) for t in weights}
    return AnalysisResult(
        provider=provider.name,
        data_source=data_source,
        proposal=result.final,
        portfolio=allocate_capital(weights, last_prices, profile.capital_usd),
        stats=portfolio_stats(prices, weights),
        turns=result.turns,
        usage=result.usage,
        cost_usd=(
            cost_usd(provider.model, result.usage) if isinstance(provider, OpenAIProvider) else None
        ),
    )
