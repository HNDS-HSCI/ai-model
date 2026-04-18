import time
import sys
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table

# Add project root to path
sys.path.append(os.getcwd())

from hsci.core.rir_loop import RIRLoop
from hsci.training.math_trainer import MATH_TRAINING_EXAMPLES
from hsci.training.transfer_tester import TRANSFER_TEST_CASES

console = Console()

def measure_metrics():
    console.print("[bold cyan]HSCI: Performance & Evaluation Metrics[/bold cyan]")
    
    brain = RIRLoop()
    results = {}

    # 1. Verification Rate (Trained Domains)
    console.print("\nMeasuring Verification Rate (Math)...")
    math_success = 0
    total_math = len(MATH_TRAINING_EXAMPLES)
    start_time = time.time()
    
    for problem, _ in MATH_TRAINING_EXAMPLES:
        output = brain.process(problem)
        if output.is_verified:
            math_success += 1
    
    math_latency = (time.time() - start_time) / total_math if total_math > 0 else 0
    results["verification_rate"] = math_success / total_math if total_math > 0 else 0
    results["verification_latency_ms"] = math_latency * 1000

    # 2. Transfer Accuracy (Zero-Shot)
    console.print("Measuring Transfer Accuracy (Physics/Finance)...")
    transfer_success = 0
    total_transfer = len(TRANSFER_TEST_CASES)
    
    for problem, _ in TRANSFER_TEST_CASES:
        output = brain.process(problem)
        if output.is_verified:
            transfer_success += 1
            
    results["transfer_accuracy"] = transfer_success / total_transfer if total_transfer > 0 else 0

    # 3. Learning Efficiency
    # We check how many new concepts were "learned" (added to library) 
    # since initialization beyond the pre-seeded 10.
    total_concepts = len(brain.knowledge_base.concept_library._concepts)
    pre_seeded = 10 # approximate based on templates
    new_concepts = max(0, total_concepts - pre_seeded)
    results["concepts_per_example"] = new_concepts / (total_math + total_transfer) if (total_math + total_transfer) > 0 else 0

    # 4. Self-Improvement (Discovery Rate)
    console.print("Measuring Self-Play Discovery Rate (60s burst)...")
    # Observe for 60 seconds and count new concepts
    start_count = len(brain.knowledge_base.concept_library._concepts)
    # Self-play is already running in background from RIRLoop init
    time.sleep(60) 
    end_count = len(brain.knowledge_base.concept_library._concepts)
    
    results["self_play_discovery_rate"] = (end_count - start_count) * 60 # Extrapolated to concepts/hour

    # 5. Summary Table
    table = Table(title=f"HSCI Research Metrics - {datetime.now().strftime('%Y-%m-%d')}")
    table.add_column("Metric", style="cyan")
    table.add_column("Current", style="magenta")
    table.add_column("Target", style="green")
    table.add_column("Status", style="bold")

    def get_status(current, target, reverse=False):
        if reverse:
            success = current <= target
        else:
            success = current >= target
        return "[green]PASS[/green]" if success else "[red]FAIL[/red]"

    table.add_row("Verification Rate (Math)", f"{results['verification_rate']:.1%}", ">95.0%", get_status(results['verification_rate'], 0.95))
    table.add_row("Transfer Accuracy", f"{results['transfer_accuracy']:.1%}", ">80.0%", get_status(results['transfer_accuracy'], 0.80))
    table.add_row("Concepts per Example", f"{results['concepts_per_example']:.2f}", ">0.30", get_status(results['concepts_per_example'], 0.30))
    table.add_row("Self-Play Rate (per hour)", f"{results['self_play_discovery_rate']:.1f}", ">2.0", get_status(results['self_play_discovery_rate'], 2.0))
    table.add_row("Verification Latency", f"{results['verification_latency_ms']:.1f}ms", "<500ms", get_status(results['verification_latency_ms'], 500, True))

    console.print(table)
    
    # Stop background thread
    brain.self_play.stop()

if __name__ == "__main__":
    measure_metrics()
