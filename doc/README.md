# HSCI V4 — Documentation Index

This directory contains the complete theoretical foundation for the HSCI V4 Cognitive Operating System.
All documents are design-only. No implementation code is contained here.

---

## Document Registry

| File | Purpose | Status |
|---|---|---|
| HSCI_V4_KNOWLEDGE_ARCHITECTURE.md | Defines all 8 knowledge types, internal representations, storage, versioning, validation, lifecycle | Complete |
| HSCI_V4_LEARNING_ARCHITECTURE.md | Defines all 17 learning processes with inputs, outputs, algorithms, and state transitions | Complete |
| HSCI_V4_THINKING_ALGORITHMS.md | Defines all 14 cognitive algorithms with complexity, data structures, failure cases, benchmarks | Complete |
| HSCI_V4_ARCHITECTURE_READINESS_REPORT.md | Contradiction analysis, gap analysis, scalability risks, 7 open research questions, implementation recommendation | Complete |

---

## Companion Documents (in artifacts directory)

| File | Purpose |
|---|---|
| hsci_v3_architecture_audit.md | Phase 0 audit — 15-section analysis of the complete codebase |
| hsci_v4_architecture_spec.md | Engineering components — BrainKernel, UKM, SolverRegistry, ConceptCompiler, etc. |
| HSCI_V4_COGNITIVE_SPECIFICATION.md | Cognitive mechanisms — 7 subsystems (MME, CAE, CEE, Skill Memory, Reflection, Goals, Understanding) |

---

## Reading Order

For a new engineer joining the project:

1. Read `hsci_v3_architecture_audit.md` — understand the current state
2. Read `hsci_v4_architecture_spec.md` — understand the engineering plan
3. Read `HSCI_V4_COGNITIVE_SPECIFICATION.md` — understand the cognitive design
4. Read `HSCI_V4_KNOWLEDGE_ARCHITECTURE.md` — understand what knowledge IS in HSCI
5. Read `HSCI_V4_LEARNING_ARCHITECTURE.md` — understand how knowledge changes
6. Read `HSCI_V4_THINKING_ALGORITHMS.md` — understand how HSCI thinks
7. Read `HSCI_V4_ARCHITECTURE_READINESS_REPORT.md` — understand what to implement first

---

## Implementation Phase Reference

| Phase | Components | Pre-reads |
|---|---|---|
| Phase 1: Stabilize | ConceptCompiler, threading, dead code removal | Architecture Spec Component 6, Thinking Algorithms |
| Phase 2: Data Layer | UKM SQLite, WorkingMemory, MME bootstrap | Knowledge Architecture, Learning Architecture |
| Phase 3: Kernel | BrainKernel, SolverRegistry, CAE, TeachingProtocol, MCC | Architecture Spec (all), Cognitive Spec (CAE, Teaching) |
| Phase 4: Cognitive | Understanding Engine, Skill Memory, Reflection, Goal Manager | Cognitive Spec (all), Thinking Algorithms |
| Phase 5: Evolution | Concept Evolution Engine (dry-run first) | Knowledge Architecture (lifecycle), Learning Architecture (generalisation) |

---

## Research Questions Requiring Resolution Before Phase 5

See `HSCI_V4_ARCHITECTURE_READINESS_REPORT.md` Section 7 for full details.

RQ1: CAE spreading activation decay rate
RQ2: Optimal CEGIS iteration count
RQ3: Skill acquisition similarity threshold
RQ4: CEE generalisation detection accuracy (BLOCKS Phase 5 auto-evolution)
RQ5: Neural Perceiver cold-start training threshold
RQ6: Mental Model Engine world state accuracy over time
RQ7: Understanding Engine follow-up resolution precision
