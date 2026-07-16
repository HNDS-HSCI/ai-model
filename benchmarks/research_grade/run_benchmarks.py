import os
import json
import time
import csv
from datetime import datetime

# Adjust sys.path to find runners
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from runners.hsci_runner import HSCIRunner
from runners.gpt_runner import GPTRunner
from runners.claude_runner import ClaudeRunner
from runners.gemini_runner import GeminiRunner

def load_tasks(benchmarks_dir):
    categories = [
        "constraint_verification",
        "requirements_analysis",
        "architecture_planning",
        "state_machine_verification",
        "dependency_resolution"
    ]
    all_tasks = []
    for cat in categories:
        task_file = os.path.join(benchmarks_dir, cat, "tasks.json")
        if os.path.exists(task_file):
            with open(task_file, "r") as f:
                tasks = json.load(f)
                for t in tasks:
                    t["category"] = cat
                all_tasks.extend(tasks)
    return all_tasks

def run_benchmarks():
    base_dir = os.path.dirname(__file__)
    tasks = load_tasks(base_dir)
    
    if not tasks:
        print("No tasks found. Run generate_research_tasks.py first.")
        return

    print(f"Loaded {len(tasks)} Research-Grade tasks.")

    runners = [
        HSCIRunner(),
        GPTRunner(),
        ClaudeRunner(),
        GeminiRunner()
    ]

    leaderboard = {r.name: {"correct": 0, "total_latency": 0.0, "total": 0} for r in runners}

    os.makedirs(os.path.join(base_dir, "results"), exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = os.path.join(base_dir, "results", f"research_benchmark_{timestamp}.csv")

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Task ID", "Category", "Difficulty", "Runner", "Expected", "Output", "Is_Correct", "Latency_sec"])

        for i, task in enumerate(tasks):
            print(f"\n--- Task {i+1}/{len(tasks)}: [{task['category']} | {task['difficulty'].upper()}] {task['id']} ---")
            for runner in runners:
                start_time = time.time()
                output = runner.run(task["prompt"])
                latency = time.time() - start_time
                
                is_correct = task["expected"].lower() in str(output).lower()
                
                writer.writerow([task["id"], task["category"], task["difficulty"], runner.name, task["expected"], str(output).replace("\n", " "), is_correct, round(latency, 3)])
                
                leaderboard[runner.name]["total"] += 1
                leaderboard[runner.name]["total_latency"] += latency
                if is_correct:
                    leaderboard[runner.name]["correct"] += 1

                print(f"[{runner.name}] Correct: {is_correct} | Latency: {latency:.2f}s")
    
    print("\n" + "="*50)
    print("🏆 FINAL RESEARCH LEADERBOARD 🏆")
    print("="*50)
    print(f"{'Runner':<15} | {'Accuracy':<10} | {'Avg Latency':<15}")
    print("-" * 50)
    
    sorted_runners = sorted(leaderboard.items(), key=lambda x: x[1]["correct"], reverse=True)
    for name, stats in sorted_runners:
        acc = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        avg_lat = stats["total_latency"] / stats["total"] if stats["total"] > 0 else 0
        print(f"{name:<15} | {acc:>6.1f}%    | {avg_lat:>6.3f}s")
    print("="*50)
    print(f"Full results exported to: {csv_file}")

if __name__ == "__main__":
    run_benchmarks()
