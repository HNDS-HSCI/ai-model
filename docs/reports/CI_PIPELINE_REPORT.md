# HSCI V4 — CI/CD Pipeline & Release Report (CI_PIPELINE_REPORT.md)

This report explains the modernized GitHub Actions workflows and the tagged release delivery automation implemented for Milestone 1.

---

## 1. Automated Workflows Audit

### 1.1 verify.yml (Continuous Intelligence Verification)
*   **Purpose**: Validates code builds and runs regressions checks on every push or pull request targeting the `main` branch.
*   **Triggers**: `push` / `pull_request` on branch `main`.
*   **Jobs**:
    1.  **verify**: Set up python 3.11 environment, install dependencies (`requirements.txt`), execute pytest, and run `evaluation_runner.py` (which produces `evaluation_report.md`).
*   **Assets Checked**: pytest suite coverage, execution latencies.

### 1.2 release.yml (Automated Tagged Release)
*   **Purpose**: Deploys compiled release assets and generates GitHub Release logs.
*   **Triggers**: `push` on tag patterns `v*` (e.g. `v0.1.0-alpha`).
*   **Jobs**:
    1.  **release**: Executes tests, runs the evaluation framework, builds release packages, creates a GitHub Release named after the tag, and uploads files as release assets.
*   **Uploaded Assets**:
    *   [PERFORMANCE_SNAPSHOT.md](file:///C:/Work/P/ai-model/docs/reports/PERFORMANCE_SNAPSHOT.md)
    *   [evaluation_report.md](file:///C:/Work/P/ai-model/evaluation_report.md)
    *   [REPOSITORY_AUDIT.md](file:///C:/Work/P/ai-model/docs/reports/REPOSITORY_AUDIT.md)
    *   [ARCHITECTURE_OVERVIEW.md](file:///C:/Work/P/ai-model/docs/reports/ARCHITECTURE_OVERVIEW.md)
    *   [HSCI_V4_Technical_Paper.md](file:///C:/Work/P/ai-model/paper/HSCI_V4_Technical_Paper.md)
    *   [DOCUMENTATION_INDEX.md](file:///C:/Work/P/ai-model/docs/reports/DOCUMENTATION_INDEX.md)

---

## 2. Release & Versioning Strategy

HSCI transitions from push-based automatic release iterations to semantically tagged releases:
1.  **CI stage only**: Standard commits pushed to `main` trigger `verify.yml` checks. No release notes or draft versions are generated.
2.  **Tag release triggers**: Staging release versions are triggered explicitly by tagging a commit (e.g. `git tag v0.1.0-alpha && git push origin v0.1.0-alpha`). This publishes a stable GitHub Release containing the evaluation benchmarks.
