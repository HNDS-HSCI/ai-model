# ARTIFACT EVALUATION CHECKLIST

| Criteria | Status | Verification Mechanism |
| :--- | :---: | :--- |
| **Artifact Identifiers** | PASSED | `papers/` contains complete LaTeX, dataset, and code assets |
| **Installation Test** | PASSED | `pip install -r requirements.txt` succeeds cleanly |
| **Functional Tests** | PASSED | `pytest hsci/tests/` passes 257 unit & integration tests |
| **Benchmark Reproducibility** | PASSED | `python -m hsci.benchmarks.runner` reproduces `results/` |
| **LaTeX Table Consistency** | PASSED | `scratch/test_hsci_pub_2_consistency.py` verifies 100% exact alignment |
| **BibTeX Validity** | PASSED | All 5 references verified against Google Scholar & DBLP |
| **License Compliance** | PASSED | MIT License provided in `papers/LICENSE.md` |
