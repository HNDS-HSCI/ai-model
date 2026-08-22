# HSCI Post-VS7 Hardcoding Audit
## Repository-Wide Inspection of Concepts, Strings, Answers & Shortcuts

**Date**: August 2026  
**Auditor**: Antigravity Cognitive Architecture Team  

---

## 1. Classification Methodology

Every identified concept mention, question template, or branch condition was categorized into:
- **Category A**: Legitimate Canonical UKM Seed Data (e.g. `oop_concepts.py` canonical concepts).
- **Category B**: Legitimate Test Fixtures (e.g. unit tests checking specific expected outputs).
- **Category C**: Legitimate Generic Algorithms (e.g. generic regex patterns for frame matching).
- **Category D**: Suspicious Implementation Shortcuts (e.g. hardcoded word lists used to steer heuristics).
- **Category E**: Actual Question-Specific Hardcoding (e.g. `if text == "What is Java Interface": return ...`).

---

## 2. Audit Findings

| Location | Occurrence / Pattern | Category | Analysis & Action Required |
|---|---|:---:|---|
| `hsci/knowledge/seeds/oop_concepts.py` | `"Java Interface"`, `"Class"`, `"Abstraction"`, `"Method"`, `"Interface"` | **A** | **Legitimate Seed Data**. Represents the canonical domain knowledge seeded into the UKM database. |
| `hsci/cognition/interpretation/interpreter.py` (L90) | `known_lexical_anchors = ["interface", "class", "method", "abstraction", ...]` | **D** | **Suspicious Shortcut**. Used to distinguish demonstrative determiners (`"what is this class"`) from bare referents (`"what is this"`). Must be replaced with a generic syntactic demonstrative parser. |
| `hsci/cognition/execution/task_executor.py` | Generalization / Comparison formatting | **C** | **Legitimate Generic Algorithm**. Dynamically reads `abstract_rule` and `reasoning_result.conclusions` without question-specific hardcoding. |
| `hsci/reasoning/reasoning_engine.py` | `GeneralizationTransitivity` rule | **C** | **Legitimate Generic Algorithm**. Bounded transitive closure rule operating over arbitrary concept graph vertices. |
| `hsci/tests/test_vs*.py` | Question strings and expected assertions | **B** | **Legitimate Test Fixtures**. Expected test fixtures validating behavior. |

---

## 3. Verdict

- **Actual Question-Specific Hardcoding (Category E)**: **0 occurrences found on the production path**.
- **Suspicious Implementation Shortcuts (Category D)**: **1 occurrence found** (`known_lexical_anchors` in `interpreter.py`). Target for generic replacement in this stabilization sprint.
