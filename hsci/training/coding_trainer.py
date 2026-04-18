import sys
import os
from datetime import datetime
from rich.console import Console

# Add project root to path
sys.path.append(os.getcwd())

from hsci.core.rir_loop import RIRLoop

CODING_EXAMPLES = [
    ("Find sum of even numbers from 1 to 10", "result == 2+4+6+8+10"),
    ("Write code to check if number x is positive", "x > 0"),
    ("Verify if x=10 satisfies invariant x > 5", "x > 5"),
    ("Construct algorithm for area of triangle with base 10, height 5", "area == (10 * 5) / 2")
]

console = Console()

def train_synthesis():
    console.print("[bold cyan]HSCI: Phase 2 Training — Synthesis & Logic[/bold cyan]")
    brain = RIRLoop()
    
    success = 0
    for i, (problem, expected) in enumerate(CODING_EXAMPLES):
        console.print(f"\n[{i+1}/{len(CODING_EXAMPLES)}] Coding Problem: {problem}")
        response = brain.process(problem)
        console.print(f"Brain Response: {response}")
        if "✓" in response:
            success += 1
            
    console.print(f"\n[bold green]Synthesis Training Complete. Success: {success}/{len(CODING_EXAMPLES)}[/bold green]")
    brain.self_play.stop()

if __name__ == "__main__":
    train_synthesis()
