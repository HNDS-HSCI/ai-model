# HSCI V4 Learning Architecture
## Theoretical Foundation for the Cognitive Operating System Learning Subsystem

**Document Version**: 1.0.0
**Status**: Final Pre-Engineering Design
**Scope**: Pure design specification — no implementation code
**Companion Documents**:
- `hsci_v3_architecture_audit.md` — v3 defects and debt
- `hsci_v4_architecture_spec.md` — structural blueprint
- `HSCI_V4_COGNITIVE_SPECIFICATION.md` — cognitive subsystem specifications

---

## 1. Preamble — What Learning Means in a Cognitive OS

In HSCI V4, the word **learning** has a precise, constrained definition that explicitly excludes several phenomena commonly called learning in machine learning literature. This section defines the boundaries.

### 1.1 What Learning Is NOT in HSCI V4

**Training** (weight adjustment) is the process by which the NeuralPerceiver's GNN weights are updated via gradient descent on a loss signal. Training modifies *how the system perceives*. It does not modify *what the system knows*. Training occurs in isolation — it never touches the UniversalKnowledgeModel (UKM), the OntologyGraph, the EpisodeMemory, or the SkillMemory. Training is a maintenance operation, not a cognitive one.

**Inference** is the moment-to-moment application of existing knowledge to a new stimulus. Inference consumes knowledge; it does not produce it. A system that only infers never learns.

**Memorisation** is the direct verbatim storage of an input. HSCI V4 does not memorise. Every knowledge change is the result of a verified cognitive operation. Raw inputs are never stored as facts.

### 1.2 The Three Faces of Learning

HSCI V4 recognises exactly three knowledge-change categories:

**Acquisition**: A concept, relationship, skill, or episode that did not exist in the UKM before now exists. The system has grown. Acquisition is always the output of a successful verification cycle — either a Z3 proof, a human teaching verification, or a SelfPlay proof. Acquisition is the primary output of Processes 4, 5, 6, and 12.

**Evolution**: An existing concept, relationship, or skill changes its content, strength, domain, or structural position in the OntologyGraph. The system has refined itself. Evolution includes both strengthening and weakening operations, generalisation, specialisation, and error correction. Evolution is the primary output of Processes 7, 8, 9, 10, 11, and 15.

**Forgetting**: A concept, relationship, or skill that is no longer useful is deprecated — marked inactive but not deleted. Deprecated knowledge is retained for audit, rollback, and potential reactivation. True deletion never occurs. Forgetting is governed exclusively by Process 9.

### 1.3 The Learning Contract

Every learning process in this document must satisfy the following contract:

1. **Verified-Only Permanence**: No knowledge enters permanent memory without passing through Z3VerificationEngine or TeachingProtocol verification. Provisional knowledge lives only in WorkingMemory.
2. **Traceable Provenance**: Every UKM record carries a proof_trace_id referencing the exact CognitiveTrace that produced it.
3. **Reversibility**: Every learning operation has a corresponding inverse operation. The system can roll back any change if contradiction is later detected.
4. **Atomicity**: A learning operation either completes fully and writes to UKM, or it aborts and leaves UKM unchanged. No partial writes.
5. **Isolation**: No learning process reads from the UKM while another learning process is writing to it for the same concept_id. Concurrent learning for distinct concepts is permitted.

---

---

## 2. The 17 Learning Processes

Each process below is defined with six mandatory sections: INPUTS, OUTPUTS, ALGORITHM, STATE TRANSITIONS, FAILURE MODES, and TESTING STRATEGY.

---

### Process 2a — Learning Lifecycle (Overall Loop)

**Purpose**: The master loop that governs how every interaction between a stimulus and the system produces permanent knowledge change.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| raw_input | str | BrainKernel.process() entry point |
| cognitive_trace | CognitiveTrace | Produced during cycle execution |
| working_memory | WorkingMemory | CognitiveContext per-request |
| verification_result | VerificationResult | Z3VerificationEngine output |

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| learning_result | LearningResult | Stored in CognitiveContext, read by LearningEngine |
| ukm_delta | List[UKMWriteRecord] | Committed to UKM if and only if verification_result.verified == True |
| episode_record | EpisodeRecord | EpisodeMemory after every complete cycle regardless of verification outcome |
| learning_event | LearningEvent | Emitted to MetaCognitiveController for rate-limiting and monitoring |

#### ALGORITHM
```
Step 1. BrainKernel receives raw_input. Allocates a fresh CognitiveContext (ctx) with:
        ctx.request_id = UUID4()
        ctx.working_memory = WorkingMemory(max_slots=512)
        ctx.started_at = utcnow()

Step 2. Layers 0–4 execute synchronously (LanguageBridge → UnderstandingEngine →
        NeuralPerceiver → MentalModelEngine → ConceptActivationEngine →
        SkillMemory.retrieve → SolverRegistry/ReasoningEngine → Z3VerificationEngine).
        All intermediate outputs are written into ctx.working_memory, never to UKM.

Step 3. Z3VerificationEngine returns VerificationResult.
        If VerificationResult.verified == True:
            Proceed to Step 4 (acquisition path).
        If VerificationResult.verified == False and counterexample exists:
            Proceed to Step 5 (weakening path).
        If VerificationResult.verified == False and timeout:
            Proceed to Step 6 (inconclusive path).

Step 4. Acquisition path:
        LearningEngine.learn(ctx) calls:
            a. ConceptExtractor.extract(ctx.working_memory) → List[ConceptCandidate]
            b. For each ConceptCandidate: UKM.write_concept(candidate, proof_trace_id=ctx.request_id)
            c. SkillMemory.acquire_from_trace(ctx.working_memory.proof_trace) → SkillRecord or None
            d. EpisodeMemory.log(ctx) → EpisodeRecord
        All writes are wrapped in a single UKM transaction (atomic).

Step 5. Weakening path:
        LearningEngine.weaken(ctx) applies Process 2h to the primary concept involved.
        EpisodeMemory.log(ctx, outcome=FAILED) → EpisodeRecord.

Step 6. Inconclusive path:
        No UKM write occurs. ctx.working_memory is discarded.
        EpisodeMemory.log(ctx, outcome=TIMEOUT) → EpisodeRecord.

Step 7. Post-cycle (async, non-blocking):
        ReflectionEngine.reflect(cognitive_trace) → CorrectionProposals.
        Proposals are queued in MetaCognitiveController.correction_queue.
        MCC processes the queue at its next scheduled tick (not in this request's cycle).

Step 8. ctx is destroyed. No state from ctx survives outside UKM/EpisodeMemory.
```

#### STATE TRANSITIONS
| Phase | UKM State | MME State |
|---|---|---|
| Before (Step 1) | Stable | Stable |
| During (Steps 2–4) | Locked for writing (per concept_id) | WorkingMemory delta only |
| After (Step 4, success) | New concept_id rows committed | WorldStateAssertion updated |
| After (Step 5, failure) | Concept strength decremented | Contradiction flag set if applicable |
| After (Step 6, timeout) | Unchanged | Unchanged |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| UKM write deadlock | timeout > 10ms on lock acquire | Abort write; log LearningEvent(type=WRITE_TIMEOUT) |
| ConceptExtractor returns empty | len(candidates) == 0 | Log as INCONCLUSIVE; no UKM write |
| Z3VerificationEngine timeout | elapsed > 5000ms | Treat as Step 6 |
| EpisodeMemory write failure | SQLException | Log to fallback file; retry on next MCC tick |

#### TESTING STRATEGY
- Unit: Feed a known-correct proof trace → assert UKM contains the expected concept with correct strength and proof_trace_id.
- Unit: Feed a refuted proof trace → assert concept strength decremented, not deleted.
- Integration: Run 100 concurrent requests with overlapping concept writes → assert zero data corruption via UKM row checksums.
- Regression: After learning a concept, feed identical input → assert concept strength > initial value (Strengthening activated).

---

### Process 2b — Teaching Lifecycle (Human-in-the-Loop)

**Purpose**: The complete sequence when a human explicitly instructs the system to learn a new concept or relationship via the TeachingProtocol.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| teaching_instruction | str | Human via API endpoint POST /v1/teach |
| teacher_id | str | Authenticated user identity |
| teaching_mode | Enum[CONCEPT, RELATION, SKILL, CORRECTION] | Request parameter |
| confidence_override | Optional[float 0.0–1.0] | Request parameter (human-asserted trust) |

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| lesson_result | LessonResult | API response to teacher |
| compiled_lesson | CompiledLesson | TeachingProtocol internal storage |
| ukm_delta | List[UKMWriteRecord] | Committed only if validation passes |
| teaching_episode | EpisodeRecord | EpisodeMemory (tagged source=HUMAN_TEACH) |

#### ALGORITHM
```
Step 1. TeachingProtocol.receive(teaching_instruction, teacher_id, teaching_mode):
        Allocate a TeachingContext (tc) with:
            tc.teacher_id = teacher_id
            tc.raw_instruction = teaching_instruction
            tc.mode = teaching_mode
            tc.received_at = utcnow()

Step 2. LessonIngestion (Process 2c) runs. Returns CompiledLesson or ValidationFailure.
        If ValidationFailure: return LessonResult(status=REJECTED, reason=error_message).

Step 3. TeachingProtocol checks confidence_override:
        If confidence_override is not None:
            CompiledLesson.confidence = min(confidence_override, 0.95)
            (cap at 0.95 — no human teaching yields absolute certainty)
        Else:
            CompiledLesson.confidence = 0.80  (default human teaching trust)

Step 4. TeachingProtocol routes based on CompiledLesson.lesson_type:
        CONCEPT  → Process 2d (Concept Acquisition)
        RELATION → Process 2e (Relationship Formation)
        SKILL    → Process 2f (Skill Formation)
        CORRECTION → Process 2o (Error Correction)

Step 5. UKM records all of the above with source_tag = HUMAN_TEACH and teacher_id.

Step 6. EpisodeMemory.log(tc, outcome=TAUGHT) → EpisodeRecord.

Step 7. MetaCognitiveController emits LearningEvent(type=HUMAN_TEACH, teacher_id, concept_id).
        MCC checks if this teaching contradicts an existing concept. If contradiction detected:
            Trigger Process 2p (Conflict Resolution) before committing.
```

#### STATE TRANSITIONS
| Phase | UKM State | TeachingProtocol State |
|---|---|---|
| Before Step 2 | Stable | AWAITING_LESSON |
| After Step 2 | Stable (not yet written) | LESSON_COMPILED |
| After Step 4 | New/updated concept committed | LESSON_COMMITTED |
| After Step 7 | Stable | IDLE |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| Incoherent instruction | UnderstandingEngine.detect_incoherence() returns True | REJECTED; return explanation to teacher |
| Concept already exists | UKM.exists(concept_id) == True | Route to Strengthening (2g) or Correction (2o) |
| Contradiction detected | Process 2p triggers | Pause commit; return ConflictReport to teacher |
| teacher_id not authenticated | auth middleware | 403 before TeachingProtocol reached |

#### TESTING STRATEGY
- Unit: POST /v1/teach with a well-formed instruction → assert LessonResult(status=ACCEPTED) and concept exists in UKM.
- Unit: POST /v1/teach with a contradictory instruction → assert ConflictReport returned, no UKM write.
- Integration: 10 concurrent teachers posting different concepts → assert all 10 are committed independently.
- Security: POST /v1/teach without auth token → assert 403.

---

---

### Process 2c — Lesson Ingestion

**Purpose**: Convert a raw human teaching instruction string into a typed, validated, executable CompiledLesson. This is the parsing and compilation layer — it produces no UKM writes.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| raw_instruction | str | TeachingContext.raw_instruction |
| teacher_id | str | TeachingContext.teacher_id |
| mode | Enum[CONCEPT, RELATION, SKILL, CORRECTION] | TeachingContext.mode |
| ukm_snapshot | UKMReadView | Read-only snapshot of current concept state |

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| compiled_lesson | CompiledLesson | TeachingProtocol.route() |
| validation_report | ValidationReport | Returned to teacher on failure |

**CompiledLesson fields**:
```
lesson_type: Enum[CONCEPT, RELATION, SKILL, CORRECTION]
lesson_id: UUID4
concept_name: str
formula: Optional[str]          # symbolic expression if applicable
formula_ast: Optional[Z3Expr]   # compiled by ConceptCompiler
domain: str                     # e.g., "mathematics", "physics", "general"
parent_concept_ids: List[str]   # existing concepts this derives from
confidence: float               # set by TeachingLifecycle in Step 3
raw_text: str                   # preserved for provenance
compiled_at: datetime
```

#### ALGORITHM
```
Step 1. LanguageBridge.parse(raw_instruction) → StructuredInput.

Step 2. UnderstandingEngine.understand(structured_input, ukm_snapshot) → SemanticFrame.
        If SemanticFrame.incoherence_detected:
            Return ValidationReport(valid=False, reason=INCOHERENT, detail=incoherence_report).

Step 3. Extract concept_name from SemanticFrame.entities[0].canonical_name.
        If concept_name is empty or ambiguous:
            Return ValidationReport(valid=False, reason=AMBIGUOUS_CONCEPT).

Step 4. Extract formula if mode == CONCEPT or CORRECTION:
        a. LogicParser.extract_formula(SemanticFrame) → formula_str or None
        b. If formula_str is not None:
               ConceptCompiler.compile(formula_str) → formula_ast or CompileError
               If CompileError: Return ValidationReport(valid=False, reason=FORMULA_INVALID, detail=error).

Step 5. Validate domain:
        domain = SemanticFrame.domain or infer from parent_concept_ids.
        If domain is None: domain = "general".

Step 6. Validate parent_concept_ids against ukm_snapshot:
        For each parent_id in SemanticFrame.referenced_concepts:
            If not ukm_snapshot.exists(parent_id):
                Return ValidationReport(valid=False, reason=UNKNOWN_PARENT, detail=parent_id).

Step 7. Validate for mode == RELATION:
        Extract source_concept_id and target_concept_id from SemanticFrame.
        Extract relation_type (IS_A, HAS_PROPERTY, DEPENDS_ON, CONTRADICTS, GENERALISES).
        If either id missing: Return ValidationReport(valid=False, reason=MISSING_RELATION_ENDPOINT).

Step 8. Construct CompiledLesson with all validated fields. Return it.
```

#### STATE TRANSITIONS
- No UKM state changes occur in this process.
- ConceptCompiler caches the compiled formula_ast in its internal LRU cache (keyed by formula_str).

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| Formula syntax error | ConceptCompiler raises CompileError | ValidationReport(FORMULA_INVALID) |
| Ambiguous entity reference | UnderstandingEngine returns ClarificationRequest | Return clarification question to teacher |
| Unknown parent concept | ukm_snapshot.exists() == False | ValidationReport(UNKNOWN_PARENT) |
| Instruction too long (>2048 chars) | len(raw_instruction) > 2048 | ValidationReport(INSTRUCTION_TOO_LONG) |

#### TESTING STRATEGY
- Unit: Well-formed CONCEPT instruction → assert CompiledLesson has correct formula_ast and domain.
- Unit: Formula with syntax error → assert ValidationReport(FORMULA_INVALID).
- Unit: Reference to non-existent parent concept → assert ValidationReport(UNKNOWN_PARENT).
- Fuzz: 1000 random string inputs → assert zero uncaught exceptions (always returns LessonResult or ValidationReport).

---

### Process 2d — Concept Acquisition

**Purpose**: Introduce a new Concept node into the UKM from a verified proof or validated CompiledLesson. This process must not run unless verification has passed.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| concept_candidate | ConceptCandidate | ConceptExtractor.extract() or CompiledLesson |
| proof_trace_id | UUID4 | CognitiveTrace or TeachingContext |
| source | Enum[PROOF, HUMAN_TEACH, SELF_PLAY] | Caller |
| initial_strength | float 0.0–1.0 | Computed by caller (see formula below) |

**Initial Strength Formula**:
```
PROOF source:       strength = 0.5 + (0.1 * z3_confidence_score)      clamp [0.5, 0.9]
HUMAN_TEACH source: strength = CompiledLesson.confidence                        [0.7, 0.95]
SELF_PLAY source:   strength = 0.3 + (0.1 * self_play_iteration_count)  clamp [0.3, 0.7]
```

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| concept_record | ConceptRecord | UKM.concept_store (permanent) |
| acquisition_event | LearningEvent | MetaCognitiveController |
| ontology_edge_requests | List[EdgeRequest] | Queued for Process 2e |

**ConceptRecord fields**:
```
concept_id: str              # hash(concept_name + domain)
concept_name: str
formula: Optional[str]
formula_ast_blob: bytes      # serialised Z3Expr
domain: str
strength: float
use_count: int               # 0 at creation
last_used: datetime
created_at: datetime
proof_trace_id: UUID4
source: Enum[PROOF, HUMAN_TEACH, SELF_PLAY]
status: Enum[ACTIVE, DEPRECATED, SUPERSEDED]  # ACTIVE at creation
version: int                 # 1 at creation; incremented on every evolution
lineage_id: str              # shared across all versions of this concept
```

#### ALGORITHM
```
Step 1. Check UKM.exists(concept_id):
        If exists AND status==ACTIVE:
            Do NOT acquire. Route to Process 2g (Concept Strengthening). Stop.
        If exists AND status==DEPRECATED:
            Reactivate: UKM.update(concept_id, status=ACTIVE, strength=initial_strength).
            Log LearningEvent(type=REACTIVATION). Stop.
        If not exists: Continue to Step 2.

Step 2. Validate concept_candidate.formula_ast if formula is present:
        ConceptCompiler.validate(formula_ast) → ValidationResult.
        If invalid: raise ConceptAcquisitionError("Formula failed re-validation").

Step 3. Generate concept_id = stable_hash(concept_name.lower() + ":" + domain).
        Check collision: if hash_collision_exists: append discriminator suffix.

Step 4. Construct ConceptRecord with all fields. strength = initial_strength.

Step 5. UKM.begin_transaction():
        UKM.insert_concept(concept_record)
        Queue ontology_edge_requests for parent_concept_ids (to be processed by 2e)
        UKM.commit()

Step 6. Emit LearningEvent(type=CONCEPT_ACQUIRED, concept_id, source, strength).
```

#### STATE TRANSITIONS
| Condition | UKM Before | UKM After |
|---|---|---|
| New concept | No row for concept_id | Row inserted, status=ACTIVE, version=1 |
| Deprecated concept reactivated | status=DEPRECATED | status=ACTIVE, strength reset |
| Duplicate (active) | status=ACTIVE | Unchanged; routed to Strengthening |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| Hash collision | UKM.exists(concept_id) && names differ | Append 4-char discriminator to concept_id |
| Formula re-validation failure | ConceptCompiler.validate() returns False | Abort acquisition; log WARNING |
| UKM insert fails | SQLException | Retry 3x with exponential backoff; escalate to MCC |

#### TESTING STRATEGY
- Unit: Acquire new concept → assert ConceptRecord exists with correct fields.
- Unit: Acquire concept that already exists → assert Strengthening called, no duplicate row.
- Unit: Acquire deprecated concept → assert status==ACTIVE and strength reset.
- Integration: Acquire 500 concepts sequentially → assert all 500 rows with distinct concept_ids.

---

---

### Process 2e — Relationship Formation

**Purpose**: Create a directed, typed edge in the OntologyGraph connecting two existing Concept nodes. Edges encode the semantic structure of HSCI's knowledge. No edge may connect to a non-existent or DEPRECATED concept.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| edge_request | EdgeRequest | Process 2d (acquisition) or CompiledLesson (RELATION mode) |
| source_concept_id | str | edge_request.source_id |
| target_concept_id | str | edge_request.target_id |
| relation_type | Enum | IS_A, HAS_PROPERTY, DEPENDS_ON, CONTRADICTS, GENERALISES, SPECIALISES |
| evidence_proof_trace_id | UUID4 | Proof or teaching that justifies this edge |
| initial_weight | float 0.0–1.0 | Computed from source strength * target strength |

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| edge_record | OntologyEdge | OntologyGraph (permanent) |
| edge_event | LearningEvent | MetaCognitiveController |

**OntologyEdge fields**:
```
edge_id: UUID4
source_concept_id: str
target_concept_id: str
relation_type: Enum[IS_A, HAS_PROPERTY, DEPENDS_ON, CONTRADICTS, GENERALISES, SPECIALISES]
weight: float              # starts at initial_weight; updated by use and verification
use_count: int             # 0 at creation
created_at: datetime
last_traversed: datetime
evidence_proof_trace_id: UUID4
status: Enum[ACTIVE, DEPRECATED, CONFLICTED]
```

#### ALGORITHM
```
Step 1. Validate both endpoints:
        Assert UKM.get_concept(source_concept_id).status == ACTIVE.
        Assert UKM.get_concept(target_concept_id).status == ACTIVE.
        If either fails: Raise RelationFormationError with concept_id.

Step 2. Check for duplicate edge:
        existing = OntologyGraph.get_edge(source_concept_id, target_concept_id, relation_type)
        If existing and existing.status == ACTIVE:
            Increment existing.use_count by 1.
            Update existing.weight += 0.05 (clamped to 1.0). Return existing.

Step 3. Check for CONTRADICTS conflict:
        If relation_type == CONTRADICTS:
            Verify that no IS_A edge exists between source and target in either direction.
            If IS_A edge exists: Raise RelationFormationError("IS_A and CONTRADICTS are mutually exclusive").

Step 4. Compute initial_weight:
        source_strength = UKM.get_concept(source_concept_id).strength
        target_strength = UKM.get_concept(target_concept_id).strength
        initial_weight = round(source_strength * target_strength, 4)

Step 5. Construct OntologyEdge record.

Step 6. OntologyGraph.insert_edge(edge_record) within the same UKM transaction as the
        concept that triggered this edge request.

Step 7. Emit LearningEvent(type=RELATION_FORMED, edge_id, relation_type).
```

#### STATE TRANSITIONS
| Condition | OntologyGraph Before | OntologyGraph After |
|---|---|---|
| New edge | No edge for (source, target, type) | Edge inserted, weight=initial_weight |
| Duplicate edge | Edge exists, status=ACTIVE | use_count+1, weight+=0.05 |
| CONTRADICTS with IS_A conflict | IS_A edge exists | Aborted; RelationFormationError raised |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| Endpoint concept DEPRECATED | UKM.get_concept().status check | Abort formation; queue for retry after concept reactivation |
| Cycle detection (IS_A only) | OntologyGraph.has_path(target, source, IS_A) | Raise CyclicInheritanceError |
| Graph write contention | Lock timeout > 10ms | Retry 3x; escalate to MCC |

#### TESTING STRATEGY
- Unit: Form IS_A edge between two ACTIVE concepts → assert edge inserted with correct weight.
- Unit: Attempt IS_A edge that creates a cycle → assert CyclicInheritanceError.
- Unit: CONTRADICTS edge where IS_A edge exists → assert RelationFormationError.
- Unit: Duplicate edge → assert use_count incremented, no duplicate row.

---

### Process 2f — Skill Formation

**Purpose**: Extract a procedural SkillMemory record from a completed multi-step proof trace. A skill encodes not just *what* the answer was, but *how* the system reasoned to reach it, so future similar problems can be solved more efficiently.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| proof_trace | List[ReasoningStep] | CognitiveTrace.reasoning_steps |
| verification_result | VerificationResult | Z3VerificationEngine |
| trigger_perception | PerceptionMap | NeuralPerceiver output |
| domain | str | CognitiveContext |
| episode_id | UUID4 | EpisodeMemory reference |

**Eligibility criteria** (all must be true to proceed):
1. `VerificationResult.verified == True`
2. `len(proof_trace) >= 3` (single-step solutions are not worth encoding as skills)
3. `trigger_perception.confidence >= 0.6`
4. No existing skill with cosine_similarity(trigger_embedding, existing.trigger_embedding) > 0.92

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| skill_record | Skill | SkillMemory (permanent) |
| skill_event | LearningEvent | MetaCognitiveController |

**Skill fields** (as per HSCI_V4_COGNITIVE_SPECIFICATION.md):
```
skill_id: UUID4
skill_name: str              # auto-generated: "{domain}_{trigger_keywords}"
trigger_pattern: SkillTriggerPattern
procedure: List[SkillStep]
success_count: int           # 1 at creation
failure_count: int           # 0 at creation
avg_solution_time_ms: float  # from cognitive_trace.duration_ms
source_episode_id: UUID4
domain: str
created_at: datetime
last_used: datetime
status: Enum[ACTIVE, RETIRED, SUPERSEDED]
```

#### ALGORITHM
```
Step 1. Check eligibility criteria (all four). If any fails: return None (no skill formed).

Step 2. Abstract the trigger pattern:
        a. Use trigger_perception.entity_types and relation_types (not specific values).
           e.g., if input had "velocity = 30 m/s", pattern uses {type: NUMERIC, unit: VELOCITY}.
        b. Compute trigger_embedding from NeuralPerceiver.embed(trigger_perception).
        c. Check SkillMemory.find_similar(trigger_embedding, threshold=0.92).
           If match found: Route to Process 2g on the existing skill (strengthen it). Stop.

Step 3. Abstract the procedure:
        For each ReasoningStep in proof_trace:
            Extract SkillStep(operation, input_types, output_types, solver_used).
            Discard specific values; retain structural operations.
        Result: List[SkillStep] as reusable procedure template.

Step 4. Compute skill_name:
        keywords = top-3 entity_types from trigger_perception.
        skill_name = f"{domain}_{'_'.join(keywords)}_{uuid4().hex[:6]}"

Step 5. Construct Skill record. success_count=1. avg_solution_time_ms = trace.duration_ms.

Step 6. SkillMemory.insert(skill_record).

Step 7. Emit LearningEvent(type=SKILL_ACQUIRED, skill_id, domain).
```

#### STATE TRANSITIONS
| Condition | SkillMemory Before | SkillMemory After |
|---|---|---|
| New skill (no similar exists) | No matching skill | Skill inserted, status=ACTIVE |
| Similar skill exists (>0.92 sim) | Existing skill | Routed to Strengthening; no new row |
| Eligibility failed | Unchanged | Unchanged |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| proof_trace too short | len(trace) < 3 | Skip silently; log at DEBUG level |
| trigger_embedding computation fails | NeuralPerceiver returns None | Skip skill formation; log WARNING |
| Similarity search timeout | elapsed > 50ms | Skip formation; emit LearningEvent(SKILL_TIMEOUT) |

#### TESTING STRATEGY
- Unit: 5-step proof trace with verified=True → assert Skill created with correct procedure.
- Unit: 2-step proof trace → assert no skill created.
- Unit: Proof trace with similar skill at 0.95 similarity → assert no new skill, existing strengthened.
- Performance: Similarity search over 10,000 skills → assert < 50ms.

---

---

### Process 2g — Concept Strengthening

**Purpose**: Increase the strength of an existing concept when a proof using that concept succeeds again. Strengthening is the reinforcement signal for correct knowledge.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| concept_id | str | UKM lookup |
| proof_trace_id | UUID4 | CognitiveTrace |
| domain | str | CognitiveContext |
| verifier_confidence | float 0.0–1.0 | VerificationResult.confidence |

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| updated_concept | ConceptRecord | UKM (updated row) |
| strengthening_event | LearningEvent | MetaCognitiveController |

#### ALGORITHM — Strengthening Update Rule
```
Let:
  S_old = current concept strength (from UKM)
  C     = verifier_confidence (from Z3VerificationEngine)
  alpha = 0.1   (learning rate for strengthening)
  S_max = 0.99  (strength ceiling — no concept reaches absolute certainty)

Update rule:
  delta = alpha * C * (S_max - S_old)
  S_new = S_old + delta
  S_new = clamp(S_new, 0.0, S_max)

This is an asymptotic approach to S_max. A concept that is proven
100 times with confidence=1.0 approaches 0.99 but never reaches 1.0.
```

```
Step 1. UKM.begin_transaction():
Step 2.     concept = UKM.get_concept_for_update(concept_id)  # row-level lock
Step 3.     S_new = compute_strengthening(concept.strength, verifier_confidence)
Step 4.     UKM.update_concept(concept_id,
                strength=S_new,
                use_count=concept.use_count + 1,
                last_used=utcnow(),
                version=concept.version + 1)
Step 5. UKM.commit()
Step 6. Emit LearningEvent(type=CONCEPT_STRENGTHENED, concept_id, delta=S_new - S_old).
```

#### STATE TRANSITIONS
| UKM Before | UKM After |
|---|---|
| strength=S_old, use_count=N, version=V | strength=S_new>S_old, use_count=N+1, version=V+1 |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| concept_id not found | UKM.get_concept() returns None | Log ERROR; skip (do not create) |
| concept status DEPRECATED | status check | Reactivate via Process 2d, then strengthen |
| Write contention | Lock timeout | Retry 3x; if all fail, log and skip this update |

#### TESTING STRATEGY
- Unit: Strengthen concept with S=0.5, C=1.0 → assert S_new == 0.5 + 0.1 * 1.0 * (0.99 - 0.5) = 0.549.
- Property: Apply strengthening 1000x with C=1.0 → assert S_new < 0.99 (never reaches ceiling).
- Unit: Strengthen non-existent concept → assert ERROR logged, no exception thrown.

---

### Process 2h — Concept Weakening

**Purpose**: Decrease the strength of an existing concept when a proof relying on that concept fails or is refuted. Weakening is the negative learning signal.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| concept_id | str | UKM lookup |
| counterexample | Z3Counterexample | VerificationResult.counterexample |
| failure_type | Enum[REFUTED, TIMEOUT, CONTRADICTION] | VerificationResult |
| proof_trace_id | UUID4 | CognitiveTrace |

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| updated_concept | ConceptRecord | UKM (updated row) |
| weakening_event | LearningEvent | MetaCognitiveController |
| deprecation_trigger | Optional[DeprecationRequest] | If strength drops below threshold |

#### ALGORITHM — Weakening Update Rule
```
Let:
  S_old  = current concept strength
  beta   = 0.2   (learning rate for weakening — faster than strengthening)
  S_min  = 0.05  (strength floor — concepts never reach 0 via weakening alone)
  DEPRECATION_THRESHOLD = 0.15

For REFUTED failure:
  delta = -beta * S_old
  S_new = max(S_old + delta, S_min)

For TIMEOUT failure:
  delta = -0.02  (small fixed penalty for inconclusive)
  S_new = max(S_old + delta, S_min)

For CONTRADICTION failure:
  delta = -0.5 * S_old  (severe penalty — concept contradicts another)
  S_new = max(S_old + delta, S_min)
```

```
Step 1. UKM.begin_transaction():
Step 2.     concept = UKM.get_concept_for_update(concept_id)
Step 3.     S_new = compute_weakening(concept.strength, failure_type)
Step 4.     UKM.update_concept(concept_id,
                strength=S_new,
                version=concept.version + 1)
            If S_new < DEPRECATION_THRESHOLD:
                emit DeprecationRequest(concept_id, reason=LOW_STRENGTH)
                  → routes to Process 2i (Forgetting) queue
Step 5. UKM.commit()
Step 6. Emit LearningEvent(type=CONCEPT_WEAKENED, concept_id, delta=S_new - S_old, failure_type).
```

#### STATE TRANSITIONS
| Condition | UKM Before | UKM After |
|---|---|---|
| REFUTED | strength=S_old | strength=S_new < S_old |
| Strength < threshold | status=ACTIVE | DeprecationRequest queued (not yet deprecated) |
| CONTRADICTION | strength=S_old | strength reduced by 50%; CONTRADICTS edge created |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| concept_id not found | UKM.get_concept() returns None | Log WARNING; skip |
| Weakening below S_min | clamp logic | Clamped at S_min; never goes negative |

#### TESTING STRATEGY
- Unit: Weaken concept with S=0.5, type=REFUTED → assert S_new == 0.4.
- Unit: Weaken concept with S=0.5, type=CONTRADICTION → assert S_new == 0.25.
- Property: Apply weakening 1000x → assert S_new >= S_min (floor respected).
- Integration: Weaken until S < 0.15 → assert DeprecationRequest emitted to MCC queue.

---

### Process 2i — Forgetting (Decay Model)

**Purpose**: Periodically deprecate concepts that are low-strength and rarely used. Forgetting is NOT deletion — it marks concepts DEPRECATED. They can be reactivated.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| ukm_snapshot | UKMReadView | Full read of UKM concepts table |
| current_time | datetime | utcnow() at scheduler tick |
| decay_config | DecayConfig | System configuration (see below) |

**DecayConfig**:
```
decay_interval_hours: int = 24       # scheduler runs this once per day
low_strength_threshold: float = 0.15
low_use_threshold: int = 3           # used fewer than 3 times total
age_threshold_days: int = 30         # older than 30 days
grace_period_days: int = 7           # human-taught concepts get 7 extra days
source_weights: Dict = {
    HUMAN_TEACH: 1.5,   # human-taught concepts decay slower
    PROOF: 1.0,
    SELF_PLAY: 0.8      # self-play concepts decay faster
}
```

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| deprecation_list | List[DeprecationRecord] | UKM batch update |
| decay_report | DecayReport | MetaCognitiveController log |

#### ALGORITHM — Decay Model
```
Step 1. MetaCognitiveController triggers Forgetting on schedule (once per 24h, low-API-load window).

Step 2. Query UKM for all concepts where status == ACTIVE:
        candidates = UKM.query(
            status=ACTIVE,
            strength < low_strength_threshold,
            use_count < low_use_threshold,
            age_days > age_threshold_days
        )

Step 3. For each candidate concept:
        a. Apply grace period: skip if source==HUMAN_TEACH and age_days < (age_threshold + grace_period).
        b. Apply time-based decay to strength:
               t = days_since_last_used
               decay_factor = source_weights[concept.source]
               S_decayed = concept.strength * exp(-0.01 * t / decay_factor)
               If S_decayed < 0.05: mark for deprecation.
        c. Append to deprecation_list.

Step 4. UKM.begin_transaction():
        For each DeprecationRecord in deprecation_list:
            UKM.update_concept(concept_id, status=DEPRECATED, deprecated_at=current_time)
            (strength value is preserved — not zeroed — for possible reactivation)
        UKM.commit()

Step 5. For each deprecated concept: cascade to OntologyGraph:
        All ACTIVE edges incident to the concept are marked DEPRECATED.
        (No edge deletion — topology is preserved for audit.)

Step 6. Emit DecayReport(deprecated_count, total_active, timestamp).
```

#### STATE TRANSITIONS
| Condition | UKM Before | UKM After |
|---|---|---|
| Decayed concept | status=ACTIVE, strength<0.05 | status=DEPRECATED, strength preserved |
| Associated edges | status=ACTIVE | status=DEPRECATED |
| Reactivation later | status=DEPRECATED | status=ACTIVE, strength=initial (via Process 2d) |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| Decay runs during high load | MCC load check before scheduling | Postpone by 1h if API RPS > 50 |
| Transaction too large (>10k concepts) | len(deprecation_list) > 10000 | Batch into 1000-concept transactions |

#### TESTING STRATEGY
- Unit: Concept with strength=0.10, use_count=1, age=60 days → assert DEPRECATED after decay run.
- Unit: Human-taught concept within grace period → assert NOT deprecated.
- Property: Strength value preserved after deprecation → assert UKM.get_concept().strength > 0.
- Integration: Reactivate a deprecated concept → assert status=ACTIVE and edges restored.

---

---

### Process 2j — Generalisation

**Purpose**: When two Concepts share sufficient semantic similarity and structural overlap, the ConceptEvolutionEngine (CEE) merges them into a single, more abstract concept. The originals become SUPERSEDED.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| concept_a | ConceptRecord | UKM |
| concept_b | ConceptRecord | UKM |
| evolution_evidence | EvolutionEvidence | CEE analysis |
| similarity_score | float | OntologyGraph semantic distance computation |

**Generalisation Eligibility**:
1. `similarity_score >= 0.88` (semantic similarity between concept_a and concept_b)
2. Both concepts have `status == ACTIVE`
3. Both concepts are in the same `domain`
4. Neither concept has `source == HUMAN_TEACH` unless `confidence < 0.75`
   (human-defined concepts require strong evidence before generalisation)
5. Z3VerificationEngine can prove that `formula_a IMPLIES formula_b` or vice versa (logical subsumption)

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| generalised_concept | ConceptRecord | UKM (new row, status=ACTIVE) |
| superseded_a | ConceptRecord | UKM (updated: status=SUPERSEDED) |
| superseded_b | ConceptRecord | UKM (updated: status=SUPERSEDED) |
| lineage_links | List[ConceptLineage] | UKM lineage table |
| generalisation_event | LearningEvent | MetaCognitiveController |

#### ALGORITHM
```
Step 1. CEE receives EvolutionProposal(type=GENERALISE, concept_a_id, concept_b_id).

Step 2. Verify eligibility (all 5 criteria). If any fails: reject proposal.

Step 3. Compute the generalised formula:
        a. Extract the common logical structure shared by formula_a and formula_b.
           Use Z3Verifier.find_common_antecedent(formula_a, formula_b) → abstract_formula.
        b. If no common antecedent can be found: reject with reason=NO_COMMON_FORMULA.

Step 4. Generate generalised concept name:
        name = CEE.generate_abstract_name(concept_a.name, concept_b.name)
        domain = concept_a.domain  (must be same)
        strength = (concept_a.strength + concept_b.strength) / 2.0
        source = PROOF (always — generalisation is always proof-driven)
        lineage_id = UUID4()  (new lineage)

Step 5. UKM.begin_transaction():
        a. Insert generalised_concept (new ConceptRecord).
        b. Update concept_a: status=SUPERSEDED, superseded_by=generalised_concept.concept_id.
        c. Update concept_b: status=SUPERSEDED, superseded_by=generalised_concept.concept_id.
        d. Insert ConceptLineage records:
               ConceptLineage(parent_id=concept_a.concept_id, child_id=generalised_concept.concept_id, type=GENERALISED_FROM)
               ConceptLineage(parent_id=concept_b.concept_id, child_id=generalised_concept.concept_id, type=GENERALISED_FROM)
        e. Migrate all OntologyGraph edges: re-point edges that pointed to concept_a or concept_b
               to point to generalised_concept (where relation_type != CONTRADICTS).
        f. UKM.commit()

Step 6. Emit LearningEvent(type=GENERALISATION, new_concept_id, merged=[a_id, b_id]).
```

#### STATE TRANSITIONS
| Object | Before | After |
|---|---|---|
| concept_a | status=ACTIVE | status=SUPERSEDED, superseded_by=new |
| concept_b | status=ACTIVE | status=SUPERSEDED, superseded_by=new |
| generalised_concept | Not in UKM | status=ACTIVE, lineage_id=new |
| OntologyGraph edges | point to a or b | re-pointed to new concept |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| No common formula found | Z3Verifier returns None | Reject; emit EvolutionVerdict(REJECTED) |
| Eligibility check fails | Any criterion false | Reject; no state change |
| Edge migration partial failure | SQLException mid-migration | Full rollback; retry next CEE schedule |

#### TESTING STRATEGY
- Unit: Two concepts with formulas `x > 0 AND x < 10` and `x > 0 AND x < 5` → assert generalised to `x > 0`.
- Unit: Concepts in different domains → assert rejection.
- Unit: Human-taught concept with confidence > 0.75 → assert rejection.
- Integration: After generalisation, query old concept_id → assert status=SUPERSEDED and redirect to new.

---

### Process 2k — Specialisation

**Purpose**: When a single Concept is observed behaving differently across two distinct contexts, the CEE splits it into two domain-specific variants. The original becomes SUPERSEDED.

#### INPUTS
| Field | Type | Source |
|---|---|---|
| parent_concept | ConceptRecord | UKM |
| context_a | DomainContext | ReflectionEngine analysis |
| context_b | DomainContext | ReflectionEngine analysis |
| divergence_evidence | EvolutionEvidence | CEE (at least 10 episodes showing divergence) |

**Specialisation Eligibility**:
1. `parent_concept.status == ACTIVE`
2. Minimum 10 episodes involving parent_concept across two distinct contexts
3. Z3VerificationEngine confirms that `formula_A AND NOT formula_B` is satisfiable
   (the two specialised versions are logically distinct)
4. Both resulting specialised concepts must have estimated strength > 0.3

#### OUTPUTS
| Field | Type | Destination |
|---|---|---|
| specialised_concept_a | ConceptRecord | UKM (new row) |
| specialised_concept_b | ConceptRecord | UKM (new row) |
| superseded_parent | ConceptRecord | UKM (updated) |
| lineage_links | List[ConceptLineage] | UKM lineage table |

#### ALGORITHM
```
Step 1. CEE receives EvolutionProposal(type=SPECIALISE, parent_concept_id, context_a, context_b).

Step 2. Verify eligibility (all 4 criteria). If any fails: reject.

Step 3. Compute specialised formulas:
        formula_a = Z3Verifier.restrict_formula(parent.formula, context_a.constraints)
        formula_b = Z3Verifier.restrict_formula(parent.formula, context_b.constraints)

Step 4. Generate names:
        name_a = f"{parent.concept_name}_{context_a.domain_tag}"
        name_b = f"{parent.concept_name}_{context_b.domain_tag}"

Step 5. Compute initial strengths:
        strength_a = parent.strength * context_a.episode_fraction
        strength_b = parent.strength * context_b.episode_fraction
        (episode fractions sum to 1.0 and represent proportion of episodes in each context)

Step 6. UKM.begin_transaction():
        a. Insert specialised_concept_a and specialised_concept_b.
        b. Update parent: status=SUPERSEDED, superseded_by=[a_id, b_id].
        c. Insert ConceptLineage:
               ConceptLineage(parent_id=parent.concept_id, child_id=a.concept_id, type=SPECIALISED_INTO)
               ConceptLineage(parent_id=parent.concept_id, child_id=b.concept_id, type=SPECIALISED_INTO)
        d. Migrate OntologyGraph edges:
               Edges in context_a → re-point to specialised_concept_a.
               Edges in context_b → re-point to specialised_concept_b.
               Ambiguous edges → duplicated for both.
        e. UKM.commit()

Step 7. Emit LearningEvent(type=SPECIALISATION, parent_id, children=[a_id, b_id]).
```

#### STATE TRANSITIONS
| Object | Before | After |
|---|---|---|
| parent_concept | status=ACTIVE | status=SUPERSEDED |
| specialised_a | Not in UKM | status=ACTIVE, lineage_id=parent.lineage_id |
| specialised_b | Not in UKM | status=ACTIVE, lineage_id=parent.lineage_id |

#### FAILURE MODES
| Failure | Detection | Recovery |
|---|---|---|
| Formulas not logically distinct | Z3 check fails | Reject; no specialisation |
| Insufficient episodes | episode count < 10 | Reject; CEE re-evaluates in next cycle |
| One specialised strength < 0.3 | estimate check | Reject to prevent weak fragmentation |

#### TESTING STRATEGY
- Unit: Parent concept used in physics and chemistry contexts → assert two specialised concepts created.
- Unit: Fewer than 10 episodes → assert rejection.
- Integration: Query parent_id after specialisation → assert SUPERSEDED and children listed.

---
