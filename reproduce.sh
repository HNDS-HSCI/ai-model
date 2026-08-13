#!/bin/bash
set -e

echo "=== HSCI Phase 8C One-Click Bash Reproducibility Script ==="

echo "1. Running Full Regression Test Suite..."
pytest hsci/tests/ -v

echo "2. Executing Benchmark Manifests (N=30 runs per manifest)..."
python -c "from hsci.benchmarks.runner import BenchmarkRunner; [BenchmarkRunner(p, output_dir='results').run() for p in ['hsci/benchmarks/manifests/formal_logic.yaml', 'hsci/benchmarks/manifests/graph_planning.yaml', 'hsci/benchmarks/manifests/lifecycle.yaml', 'hsci/benchmarks/manifests/security.yaml']]"

echo "3. Validating LaTeX & JSON Publication Consistency..."
pytest scratch/test_hsci_pub_2_consistency.py -v

echo "=== Reproduction Successfully Completed ==="
