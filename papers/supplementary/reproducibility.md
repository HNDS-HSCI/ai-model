# Supplementary Reproducibility Package & Hardware Manifest

## Hardware & Software Specifications
* **Operating System**: Windows 11 / x86_64
* **Python Environment**: Python 3.13.1
* **PyTest Version**: 9.0.2
* **Z3 Solver Version**: 4.14.0.0
* **PyTorch Version**: 2.7.0 / CPU

---

## Reproduction Commands

```bash
# 1. Environment Verification & Full Unit/Integration Regression (257 passing tests)
pytest hsci/tests/ -v

# 2. Benchmark Suite Execution & Result Export
python -c "from hsci.benchmarks.runner import BenchmarkRunner; [BenchmarkRunner(p, output_dir='results').run() for p in ['hsci/benchmarks/manifests/formal_logic.yaml', 'hsci/benchmarks/manifests/graph_planning.yaml', 'hsci/benchmarks/manifests/lifecycle.yaml', 'hsci/benchmarks/manifests/security.yaml']]"

# 3. Benchmark Infrastructure Unit Suite Verification
pytest hsci/tests/test_benchmark_framework.py -v
```
