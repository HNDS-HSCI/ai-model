# HSCI V4 — Knowledge Architecture

**Document:** HSCI_V4_KNOWLEDGE_ARCHITECTURE.md
**Classification:** Cognitive Theory — No Implementation
**Basis:** Phase 0 Architecture Audit, V4 Architecture Spec, V4 Cognitive Specification
**Purpose:** Define every form of knowledge in HSCI with sufficient precision that implementation requires no ontological invention.

---

## 1. Preamble: Why a Formal Knowledge Ontology Is Required

The Phase 0 Architecture Audit revealed a critical structural weakness: HSCI's knowledge is scattered across at least six disconnected storage artefacts with no shared schema, no shared vocabulary, and no defined relationships between them. These are:

- `hsci/knowledge/concept_library.py` — Python dicts of concept definitions
- `hnsds/learner/primordial_knowledge.jsonl` — JSONL flat file of seed concepts
- `hnsds/learner/metaphysical_blueprint.json` — JSON structure of domain mappings
- `hnsds/lobes/native_graph.py` — adjacency list with no typed edges
- `episodes.jsonl` — 500KB flat-file episode store with no schema
- `synaptic_weights.json` — 88KB JSON blob of weights with no version or provenance

This fragmentation means that "knowledge" in HSCI V3 has no agreed definition. A Concept in `concept_library.py` is a different structure than a Concept implied by `metaphysical_blueprint.json`. An episode in `episodes.jsonl` has a different schema than an episode used by the V3 KnowledgeBase. No component can safely read another's storage without implicit schema knowledge encoded in the reading code.

The result is brittle coupling: changes to any one artefact require updating every component that reads it. No migration is possible without simultaneous updates to all readers. Testing is impossible without intimate knowledge of all formats.

This document defines the canonical knowledge ontology for HSCI V4. Every form of knowledge is given a precise definition, an unambiguous internal representation, a single authoritative storage location, a versioning policy, and a validation protocol. After this document, there is no ambiguity about what knowledge is, where it lives, or how it changes.

---

## 2. What Is Knowledge?

Knowledge in HSCI is defined operationally: a piece of information is knowledge if and only if it can be used by the system to produce a verified correct answer to a problem it has not seen before in the same form.

This definition excludes:
- **Data**: raw numbers or strings with no semantic context (an entity value extracted from input is data, not knowledge)
- **Information**: structured data with some context but no inferential power (a parsed PerceptionMap is information)
- **Noise**: patterns that appeared in the past but have not been verified to generalise (unverified hypothesis outputs from SelfPlay are not knowledge)

A piece of information becomes knowledge when it satisfies all three conditions:
1. It has been **verified** — either by Z3 formal proof or by empirical confirmation across multiple episodes
2. It has been **generalised** — it applies to a class of inputs, not just one specific instance
3. It has been **stored** — it is retrievable from the UniversalKnowledgeModel and can influence future reasoning

This definition is grounded in HSCI's architecture: the Z3VerificationEngine is the formal verification gate, the ConceptActivationEngine provides retrieval, and the UniversalKnowledgeModel provides storage. Knowledge that cannot pass through all three gates is not knowledge — it is a provisional belief held in WorkingMemory.

---

## 3. The Knowledge Taxonomy

HSCI recognises exactly eight categories of knowledge. These eight categories are exhaustive for the problem domains HSCI addresses. The design rationale for this specific count is provided in Section 11.

### 3.1 Concept

A Concept is the primary unit of HSCI's knowledge system. It represents a reusable, domain-applicable relationship between two or more quantities that has been formally verified to hold in at least one case and is believed to generalise.

A Concept is NOT a fact (a Concept does not assert that a specific value is true). A Concept is NOT a rule (a Concept is symmetric — it can solve for any entity in the relationship, given the others; a Rule has a directional conclusion). A Concept is NOT a procedure (a Concept is a single declarative relationship; a Procedure is an ordered sequence of operations).

Every Concept has a formal property that distinguishes it from informal pattern matches: its `abstract_rule` — a symbolic expression of the relationship (e.g., "velocity = distance / time") — must be expressible as a Z3 SMT constraint. If a candidate concept cannot be compiled to Z3, it is not a Concept; it is a Procedure or an Experience.

A Concept exists in the system from the moment it passes ConceptCompiler validation. It enters ACTIVE status when its first Z3 proof succeeds. It reaches WEAKENED status when its proof success rate falls below 0.3. It is DEPRECATED when its strength falls below 0.1 and it has not been used in 90 days. It is ARCHIVED when its domain has been superseded by a more general Concept via a verified Generalisation event.

### 3.2 Fact

A Fact is an atomic, singular, verifiable claim about the world: a specific entity has a specific attribute with a specific value. Facts live in the MentalModelEngine's WorldStateGraph as WorldStateNode attributes.

A Fact differs from a Concept: a Concept is a general relationship (velocity = distance/time). A Fact is a specific assertion (the velocity of object X in experiment Y is 20 m/s). Facts are observation-grounded; Concepts are inference-grounded.

Facts have a confidence score between 0.0 and 1.0. A confidence of 1.0 means the Fact was produced by a Z3-verified proof from known premises. A confidence of 0.8 means the Fact was asserted by a human instructor via TeachingProtocol. A confidence below 0.5 means the Fact was inferred from incomplete information or analogy and has not yet been verified.

Facts decay over time if not reinforced. The decay model is: `confidence(t) = confidence(t0) × e^(-λ × days_since_confirmation)` where λ = 0.01 (half-life ≈ 70 days). When a Fact's confidence falls below 0.2, it is flagged as a KnowledgeGap and the Mental Model Engine notifies the GoalManager.

### 3.3 Rule

A Rule is a conditional knowledge structure: if a set of preconditions holds, then a specific conclusion follows. Rules differ from Concepts in directionality. A Concept (velocity = distance/time) can derive any of its three variables given the other two. A Rule has fixed input positions and a fixed output. Rules are used in the ReasoningEngine when the Concept relationship is asymmetric or when the conclusion requires a precondition check beyond simple algebraic equality.

Rules are stored as `CompiledRule` structures: a Z3 Builder function that takes a variable dict and returns a BoolRef expressing "IF antecedent THEN consequent." The ConceptCompiler compiles human-readable rule specifications into CompiledRules using the same AST whitelist as Concept compilation.

### 3.4 Procedure

A Procedure is an ordered sequence of cognitive operations that transforms a class of inputs into outputs. Procedures are not verified in the Z3 sense — they are verified empirically: a Procedure is accepted if it produces correct outputs in ≥ 80% of test cases across a domain.

A Procedure differs from a Skill: a Procedure is a raw description of steps (typically authored by a human via TeachingProtocol). A Skill is a compiled, indexed, performance-tracked version of a Procedure that has been acquired autonomously from successful problem-solving traces. Every Skill originates from either a Procedure or a multi-step proof trace. Not every Procedure becomes a Skill — only those that are used repeatedly and prove reliable.

### 3.5 Skill

A Skill is the compiled, executable form of procedural knowledge. It is a sequence of SkillSteps (cognitive operations: ACTIVATE_CONCEPT, INVOKE_SOLVER, EMIT_SUB_GOAL, etc.) indexed by trigger conditions that make it retrievable for matching inputs.

A Skill is acquired automatically by the SkillMemory subsystem when a multi-step proof succeeds. Its performance is tracked per-domain (success_rate, application_count). A Skill that fails consistently is retired — moved to DEPRECATED status — rather than deleted, preserving its history.

The distinction between a Procedure and a Skill is operationally important: a Procedure is a specification authored externally; a Skill is a performance-tracked executable acquired internally. HSCI can have Skills with no corresponding Procedure (acquired from proof traces) and Procedures with no corresponding Skill (defined by a teacher but never triggered by a matching input).

### 3.6 Relationship

A Relationship is a typed directed edge in the OntologyGraph connecting two knowledge entities (typically two Concepts or a Concept and a domain). Relationships carry semantic meaning beyond simple adjacency.

The complete edge type taxonomy is defined in Section 7. Key properties: every Relationship has a type, a source node, a target node, a confidence score, and a creation timestamp. Relationships are the basis for spreading activation in the ConceptActivationEngine: traversal follows relationship edges, with activation decaying by 0.6 per hop.

### 3.7 Constraint

A Constraint is a Z3-compilable boundary condition on one or more entities, independent of any specific Concept. Constraints differ from Rules: a Rule asserts a relationship between entities. A Constraint asserts a limitation on entity values (e.g., "pressure must be ≥ 0", "probability must be in [0, 1]", "order quantity must be a positive integer").

Constraints are applied at the Z3 verification stage as additional assertions. The SolverRegistry's ConstraintMatrixSolver is the primary user of Constraints. They are stored in the UKM's ConceptStore under axiom_type=CONSTRAINT.

### 3.8 Experience

An Experience is an episodic memory: the complete record of one cognitive cycle, including the input, the perception, the concepts activated, the plan, the verification result, and the final answer. Experiences are the substrate for analogy, experience replay, and Skill acquisition.

Experiences are stored in the UKM's EpisodeStore. They decay in retrieval priority (not in content): older experiences receive lower similarity scores during TF-IDF retrieval. Decay parameter: experience weight = base_weight × 0.99^(days_since_creation). Experiences are never deleted — they are compressed and archived after 365 days of low retrieval.

---

## 4. What Is Understanding?

Understanding in HSCI is the transition from syntactically parsed input to semantically grounded meaning. It is distinct from parsing (which produces StructuredInput) and distinct from reasoning (which operates on already-understood meaning).

Understanding is achieved when a StructuredInput has been enriched by the UnderstandingEngine to produce a SemanticFrame — a fully grounded, disambiguated, presupposition-checked representation of what the input means in the context of the system's current world model.

The SemanticFrame is the product of understanding. It contains:
- `core_intent`: the AxiomType (REDUCTION, COMPOSITION, SYNTHESIS, TRANSFORMATION) of the intended operation
- `primary_subject`: the entity_id in the WorldStateGraph that the input is asking about
- `given_entities`: entity values fully grounded to WorldStateNodes (not just parsed strings)
- `target_entities`: what to solve for, grounded to known entity types
- `temporal_context`: whether this is a present query, hypothetical, or historical
- `is_followup`: whether this input references prior context in the session

Understanding fails when the system cannot construct a complete SemanticFrame — when entities cannot be grounded, references cannot be resolved, or presuppositions are violated. In these cases, the UnderstandingEngine generates a ClarificationRequest instead of a SemanticFrame, and the BrainKernel short-circuits the RIR loop to ask for clarification.

Understanding is what separates HSCI from a pattern-matching system. A pattern matcher processes the surface form of an input. HSCI understands the meaning of the input — what it is asking, what it presupposes, what context it references — before any reasoning begins.

---

## 5. Internal Representation

### 5.1 Concept — Data Model

Every Concept is a single record in the UKM's ConceptStore. All fields are required unless marked Optional.

| Field | Type | Semantics |
|---|---|---|
| concept_id | str | UUID, system-generated, immutable once created |
| name | str | Human-readable label (unique per domain) |
| domain | str | Broad subject area: "physics", "finance", "logic", "biology" |
| abstract_rule | str | Human-readable symbolic expression: "velocity = distance / time" |
| z3_template | str | Z3 Python expression string, AST-validated by ConceptCompiler |
| axiom_type | AxiomType | REDUCTION, COMPOSITION, SYNTHESIS, or TRANSFORMATION |
| required_entities | List[str] | Entity type names this concept requires: ["distance", "time", "velocity"] |
| unknown_entity | str | Which required entity is typically the unknown: "velocity" |
| strength | float | [0.0, 1.0] — proof success rate, updated by LearningEngine |
| proof_count | int | Total number of times this concept was verified in any cycle |
| success_count | int | Number of those verifications that succeeded |
| version | int | Incremented on every structural change to abstract_rule or z3_template |
| status | ConceptStatus | CANDIDATE, ACTIVE, WEAKENED, DEPRECATED, ARCHIVED |
| source | str | "taught" (TeachingProtocol), "acquired" (proof trace), "evolved" (CEE) |
| parent_concept_id | Optional[str] | Set if this concept was specialised or derived from another |
| child_concept_ids | List[str] | Set if this concept has been specialised |
| created_at | datetime | UTC timestamp, immutable |
| last_used | datetime | UTC timestamp of last successful retrieval by CAE |
| deprecation_reason | Optional[str] | Set when status changes to DEPRECATED |
| compiled_rule | CompiledRule | In-memory only — not persisted. Rebuilt by ConceptCompiler on load |

**JSON Canonical Form:**
```json
{
  "concept_id": "c-0042",
  "name": "uniform_velocity",
  "domain": "physics",
  "abstract_rule": "velocity = distance / time",
  "z3_template": "z3_vars['velocity'] == z3_vars['distance'] / z3_vars['time']",
  "axiom_type": "REDUCTION",
  "required_entities": ["distance", "time", "velocity"],
  "unknown_entity": "velocity",
  "strength": 0.87,
  "proof_count": 142,
  "success_count": 124,
  "version": 3,
  "status": "ACTIVE",
  "source": "taught",
  "parent_concept_id": null,
  "child_concept_ids": [],
  "created_at": "2026-01-15T08:00:00Z",
  "last_used": "2026-06-27T14:35:00Z",
  "deprecation_reason": null
}
```

**Representation choice rationale:** A flat record (not nested) is used to allow indexed queries on any field (domain, axiom_type, strength, status) without JSON path traversal. The `compiled_rule` is rebuilt in-memory from `z3_template` on every system load — Z3 objects cannot be serialised.

---

### 5.2 Fact — Data Model

| Field | Type | Semantics |
|---|---|---|
| fact_id | str | UUID |
| entity_id | str | The entity this fact is about (WorldStateNode.node_id) |
| attribute | str | Which attribute of the entity is asserted |
| value | Union[float, str, bool] | The asserted value |
| unit | Optional[str] | Physical unit if applicable: "m/s", "kg", "USD" |
| confidence | float | [0.0, 1.0] — see decay model in Section 3.2 |
| source | str | "z3_proof", "taught", "inferred", "observed" |
| proof_trace_id | Optional[str] | If source=z3_proof: the trace that established this fact |
| created_at | datetime | UTC |
| last_confirmed_at | datetime | Last time confidence was reinforced |
| session_id | Optional[str] | If scoped to a session (transient fact) |
| is_transient | bool | True = lives in WorkingMemory only, not persisted to UKM |

**Representation choice rationale:** Facts are entity-attribute-value triples (EAV model), matching the WorldStateGraph's node-attribute structure. EAV allows any entity to have any attribute without schema migration — necessary for a system that learns about new entities it has never seen.

---

### 5.3 Rule — Data Model

| Field | Type | Semantics |
|---|---|---|
| rule_id | str | UUID |
| name | str | Human-readable name |
| antecedent | str | Human-readable precondition expression |
| consequent | str | Human-readable conclusion expression |
| antecedent_z3 | str | Z3 template for precondition |
| consequent_z3 | str | Z3 template for conclusion |
| domain | str | Domain scope |
| confidence | float | Empirical success rate |
| source | str | "taught", "derived" |
| version | int | |
| status | str | ACTIVE, DEPRECATED |
| created_at | datetime | |

**Representation choice rationale:** Rules are stored separately from Concepts because their asymmetric structure (antecedent → consequent) requires different Z3 encoding (implication, not equality). Mixing them with Concepts would force ConceptCompiler to handle two structurally different Z3 patterns.

---

### 5.4 Procedure — Data Model

| Field | Type | Semantics |
|---|---|---|
| procedure_id | str | UUID |
| name | str | |
| description | str | Human-readable purpose |
| domain | str | |
| steps | List[ProcedureStep] | Ordered, human-readable operation descriptions |
| preconditions | List[str] | Must hold before procedure can be applied |
| postconditions | List[str] | Must hold after procedure completes |
| source | str | Always "taught" (Procedures come from TeachingProtocol) |
| empirical_success_rate | float | Measured over test_cases |
| test_cases | List[Dict] | Input/output pairs for validation |
| version | int | |
| status | str | ACTIVE, DEPRECATED |
| created_at | datetime | |

**ProcedureStep fields:** step_index (int), description (str), operation (str, human-readable), inputs (List[str]), outputs (List[str]).

---

### 5.5 Skill — Data Model

(Full specification in V4 Cognitive Specification, Subsystem 4. Summary here for completeness.)

| Field | Type | Semantics |
|---|---|---|
| skill_id | str | UUID |
| name | str | Auto-generated: "{domain}_{axiom_type}_skill_{index}" |
| domain | str | |
| applicable_axiom_types | List[AxiomType] | |
| required_entity_types | List[str] | |
| procedure | List[SkillStep] | Compiled steps (not human-readable descriptions) |
| success_rate | float | Across all applications |
| domain_success_rates | Dict[str, float] | Per-domain |
| application_count | int | |
| source | str | "acquired", "taught", "composed" |
| acquired_from_episode | Optional[str] | Episode ID if source=acquired |
| version | int | |
| status | str | ACTIVE, DEPRECATED |
| created_at | datetime | |
| last_applied | datetime | |

---

### 5.6 Relationship — Data Model

| Field | Type | Semantics |
|---|---|---|
| edge_id | str | UUID |
| edge_type | EdgeType | See taxonomy in Section 7 |
| source_id | str | Source node (concept_id, domain string, or entity type string) |
| target_id | str | Target node |
| confidence | float | [0.0, 1.0] |
| source | str | "taught", "inferred", "evolved" |
| created_at | datetime | |
| last_confirmed_at | datetime | |
| is_inferred | bool | True if derived by transitivity, False if directly asserted |

---

### 5.7 Constraint — Data Model

| Field | Type | Semantics |
|---|---|---|
| constraint_id | str | UUID |
| name | str | |
| entity_type | str | Which entity type this constrains |
| constraint_expr | str | Human-readable: "pressure >= 0" |
| z3_template | str | Z3 expression |
| domain | Optional[str] | Null = universal constraint |
| is_hard | bool | True = violation causes UNSAT. False = violation causes warning |
| source | str | "taught", "inferred" |
| version | int | |
| created_at | datetime | |

---

### 5.8 Experience — Data Model

| Field | Type | Semantics |
|---|---|---|
| episode_id | str | UUID |
| session_id | str | Which session produced this experience |
| raw_input | str | Original input text |
| perception | Dict | Serialised PerceptionMap fields |
| intent | str | AxiomType name |
| domain | str | |
| entities | Dict[str, float] | Entity name → value (known entities) |
| unknown_entity | str | What was solved for |
| solution_value | Optional[float] | The verified answer (null if verification failed) |
| concepts_used | List[str] | concept_ids that contributed to the solution |
| was_verified | bool | Whether Z3 proof succeeded |
| cegis_iterations | int | How many CEGIS iterations were needed |
| was_analogical | bool | True if solved via analogy |
| skill_applied | Optional[str] | skill_id if a Skill was applied |
| reflection_report_id | Optional[str] | report_id from ReflectionEngine |
| tfidf_index | Optional[str] | In-memory only — rebuilt on load |
| created_at | datetime | UTC |

**Representation choice rationale:** Experiences are stored as semi-structured JSON (not rigid schema) because the perception field varies by domain and input type. The entities and concepts_used fields are indexed for retrieval. TF-IDF index is rebuilt in-memory on startup from raw_input fields — it cannot be persisted portably.

---

## 6. Storage Architecture

### 6.1 UniversalKnowledgeModel Store Mapping

| Knowledge Type | UKM Store | Table / Collection | Primary Index |
|---|---|---|---|
| Concept | ConceptStore | concepts | (domain, axiom_type, status) |
| Fact | MemoryStore (MME) | world_state_facts | (entity_id, attribute) |
| Rule | ConceptStore | rules | (domain, status) |
| Procedure | ConceptStore | procedures | (domain, status) |
| Skill | ConceptStore | skills | (domain, axiom_type, status) |
| Relationship | OntologyStore | ontology_edges | (source_id, edge_type) |
| Constraint | ConceptStore | constraints | (entity_type, domain) |
| Experience | EpisodeStore | episodes | (domain, intent, created_at) |

### 6.2 SQLite Schema

**concepts table:**
```sql
CREATE TABLE concepts (
  concept_id   TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  domain       TEXT NOT NULL,
  abstract_rule TEXT NOT NULL,
  z3_template  TEXT NOT NULL,
  axiom_type   TEXT NOT NULL,
  required_entities TEXT NOT NULL,  -- JSON array
  unknown_entity TEXT NOT NULL,
  strength     REAL DEFAULT 0.5,
  proof_count  INTEGER DEFAULT 0,
  success_count INTEGER DEFAULT 0,
  version      INTEGER DEFAULT 1,
  status       TEXT DEFAULT 'CANDIDATE',
  source       TEXT NOT NULL,
  parent_concept_id TEXT,
  child_concept_ids TEXT DEFAULT '[]',  -- JSON array
  created_at   TEXT NOT NULL,
  last_used    TEXT,
  deprecation_reason TEXT
);
CREATE INDEX idx_concepts_domain_type ON concepts(domain, axiom_type);
CREATE INDEX idx_concepts_status ON concepts(status);
CREATE INDEX idx_concepts_strength ON concepts(strength);
```

**episodes table:**
```sql
CREATE TABLE episodes (
  episode_id   TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL,
  raw_input    TEXT NOT NULL,
  domain       TEXT NOT NULL,
  intent       TEXT NOT NULL,
  entities     TEXT NOT NULL,   -- JSON object
  unknown_entity TEXT,
  solution_value REAL,
  concepts_used TEXT NOT NULL,  -- JSON array
  was_verified INTEGER NOT NULL, -- 0 or 1
  cegis_iterations INTEGER DEFAULT 1,
  was_analogical INTEGER DEFAULT 0,
  skill_applied TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX idx_episodes_domain ON episodes(domain);
CREATE INDEX idx_episodes_created ON episodes(created_at);
```

### 6.3 Concurrency Model

All UKM write operations are protected by a single readers-writer lock (`threading.RLock` in V4, upgradeable to `asyncio.Lock` if async is adopted):
- Multiple concurrent reads: permitted
- Any write: exclusive — blocks all other reads and writes
- Write operations batched in a 500ms write buffer to reduce lock contention
- Within the write buffer: coalesced updates (multiple strength updates for same concept_id = last wins)

---

## 7. Connectivity — Edge Type Taxonomy

### 7.1 Complete Edge Type Registry

| EdgeType | Direction | Semantics | Example |
|---|---|---|---|
| IS_A | concept → concept | Subtype relationship | "kinetic_energy IS_A energy" |
| IMPLEMENTS | concept → procedure | Concept implements a procedure | "ohms_law IMPLEMENTS electrical_analysis_procedure" |
| REQUIRES | concept → concept | Cannot be applied without the other | "compound_interest REQUIRES simple_interest" |
| SYNONYM_OF | concept ↔ concept | Equivalent formulations (bidirectional) | "velocity SYNONYM_OF speed_with_direction" |
| GENERALIZES | abstract → specific | More general concept generalises a specific one | "uniform_motion GENERALIZES uniform_velocity" |
| CONTRADICTS | concept ↔ concept | Cannot both be true simultaneously | "newtonian_gravity CONTRADICTS general_relativity_weak_field_limit" |
| DERIVED_FROM | concept → concept | Created by analogy or evolution from another | "electrical_current_law DERIVED_FROM fluid_flow_law" |
| EMPIRICALLY_OBSERVED | concept → domain | Concept has been verified in a domain | "pythagorean_theorem EMPIRICALLY_OBSERVED geometry" |
| SPECIALIZES | specific → abstract | Inverse of GENERALIZES | "uniform_velocity SPECIALIZES uniform_motion" |
| DOMAIN_MEMBER | concept → domain | Concept belongs to a domain | "velocity DOMAIN_MEMBER physics" |

### 7.2 Inference Rules from Edges

- **IS_A transitivity:** If A IS_A B and B IS_A C, then A IS_A C (derived edge, is_inferred=True)
- **GENERALIZES reachability:** If X GENERALIZES Y and Y GENERALIZES Z, then X is reachable from Z via spreading activation in 2 hops
- **CONTRADICTS symmetry:** If A CONTRADICTS B, then B CONTRADICTS A (automatically asserted)
- **DERIVED_FROM strength inheritance:** A DERIVED_FROM B → A.strength_floor = B.strength × 0.5 (derived concepts start with at least half the source concept's strength)

### 7.3 Forbidden Edges

| Forbidden | Reason |
|---|---|
| IS_A cycles (A IS_A B IS_A A) | Creates infinite traversal loops in activation |
| Fact → Concept edges of any type | Facts are world assertions; concepts are structural relationships — mixing them collapses the ontological boundary |
| Experience → Concept IS_A | Experiences cannot be subtypes of Concepts |
| Constraint → Concept REQUIRES | Constraints qualify entity values, not concept relationships |

All edges are validated by OntologyStore before insertion. Cycle detection uses a visited-set DFS over existing edges before accepting a new IS_A edge.

### 7.4 Graph Traversal Rules

ConceptActivationEngine traversal (spreading activation):
1. Start from all seed concept_ids produced by direct name/intent matching
2. Traverse OUTGOING edges of types: IS_A, GENERALIZES, DERIVED_FROM, SYNONYM_OF
3. For each traversed edge, apply decay: `activation_score = parent_score × 0.6`
4. Stop at depth=2 (maximum 2 hops from seed)
5. Do not traverse CONTRADICTS edges (they are used for conflict detection, not activation)
6. Do not traverse EMPIRICALLY_OBSERVED edges (domain-level, not concept-level)
7. Minimum activation threshold: 0.1 (below this, concept not included in ActivationField)

---

## 8. Versioning

### 8.1 Concept Versioning

**Version-breaking changes** (increment version, retain prior version as archived record):
- Change to `abstract_rule` (structural formula change)
- Change to `z3_template` (affects all future proofs)
- Change to `required_entities` (changes what inputs the concept accepts)
- Change to `axiom_type` (re-classifies the concept entirely)

**Non-breaking changes** (update in place, no version increment):
- Change to `strength`, `proof_count`, `success_count` (numeric metadata — learning updates)
- Change to `last_used` (access timestamp)
- Change to `status` from ACTIVE → WEAKENED → DEPRECATED (lifecycle, not structure)

**Version history retention:** Every version of a Concept is retained in a `concepts_history` table:
```sql
CREATE TABLE concepts_history (
  history_id   TEXT PRIMARY KEY,
  concept_id   TEXT NOT NULL,
  version      INTEGER NOT NULL,
  snapshot     TEXT NOT NULL,  -- JSON of full concept record at this version
  changed_at   TEXT NOT NULL,
  changed_by   TEXT NOT NULL   -- "CEE", "TeachingProtocol", "manual"
);
```

**Rollback mechanics:** If a version-breaking change produces worse proof outcomes (success_rate drops by > 0.2 within 100 subsequent cycles), the MCC can trigger a rollback: `UKM.rollback_concept(concept_id, version=N-1)` which restores the concept record from `concepts_history` at the specified version.

### 8.2 Skill Versioning

Same policy as Concepts. Version-breaking changes: any change to procedure (SkillStep sequence). Non-breaking: strength, success_rate, application_count updates.

### 8.3 Fact Versioning

Facts are not versioned — they are updated in place when confidence changes. If a Fact's value must change (e.g., the velocity of object X is now known to be 25 m/s, not 20 m/s), the prior value is overwritten and the change logged in `world_state_history`:
```sql
CREATE TABLE world_state_history (
  history_id   TEXT PRIMARY KEY,
  entity_id    TEXT NOT NULL,
  attribute    TEXT NOT NULL,
  prior_value  TEXT,
  new_value    TEXT,
  changed_at   TEXT NOT NULL,
  reason       TEXT
);
```

### 8.4 Experience Versioning

Experiences are immutable — they are records of what happened and cannot be revised. If a re-analysis of a past experience produces a different interpretation, a new Experience record is created with `references_episode_id` pointing to the original.

---

## 9. Validation

### 9.1 Syntactic Validation

Performed by ConceptCompiler for all knowledge types before storage. Rules:
- All required fields are present and non-null
- `concept_id` matches UUID format
- `strength` is in [0.0, 1.0]
- `axiom_type` is a valid AxiomType enum value
- `required_entities` is a non-empty list
- `z3_template` is a non-empty string that parses as Python source (ast.parse() check)
- `domain` is non-empty and contains no special characters

**Syntactic validation failures** cause the operation to be rejected immediately. No partial writes. The caller receives a ValidationError with the specific field and reason.

### 9.2 Semantic Validation

Performed by ConceptCompiler + Z3VerificationEngine for Concepts and Rules.

**For Concepts:**
1. ConceptCompiler parses `z3_template` using ast.parse() and validates each node against the whitelist (PERMITTED: Assign, BinOp, Compare, Name, Num, Call to z3.Real/z3.Int/z3.Bool)
2. ConceptCompiler attempts to call the compiled z3_builder with a test dict of z3.Real variables — must not raise
3. Z3VerificationEngine runs the compiled rule against one synthetic example with known-good values — must return SAT with correct model value

**For Rules:**
1. Same AST whitelist check on both antecedent_z3 and consequent_z3
2. Z3 implication check: `solver.add(z3.Implies(antecedent_expr, consequent_expr))` must return SAT

**Semantic validation failures:** Concept is stored as CANDIDATE (not ACTIVE). A CorrectionProposal is generated for the TeachingProtocol to request a corrected definition.

### 9.3 Empirical Validation

Applied to Procedures and Skills using their `test_cases`.

**For Procedures:** Each test_case is run through the ProcedureExecutor (a controlled execution environment for SkillStep sequences). If empirical_success_rate across all test_cases < 0.8, the Procedure is stored with status=CANDIDATE and flagged for human review.

**For Skills (auto-acquired):** A Skill is immediately given ACTIVE status if it was acquired from a verified proof (the proof itself is the empirical validation). For Skill compositions, the composed Skill must be tested against 5 synthetic examples before activation.

### 9.4 Validation Ownership

| Validation Type | Owner Component | Applied To |
|---|---|---|
| Syntactic | ConceptCompiler | All knowledge types |
| Semantic (AST) | ConceptCompiler | Concepts, Rules, Constraints |
| Semantic (Z3) | Z3VerificationEngine | Concepts, Rules |
| Empirical (test cases) | SkillMemory / ProcedureExecutor | Procedures, Skill compositions |
| Conflict detection | OntologyStore | Relationships (CONTRADICTS check) |
| Confidence decay | MentalModelEngine | Facts |

---

## 10. Knowledge Lifecycle State Machines

### 10.1 Concept Lifecycle

```
States: CANDIDATE → ACTIVE → WEAKENED → DEPRECATED → ARCHIVED

Transitions:

  CANDIDATE → ACTIVE
    Trigger: Z3 semantic validation passes AND first proof succeeds
    Action: strength = 0.5 (initial), status = ACTIVE

  ACTIVE → WEAKENED
    Trigger: strength < 0.3 (updated by LearningEngine after failed proof)
    Action: MCC logs; GoalManager creates IMPROVE_DOMAIN goal for this concept's domain

  WEAKENED → ACTIVE
    Trigger: strength recovers to >= 0.4 (after successful proofs reinforce the concept)
    Action: status = ACTIVE; cancel associated IMPROVE_DOMAIN goal if present

  ACTIVE/WEAKENED → DEPRECATED
    Trigger: (strength < 0.1 AND days_since_last_used > 90) OR (explicit deprecation by CEE/admin)
    Action: status = DEPRECATED; deprecation_reason recorded

  DEPRECATED → ARCHIVED
    Trigger: days_since_deprecated > 365 AND no rollback has been requested
    Action: Record moved to concepts_archive table; removed from active ConceptStore

  ARCHIVED: Terminal state — cannot transition to any other state without explicit restoration

  Any → CANDIDATE (rollback)
    Trigger: MCC.rollback_concept() called
    Action: Restore from concepts_history at specified version; status = CANDIDATE; re-validate
```

### 10.2 Skill Lifecycle

```
States: CANDIDATE → ACTIVE → DEPRECATED → ARCHIVED

Transitions:

  CANDIDATE → ACTIVE
    Trigger: Source = "acquired" (from verified proof trace) → immediate ACTIVE
             Source = "composed" → requires 5 test-case empirical validation pass
             Source = "taught" → requires at least 1 successful application

  ACTIVE → DEPRECATED
    Trigger: success_rate < 0.2 AND application_count > 20 (MCC scheduled scan)
             OR explicit retirement via SkillMemory.retire()
    Action: status = DEPRECATED; added to retired_skills log

  DEPRECATED → ARCHIVED
    Trigger: days_since_deprecated > 90
    Action: Moved to skills_archive; removed from active retrieval index

  ARCHIVED: Terminal state
```

---

## 11. Design Rationale — Why These Eight Types

The taxonomy of eight knowledge types is not arbitrary. Each type was chosen because it is irreducible to any other type in terms of structure, storage requirements, retrieval mechanics, or validation protocol.

**Why Concept and Fact are separate:** A Concept is a general relationship; a Fact is a specific assertion. Merging them would require every Concept to carry a confidence score (violating the principle that verified Concepts are structurally reliable) or every Fact to carry a z3_template (inappropriate for singular observational claims).

**Why Rule and Concept are separate:** A Concept is symmetric (solve for any variable). A Rule is asymmetric (direction: antecedent → consequent). The Z3 encodings differ: Concepts use equality constraints; Rules use Z3.Implies. Treating Rules as directional Concepts would require every Concept to carry a directionality field and conditional logic in the ConceptCompiler, vastly complicating the most critical path.

**Why Procedure and Skill are separate:** A Procedure is a specification authored externally. A Skill is a compiled, indexed, performance-tracked executable. Merging them would lose the distinction between "what was defined" and "what was learned to work." A system without this distinction cannot track which procedures were useful and which were not.

**Why Relationship is a first-class type:** In HSCI V3, relationships were implicit in the adjacency list of `native_graph.py` with no types and no confidence scores. Making Relationship a first-class type enables typed traversal (IS_A vs. GENERALIZES vs. CONTRADICTS), confidence-weighted spreading activation, inference of derived edges, and rollback of incorrect edges — none of which is possible with an untyped adjacency list.

**Why Constraint is separate from Rule:** A Constraint is a boundary condition on entity values, not an inferential structure. A Rule produces new knowledge from existing knowledge. A Constraint prevents invalid reasoning. In Z3 terms: Rules are Z3.Implies; Constraints are Z3.And conditions added unconditionally to the solver. Mixing them forces the solver to distinguish between "this is a hard boundary" and "this is an inferential step" — a distinction that must be made before the solver is invoked, not inside it.

**Why Experience is separate from Fact:** An Experience is a complete episodic record — it captures the process of arriving at a fact, not just the fact itself. The experience record enables analogy (by structural similarity of problems), Skill acquisition (by extraction of proof traces), and experience replay (by re-running verified episodes on modified concept versions). A Fact record cannot support any of these because it contains only the claim, not the reasoning history.

**Why Understanding is not a knowledge type:** Understanding is a process (the act of constructing a SemanticFrame from a StructuredInput), not a stored artefact. The output of understanding — the SemanticFrame — is held in WorkingMemory for the duration of one cognitive cycle. It is not persisted because it is session-specific, context-dependent, and derives its meaning from the UKM rather than contributing to it. Making Understanding a knowledge type would imply storing SemanticFrames permanently — which would be a 1:1 mapping to Episodes. The Experience type already captures this: the `perception` field of an Experience record contains the semantic interpretation of the original input.
