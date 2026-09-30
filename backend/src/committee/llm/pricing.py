"""USD per 1M tokens (input, output). Source: developers.openai.com/api/docs/pricing, 2026-09-30."""

from committee.llm.types import Usage

PRICES: dict[str, tuple[float, float]] = {
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6.1-sol": (2.00, 10.00),
    "gpt-6-astra": (10.00, 50.00),
}


def cost_usd(model: str, usage: Usage) -> float | None:
    """None when we don't know the model's price."""
    if model not in PRICES:
        return None
    price_in, price_out = PRICES[model]
    return (usage.input_tokens * price_in + usage.output_tokens * price_out) / 1_000_000
