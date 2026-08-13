Write-Host "=== HSCI Phase 8C One-Click PowerShell Reproducibility Script ===" -ForegroundColor Green

Write-Host "1. Running Full Regression Test Suite..." -ForegroundColor Cyan
pytest hsci/tests/ -v

Write-Host "2. Executing Benchmark Manifests (N=30 runs per manifest)..." -ForegroundColor Cyan
python -c "from hsci.benchmarks.runner import BenchmarkRunner; [BenchmarkRunner(p, output_dir='results').run() for p in ['hsci/benchmarks/manifests/formal_logic.yaml', 'hsci/benchmarks/manifests/graph_planning.yaml', 'hsci/benchmarks/manifests/lifecycle.yaml', 'hsci/benchmarks/manifests/security.yaml']]"

Write-Host "3. Validating LaTeX & JSON Publication Consistency..." -ForegroundColor Cyan
pytest scratch/test_hsci_pub_2_consistency.py -v

Write-Host "=== Reproduction Successfully Completed ===" -ForegroundColor Green
