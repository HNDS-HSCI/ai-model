import os
import json
import time
import csv
import re
import concurrent.futures
from datetime import datetime

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from runners.hsci_runner import HSCIRunner
from runners.gpt_runner import GPTRunner
from runners.claude_runner import ClaudeRunner
from runners.gemini_runner import GeminiRunner

def evaluate_run(task, output):
    """
    Regex boundary scoring to prevent substring false positives
    like VALID being found inside INVALID.
    """
    expected = task["expected"].upper()
    response = str(output).upper()
    
    valid_keywords = [
        "VALID", "INVALID", "CONTRADICTION", 
        "CONSISTENT", "INCONSISTENT", "MISSING_REQUIREMENT",
        "VALID_ORDER", "CYCLIC_DEPENDENCY", "INVALID_ORDER"
    ]
    
    # Strict Evaluation Rules:
    # 1. Expected keyword must be found.
    # 2. NO OTHER conflicting keywords can be present.
    
    # Extract candidate from Proven block if it exists
    match = re.search(r'\[TASK 1\] PROVEN: (.*)', response)
    if match:
        candidate = match.group(1).strip()
        found_keywords = []
        for kw in valid_keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', candidate):
                found_keywords.append(kw)
        if expected in found_keywords and len(found_keywords) == 1:
            return True
        return False

    # Fallback to general search
    found_keywords = []
    for kw in valid_keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', response):
            found_keywords.append(kw)
            
    if expected in found_keywords and len(found_keywords) == 1:
        return True
    return False

def run_with_timeout(runner, prompt, timeout=15):
    """
    Executes the runner with a hard 15 second timeout.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(runner.run, prompt)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return "TIMEOUT_ERROR"

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
                all_tasks.extend(tasks)
    return all_tasks

def run_benchmarks():
    base_dir = os.path.dirname(__file__)
    tasks = load_tasks(base_dir)
    
    if not tasks:
        print("No tasks found. Run generate_v2_tasks.py first.")
        return

    print(f"Loaded {len(tasks)} V2 tasks.")

    runners = [
        HSCIRunner()
    ]

    leaderboard = {r.name: {"correct": 0, "total_latency": 0.0, "total": 0, "timeouts": 0} for r in runners}

    os.makedirs(os.path.join(base_dir, "results"), exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = os.path.join(base_dir, "results", f"v2_benchmark_{timestamp}.csv")

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Task ID", "Category", "Runner", "Expected", "Output", "Is_Correct", "Latency_sec", "Timeout"])

        for i, task in enumerate(tasks):
            print(f"\n--- Task {i+1}/{len(tasks)}: [{task['category']}] {task['id']} ---")
            for runner in runners:
                start_time = time.time()
                
                # 15 second timeout protection
                output = run_with_timeout(runner, task["prompt"], timeout=15)
                latency = time.time() - start_time
                
                is_timeout = (output == "TIMEOUT_ERROR")
                is_correct = False if is_timeout else evaluate_run(task, output)
                
                writer.writerow([task["id"], task["category"], runner.name, task["expected"], str(output).replace("\n", " "), is_correct, round(latency, 3), is_timeout])
                
                leaderboard[runner.name]["total"] += 1
                if is_timeout:
                    leaderboard[runner.name]["timeouts"] += 1
                    leaderboard[runner.name]["total_latency"] += 15.0  # Cap timeout stat at 15s
                    print(f"[{runner.name}] TIMEOUT (15.0s)")
                else:
                    leaderboard[runner.name]["total_latency"] += latency
                    if is_correct:
                        leaderboard[runner.name]["correct"] += 1
                    print(f"[{runner.name}] Correct: {is_correct} | Latency: {latency:.2f}s")
    
    print("\n" + "="*70)
    print("FINAL V2 LEADERBOARD")
    print("="*70)
    print(f"{'Runner':<15} | {'Accuracy':<10} | {'Avg Latency':<15} | {'Timeouts':<10}")
    print("-" * 70)
    
    sorted_runners = sorted(leaderboard.items(), key=lambda x: x[1]["correct"], reverse=True)
    for name, stats in sorted_runners:
        acc = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        avg_lat = stats["total_latency"] / stats["total"] if stats["total"] > 0 else 0
        print(f"{name:<15} | {acc:>6.1f}%    | {avg_lat:>6.3f}s        | {stats['timeouts']}")
    print("="*70)
    print(f"Full results exported to: {csv_file}")

if __name__ == "__main__":
    run_benchmarks()
