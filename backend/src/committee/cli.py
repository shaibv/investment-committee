"""Command-line entry point: `uv run committee analyze` / `uv run committee serve`."""

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from committee.agent import AgentError
from committee.events import Event
from committee.service import ConfigError, DataSource, ProviderName, run_analysis

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


@app.callback()
def main() -> None:
    """Investment Committee: AI agents that build a paper portfolio."""


def print_event(event: Event) -> None:
    d = event.data
    match event.type:
        case "agent_started":
            console.rule(f"[bold]{event.agent}[/] on [cyan]{d['provider']}[/]")
        case "model_response" if d["text"]:
            console.print(f"[dim]turn {d['turn']}[/] [italic]{d['text']}[/]")
        case "tool_call":
            args = json.dumps(d["arguments"])
            args = args if len(args) <= 120 else args[:120] + "…"
            console.print(f"  [yellow]→ {d['tool']}[/]({args})")
        case "tool_result":
            style, label = ("red", "✗ rejected") if d["is_error"] else ("green", "✓")
            preview = d["content"].replace("\n", " ")
            console.print(f"  [{style}]{label}[/] [dim]{preview[:140]}…[/]")
        case "agent_nudged":
            console.print("  [magenta]nudged: model answered without a tool call[/]")
        case "agent_submitted":
            u = d["usage"]
            console.print(
                f"[green]submitted[/] after {d['turn']} turns · "
                f"{u['input_tokens']:,} in / {u['output_tokens']:,} out tokens"
            )


@app.command()
def analyze(
    provider: ProviderName = ProviderName.mock,
    data: Annotated[DataSource, typer.Option(help="Price source.")] = DataSource.yahoo,
) -> None:
    """Run one portfolio agent over the candidate list and print its allocation."""
    try:
        result = run_analysis(provider, data, on_event=print_event)
    except (ConfigError, AgentError) as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1) from e

    rationale = {p.ticker.upper(): p.rationale for p in result.proposal.positions}
    p = result.portfolio
    table = Table(title=f"Paper portfolio · ${p.total_value:,.0f}")
    for col in ["Ticker", "Weight", "Shares", "Price", "Value", "Rationale"]:
        table.add_column(col, justify="left" if col in {"Ticker", "Rationale"} else "right")
    for h in sorted(p.holdings, key=lambda h: -h.target_weight):
        table.add_row(
            h.ticker,
            f"{h.target_weight:.1%}",
            str(h.shares),
            f"${h.price:,.2f}",
            f"${h.value:,.2f}",
            rationale[h.ticker],
        )
    table.add_row("CASH", "", "", "", f"${p.cash:,.2f}", "leftover from whole shares")
    console.print(table)

    s = result.stats
    console.print(f"[bold]Thesis:[/] {result.proposal.summary}")
    console.print(
        f"[bold]Trailing year:[/] return {s['annual_return']:.1%} · "
        f"volatility {s['annual_volatility']:.1%} · "
        f"max drawdown {s['max_drawdown']:.1%} · Sharpe {s['sharpe']}"
    )
    if result.cost_usd is not None:
        console.print(f"[bold]Model cost:[/] ${result.cost_usd:.4f}")
    if data is DataSource.synthetic:
        console.print("[yellow]Synthetic prices: numbers are fake, for offline testing only.[/]")


@app.command()
def serve(port: int = 8000, reload: bool = True) -> None:
    """Start the web API for the frontend."""
    import uvicorn

    uvicorn.run("committee.api:app", host="127.0.0.1", port=port, reload=reload)
