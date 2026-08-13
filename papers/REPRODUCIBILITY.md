# REPRODUCIBILITY GUIDE — HSCI Phase 8C

## Executive Summary
This guide provides the complete, one-command protocol to reproduce all unit tests, integration regression tests, benchmark executions ($N=30$ runs per manifest, Total $N=240$), LaTeX table generation, and paper compilation for **Hyper-Symbolic Cognitive Invention (HSCI)**.

---

## Hardware & Environment Specifications
* **Operating System**: Windows 11 / x86_64 (Tested on PowerShell 7+)
* **Python**: 3.13.1
* **PyTest**: 9.0.2
* **Z3 Solver**: 4.14.0.0
* **PyTorch**: 2.7.0 / CPU

---

## One-Click Reproduction Commands

### PowerShell (Windows)
```powershell
.\reproduce.ps1
```

### Bash (Linux/macOS)
```bash
./reproduce.sh
```

---

## Step-by-Step Reproduction Breakdown

1. **Regression Suite**:
   ```bash
   pytest hsci/tests/ -v
   ```
2. **Benchmark Suites Execution**:
   ```bash
   python -c "from hsci.benchmarks.runner import BenchmarkRunner; [BenchmarkRunner(p, output_dir='results').run() for p in ['hsci/benchmarks/manifests/formal_logic.yaml', 'hsci/benchmarks/manifests/graph_planning.yaml', 'hsci/benchmarks/manifests/lifecycle.yaml', 'hsci/benchmarks/manifests/security.yaml']]"
   ```
3. **Automated Consistency Validation**:
   ```bash
   pytest scratch/test_hsci_pub_2_consistency.py -v
   ```
