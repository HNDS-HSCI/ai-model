# HSCI Scientific Publication Package (HSCI-PUB-1)

## Overview

This directory contains the reproducible publication package for the paper:

> **Hyper-Symbolic Cognitive Invention (HSCI): Unified Graph & Registry Lifecycle Management with Strict SMT Verification Authority**

All empirical tables, metrics, figures, TikZ diagrams, references, and supplementary material in this repository are derived directly from verified benchmark outputs (`results/`) and audited test execution trajectories.

---

## Directory Structure

```text
papers/
├── README.md                 # Reproducibility instructions & package map
├── HSCI_Paper.tex            # Master LaTeX publication manuscript
├── references.bib            # BibTeX bibliography
├── figures/                  # TikZ & vector architecture/workflow diagrams
│   └── architecture.tex
├── tables/                   # LaTeX empirical evaluation & ablation tables
│   └── master_results.tex
├── appendix/                 # Supplementary appendices & equations
│   └── metrics_appendix.tex
└── supplementary/            # Environment manifest & reproduction commands
    └── reproducibility.md
```

---

## Reproducibility Protocol

To independently verify and reproduce all empirical tables and figures in the manuscript:

### 1. Requirements
* Python 3.13+
* Dependencies: `pytest`, `z3-solver`, `numpy`, `pyyaml`, `torch`, `torch_geometric`

### 2. Execution Commands
```bash
# 1. Run complete unit and integration regression suite (257 passing tests)
pytest hsci/tests/ -v

# 2. Run benchmark suites across all manifests (fixed seed determinism)
python -c "from hsci.benchmarks.runner import BenchmarkRunner; [BenchmarkRunner(p, output_dir='results').run() for p in ['hsci/benchmarks/manifests/formal_logic.yaml', 'hsci/benchmarks/manifests/graph_planning.yaml', 'hsci/benchmarks/manifests/lifecycle.yaml', 'hsci/benchmarks/manifests/security.yaml']]"

# 3. Verify benchmark statistics and output consistency
pytest hsci/tests/test_benchmark_framework.py -v
```

---

## Citation

```bibtex
@inproceedings{hsci2026unified,
  title={Hyper-Symbolic Cognitive Invention: Unified Graph \& Registry Lifecycle Management with Strict SMT Verification Authority},
  author={HSCI Research Team},
  booktitle={Proceedings of the AAAI Conference on Artificial Intelligence},
  year={2026}
}
```
