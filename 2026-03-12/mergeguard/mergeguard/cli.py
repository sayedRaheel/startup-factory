import typer
from rich.console import Console
from rich.panel import Panel
import sys
from mergeguard.analyzer import run_analysis

app = typer.Typer(help="MergeGuard: Defend your repo against AI slop.")
console = Console()

@app.command()
def scan():
    """Scan current git diff for AI generation tells and architectural incoherence."""
    with console.status("[bold blue]Analyzing repository diff...[/bold blue]"):
        try:
            result = run_analysis()
        except Exception as e:
            console.print(f"[bold red]Error during analysis:[/bold red] {e}")
            raise typer.Exit(code=1)

    if result.get("status") == "skipped":
        console.print("[yellow]No changes detected to analyze.[/yellow]")
        return

    score = result["score"]
    passed = result["passed"]
    color = "green" if passed else "red"
    
    panel_content = (
        f"Authenticity Score: [bold {color}]{score}/100[/bold {color}]\n"
        f"Threshold: {result['threshold']}\n\n"
        f"[bold]Reasoning:[/bold]\n{result['reasoning']}"
    )
    
    console.print(Panel(panel_content, title="MergeGuard Analysis Result", border_style=color))

    if not passed and result["fail_on_block"]:
        console.print("[bold red]PR blocked: Authenticity score below threshold.[/bold red]")
        sys.exit(1)
    elif passed:
        console.print("[bold green]PR passed authenticity checks.[/bold green]")

if __name__ == "__main__":
    app()
