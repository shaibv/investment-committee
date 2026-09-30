"""Rules a proposal must satisfy. Violations are sent back to the agent so it can fix them."""

from committee.domain import AllocationProposal, InvestorProfile

WEIGHT_TOLERANCE = 0.01


def validate_proposal(
    proposal: AllocationProposal, profile: InvestorProfile, allowed_tickers: set[str]
) -> list[str]:
    errors: list[str] = []
    tickers = [p.ticker.upper() for p in proposal.positions]

    if len(tickers) != len(set(tickers)):
        errors.append("Duplicate tickers in proposal.")
    if not profile.min_holdings <= len(tickers) <= profile.max_holdings:
        errors.append(
            f"Proposal has {len(tickers)} holdings; must be between "
            f"{profile.min_holdings} and {profile.max_holdings}."
        )

    total = sum(p.weight for p in proposal.positions)
    if abs(total - 1) > WEIGHT_TOLERANCE:
        errors.append(f"Weights sum to {total:.4f}; they must sum to 1.0.")

    for p in proposal.positions:
        t = p.ticker.upper()
        if p.weight > profile.max_weight + 1e-9:
            errors.append(f"{t} weight {p.weight:.2%} exceeds max {profile.max_weight:.0%}.")
        if t in {x.upper() for x in profile.excluded_tickers}:
            errors.append(f"{t} is excluded by the investor profile.")
        if t not in allowed_tickers:
            errors.append(f"{t} is not a candidate with available price data.")
    return errors
