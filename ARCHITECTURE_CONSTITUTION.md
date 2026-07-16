# HSCI V4 — Architecture Constitution (ARCHITECTURE_CONSTITUTION.md)

This Constitution is the foundational architectural covenant for the HSCI Cognitive Operating System. Every modification to the codebase must remain strictly compliant with its tenets.

---

## Article 1: Immutable Architectural Structure

The core system architecture consists of exactly two structural blocks: the **BrainKernel** (the orchestrator) and the **Universal Knowledge Model (UKM)** (the persistence layer).

```
   ┌────────────────────────────────────────────────────────┐
   │                       BrainKernel                      │
   │  (Orchestrates the 10-Stage Stateless execution loop)  │
   └───────────┬────────────────────────────────┬───────────┘
               │                                │
               ▼                                ▼
   ┌──────────────────────┐          ┌──────────────────────┐
   │    WorkingMemory     │          │    SolverRegistry    │
   │  (Ephemeral Request  │          │  (Dynamic Solver     │
   │      Scratchpad)     │          │     Plugins list)    │
   └──────────────────────┘          └──────────────────────┘
               │                                │
               └───────────────┬────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │               Universal Knowledge Model                │
   │          (SQLite Transactional Data Store)             │
   └────────────────────────────────────────────────────────┘
```

### Section 1.1: The 10-Stage Cognitive Pipeline
The BrainKernel executes incoming prompts through exactly 10 stages in a sequential, non-skipping pipeline:
1.  **Stage 0: LanguageBridge** (Translates raw text to tokens)
2.  **Stage 0.5: UnderstandingEngine** (Resolves context to `SemanticFrame`)
3.  **Stage 1: NeuralPerceiver** (Generates GNN embeddings and intent tags)
4.  **Stage 1.5: MentalModelEngine** (Detects gaps in `WorldStateGraph`)
5.  **Stage 2: ConceptActivationEngine** (Spreads activation on the `OntologyGraph`)
6.  **Stage 2.5: SkillMemory** (Retrieves applicable procedural skills)
7.  **Stage 3: SolverRegistry & ReasoningEngine** (HTN planning and solver selection)
8.  **Stage 4: Z3VerificationEngine** (Verifies candidate answers via CEGIS)
9.  **Stage 5: LearningEngine** (Updates weights and concepts in UKM)
10. **Stage 6: ResponseBridge** (Translates output to user format)

---

## Article 2: The Core Architectural Tenets

### Tenet 2.1: The Arbitration of Verification
No reasoning outcome or inferred relationship may enter permanent storage without formal verification. The `Z3VerificationEngine` is the final arbiter of truth. Any candidate concept or fact that cannot be validated via a mathematical proof remains transient in `WorkingMemory` or is rejected.

### Tenet 2.2: Ephemerality of Working Memory
`WorkingMemory` is request-scoped and short-lived. It is allocated at the start of a cognitive cycle and garbage-collected upon response emission. Service classes must never persist data in global variables, class-level fields, or local instance files.

### Tenet 2.3: Structural Decoupling of Solvers
The core engine is domain-agnostic. Domain-specific solver behaviors must be decoupled into independent solver plugins. These plugins register dynamically with the `SolverRegistry` and communicate using generic input/output types.

### Tenet 2.4: Traceable Provenance
Every database record in the `ConceptStore` and `EpisodeStore` must carry an immutable `proof_trace_id` referencing the exact cognitive execution trace that generated the data. The system must maintain audit visibility from any stored fact back to its proof premises.

---

## Article 3: Database & Transactional Integrity

### Section 3.1: Database Unification
All knowledge formats must exist within a single relational SQLite schema. Scattered flat files are prohibited.

### Section 3.2: Transactional Isolation
No service may read from or write to the SQLite database without acquiring the appropriate lock. Write transactions must be executed using exclusive locks, protecting database rows from concurrent access conflicts during self-play updates.

---

## Article 4: Amendment & Drift Policy

This constitution can only be amended through formal design reviews and user-approved Architecture Decision Records (ADRs). Code changes that drift from these Articles without an approved ADR must be rejected immediately during code reviews.
