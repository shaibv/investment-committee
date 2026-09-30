from committee.domain import AllocationProposal, InvestorProfile, ProposedPosition
from committee.portfolio.validation import validate_proposal

PROFILE = InvestorProfile(min_holdings=2, max_holdings=3, max_weight=0.6, excluded_tickers=["BAD"])


def proposal(**weights: float) -> AllocationProposal:
    return AllocationProposal(
        positions=[ProposedPosition(ticker=t, weight=w, rationale="r") for t, w in weights.items()],
        summary="s",
    )


def test_valid_proposal_has_no_errors() -> None:
    assert validate_proposal(proposal(A=0.5, B=0.5), PROFILE, {"A", "B"}) == []


def test_every_rule_is_reported() -> None:
    errors = validate_proposal(proposal(A=0.7, BAD=0.1, Z=0.1, Y=0.05), PROFILE, {"A", "BAD"})
    text = "\n".join(errors)
    assert "4 holdings" in text
    assert "sum to 0.95" in text
    assert "A weight 70.00% exceeds" in text
    assert "BAD is excluded" in text
    assert "Z is not a candidate" in text
