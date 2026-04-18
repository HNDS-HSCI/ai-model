import sys
import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add project root to path
sys.path.append(os.getcwd())

from hsci.core.rir_loop import RIRLoop

console = Console()

def main():
    console.print(Panel.fit(
        "[bold cyan]HSCI: Hyper-Symbolic Cognitive Intelligence v3.1[/bold cyan]\n"
        "[italic]Axiomatic Intelligence Engine — Transactional Reasoning & Verification[/italic]",
        border_style="cyan"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Waking up the brain...", total=None)
        brain = RIRLoop()
        time.sleep(1)

    console.print("[green]Brain active and listening. Type 'exit' to rest.[/green]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold magenta]User[/bold magenta]")
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("\n[yellow]Resting the brain. Goodbye.[/yellow]")
                brain.self_play.stop()
                break

            if not user_input.strip():
                continue

            # Check for special commands
            if user_input.startswith("teach:"):
                console.print("[yellow]Learning mode engaged. (Placeholder for manual concept injection)[/yellow]")
                continue
            
            if user_input.startswith("stats"):
                stats = brain.self_play.stats
                table = Table(title="Brain Runtime Stats")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="magenta")
                for k, v in stats.items():
                    table.add_row(k, str(v))
                console.print(table)
                continue

            # Process through RIR Loop
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Reasoning...", total=None)
                response = brain.process(user_input)

            console.print(f"\n[bold cyan]HSCI[/bold cyan]\n{response}\n")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to close properly.[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Error in cognition loop: {e}[/bold red]")

if __name__ == "__main__":
    main()
