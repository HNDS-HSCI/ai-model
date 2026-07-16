# HSCI V4 — Release Plan (RELEASE_PLAN.md)

This release plan outlines the versioning lifecycle and deployment policies for the HSCI architecture.

---

## 1. Release Milestone Map

*   **v0.1.0-alpha (Milestone 1)**: Core Cognitive Infrastructure.
    *   *Subsystems*: BrainKernel, WorkingMemory, UKM SQLite store, Concept Activation Engine, Understanding Engine, Cognitive Reasoning Engine, and Answer Generation Engine.
    *   *Deployment Status*: Staged and prepared.
*   **v0.2.0-beta (Milestone 2)**: Cognitive Evolution & Planners.
    *   *Subsystems*: Mental Model Engine, HTN Planner, Reflection Engine, and Learning Engine loops.

---

## 2. Release Automation

Release notes, pyproject.toml package versioning, and commit analyses are automated using semantic-release workflows configured in `.releaserc`.

*   **Commit Analyzer**: Scans commit intents to determine semantic upgrades.
*   **Notes Generator**: Appends updates to `CHANGELOG.md`.
