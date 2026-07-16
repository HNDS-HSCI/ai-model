# HSCI V4 — UKM Knowledge Representation Design (UKM_Knowledge_Representation_Design.md)

This document establishes the storage-independent cognitive knowledge representation model for the Universal Knowledge Model (UKM) of the HSCI V4 Cognitive Operating System.

---

## 1. Purpose & Core Principles

The Universal Knowledge Model (UKM) represents the permanent memory, logical reasoning core, and cognitive associations of the HSCI system. The primary goal of this design is **Storage Independence**. The Knowledge Layer must exist as a set of logical structures and abstract interfaces, completely decoupled from concrete storage engines (such as SQLite, PostgreSQL, Neo4j, Redis, or local flat files). 

### Core Principles
1.  **Axiomatic Validity**: No knowledge object is registered as "verified" without a mathematical proof trace mapped to Z3 verification outcomes.
2.  **Referential Provenance**: Every stored fact or concept must maintain an immutable link to the exact cognitive episode and verification trace that established it.
3.  **Dynamic Evolution**: Concepts are not static; they evolve through splits (specialisation) and mergers (generalisation) driven by reflection.
4.  **Epistemic Decoupling**: Storage implementations (relational, graph, or vector databases) are treated as pluggable providers.

---

## 2. Core Cognitive Objects

Every knowledge object is modeled with its purpose, schema fields, lifecycle states, relationships, ownership, mutability, persistence, validation rules, and confidence metrics.

```
                  ┌─────────────────────────────────┐
                  │          KnowledgeObject        │
                  │   (Base metadata + provenance)  │
                  └────────────────┬────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
  │   Concept   │           │    Fact     │           │   Episode   │
  │ (Axiomatic) │           │ (Temporal)  │           │ (Historical)│
  └─────────────┘           └─────────────┘           └─────────────┘
```

### 2.1 Concept
*   **Purpose**: Represents an abstract mathematical rule, mathematical definition, or reasoning pattern.
*   **Fields**: `concept_id: str`, `name: str`, `namespace: str`, `axiom_type: AxiomType`, `abstract_rule: str`, `z3_template: str`, `strength: float`, `proof_count: int`, `status: ConceptStatus`.
*   **Lifecycle**: `CANDIDATE` $\rightarrow$ `ACTIVE` $\rightarrow$ `WEAKENED` $\rightarrow$ `DEPRECATED` $\rightarrow$ `ARCHIVED`.
*   **Ownership**: Owned globally or linked to the creator session.
*   **Mutability**: Immutable except for strength metadata and status transitions. Rule changes spawn a new concept version.
*   **Validation Rules**: Rules must compile to valid AST nodes. Z3 templates must parse cleanly.

### 2.2 Fact
*   **Purpose**: An Entity-Attribute-Value (EAV) representation of a state in the world model.
*   **Fields**: `fact_id: str`, `entity: str`, `attribute: str`, `value: Any`, `confidence: float`, `timestamp: float`.
*   **Lifecycle**: `OBSERVED` $\rightarrow$ `BELIEVED` $\rightarrow$ `DECAYED` $\rightarrow$ `PRUNED`.
*   **Mutability**: Mutable confidence; values are updated by appending new versions.
*   **Confidence Model**: Decays over time via `e^(-0.01 * t)`.

### 2.3 Rule
*   **Purpose**: Represents an implication constraint ($A \implies B$) used by solvers and planners.
*   **Fields**: `rule_id: str`, `premise: Expression`, `conclusion: Expression`, `z3_constraint: str`.
*   **Mutability**: Immutable.

### 2.4 Procedure & Skill
*   **Purpose**: `Procedure` maps sequential actions. `Skill` maps the procedural blueprint triggered by a specific neural embedding.
*   **Fields**: `skill_id: str`, `trigger_embedding: List[float]`, `ordered_tasks: List[Task]`, `success_rate: float`.
*   **Mutability**: Success rate is mutable; task sequences require version increments.

### 2.5 Hypothesis
*   **Purpose**: A candidate rule proposed during self-play or reflection before validation.
*   **Fields**: `hypothesis_id: str`, `proposed_rule: str`, `concept_sources: List[str]`, `verification_status: VerificationStatus`.
*   **Lifecycle**: `PROPOSED` $\rightarrow$ `VERIFIED` (becomes active Concept) or `REFUTED` (becomes archived).

### 2.6 Episode & Proof
*   **Purpose**: `Episode` stores a problem solving instance. `Proof` stores the Z3 validation trace.
*   **Fields**: `episode_id: str`, `stimulus: str`, `proof_trace: ProofTrace`, `was_verified: bool`, `pnl_outcomes: float`.
*   **Mutability**: Read-only (strictly immutable).

### 2.7 Additional Objects
*   **Goal**: The target state description.
*   **Counterexample**: A dictionary of assignments falsifying a hypothesis.
*   **Observation**: A raw sensor or parsing output.
*   **Task / Action**: Planner execution elements.
*   **Reflection**: Logs diagnosed failures and CEE evolution proposals.
*   **Learning Event**: Tracks PYG weight modifications.

---

## 3. Knowledge Relationships

Cognitive objects are linked in the `OntologyGraph` via the following relationship types:

| Relationship Type | Source Object | Target Object | Semantic Meaning |
|---|---|---|---|
| `IS_A` | Concept | Concept | Inheritance / Taxonomic subclassing. |
| `PART_OF` | Task | Procedure | Decomposition structure. |
| `CAUSES` | Fact / Rule | Fact | Causal implication logic. |
| `USES` | SubGoal | Skill | Procedural assignment. |
| `DEPENDS_ON` | Concept | Concept | Prerequisite requirement. |
| `CONFLICTS_WITH` | Concept | Concept | Logical contradiction (Z3 proven). |
| `SUPERSEDES` | Concept (v2) | Concept (v1) | Version deprecation mapping. |
| `PROVES` | Proof | Hypothesis | Formal verification confirmation. |
| `REFUTES` | Counterexample| Hypothesis | Falsification link. |
| `LEARNED_FROM` | Concept | Episode | Provenance mapping. |
| `GENERALIZES` | Concept | Concept | Conceptual merger target. |
| `SPECIALIZES` | Concept | Concept | Conceptual split target. |

---

## 4. Concept Identity & Evolution

*   **Identifiers & Namespaces**: Every concept belongs to a hierarchical namespace (e.g., `hsci.math.arithmetic.addition`) and has a UUID4 key.
*   **Synonyms & Aliases**: Concepts map to lists of text aliases to support semantic matches.
*   **Concept Merger (Generalisation)**: When two concepts are structurally identical and behave symmetrically across all verified episodes, they are merged. A new concept is created (`vMajor+1`), and the original concepts transition to `DEPRECATED` status with a `SUPERSEDES` relation.
*   **Concept Split (Specialisation)**: When a general concept fails verification on a subclass of inputs, the Concept Evolution Engine splits it into two targeted sub-concepts linked by a `SPECIALIZES` relationship.

---

## 5. Confidence & Uncertainty Model

*   **Concept Strength**: A float value ($[0.0, 1.0]$) representing the reliability of the concept.
    *   *Strengthening (Success)*: $S_{t+1} = S_t + \eta \cdot (1 - S_t)$
    *   *Weakening (Failure)*: $S_{t+1} = S_t - \eta \cdot S_t$ (where $\eta$ is the learning rate, default 0.01).
*   **Temporal Fact Decay**: Fact confidence decays lazily:
    $$\text{Confidence}(t) = \text{Confidence}_0 \cdot e^{-0.01 \cdot \Delta t}$$
*   **Source Reliability**: Knowledge ingested via direct human teaching (`TeachingProtocol`) initializes with a baseline confidence of $1.0$. Knowledge generated via self-play guesses initializes at $0.4$.

---

## 6. Abstract Interfaces (APIs)

```python
class IConceptStore(ABC):
    @abstractmethod
    def create_concept(self, concept: Concept) -> str:
        """Saves a new concept and returns its unique ID."""
        pass

    @abstractmethod
    def get_concept(self, concept_id: str) -> Optional[Concept]:
        pass

    @abstractmethod
    def update_strength(self, concept_id: str, success: bool) -> None:
        """Applies Hebbian updates to strength and proof counts."""
        pass

    @abstractmethod
    def deprecate_concept(self, concept_id: str, superseded_by: str) -> None:
        """Sets status=DEPRECATED and registers the replacement link."""
        pass


class IOntologyStore(ABC):
    @abstractmethod
    def add_relationship(self, source_id: str, target_id: str, rel_type: str) -> None:
        pass

    @abstractmethod
    def remove_relationship(self, source_id: str, target_id: str, rel_type: str) -> None:
        pass

    @abstractmethod
    def get_related_objects(self, object_id: str, rel_type: Optional[str] = None) -> List[Tuple[str, str]]:
        """Returns related object IDs and relationship types."""
        pass


class IEpisodeStore(ABC):
    @abstractmethod
    def store_episode(self, episode: Episode) -> str:
        pass

    @abstractmethod
    def find_similar_episodes(self, query_embedding: List[float], limit: int = 5) -> List[Episode]:
        """Analogical experience search."""
        pass
```

---

## 7. Scalability & Extensibility

*   **Federated Providers**: The abstract APIs allow developers to implement local SQLite stores for desktop execution, while wrapping them behind PostgreSQL or Neo4j server nodes for distributed enterprise deployments.
*   **Vector Search Adaptability**: The `find_similar_episodes` interface accepts standard float vectors. This supports simple TF-IDF indexing in the initial phases, while accommodating pluggable HNSW vector indexes as the database expands.
*   **Domain Partitioning**: The ontology traversals are partitioned by domain namespaces, preventing computational complexity degradation in large graphs.
