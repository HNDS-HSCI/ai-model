# HSCI: Hyper-Symbolic Cognitive Intelligence
## Complete Architectural Implementation Specification
### For: Gemini CLI / Senior Principal Engineer / Research Implementation

---

## PREAMBLE: READ THIS FIRST

You are acting as a **Senior Principal AI Research Engineer** implementing
a novel neurosymbolic cognitive architecture called HSCI (Hyper-Symbolic
Cognitive Intelligence). This is not a standard software project. This is
a research-grade AI system that combines:

- Neural perception (small graph neural network)
- Symbolic reasoning (Microsoft Z3 SMT solver)
- Proof-guided learning (novel mechanism)
- Concept extraction (Inductive Logic Programming)
- Self-improving intelligence (CEGIS-based self-play)

Your implementation must follow **Axiomatic First** principles:
- Every output is formally verified before being returned
- Every weight update is grounded in symbolic proof
- Every concept is extracted from proven examples, not memorized
- No probabilistic guessing is ever shown as a final answer

This document is the **single source of truth**. Implement exactly what
is specified. Do not simplify. Do not substitute. Do not skip layers.

---

## PART 1: SYSTEM VISION AND PRINCIPLES

### 1.1 What This System Is

HSCI is a self-verifying, self-improving cognitive architecture that:

1. **Learns** — builds concepts from proven examples, not statistical patterns
2. **Reasons** — composes concepts to solve unseen problems
3. **Verifies** — mathematically proves every answer before outputting
4. **Improves** — continuously deepens knowledge through self-play
5. **Transfers** — applies concepts across domains without retraining

### 1.2 Core Design Principles

**Principle 1: Truth Over Probability**
The system never outputs a probabilistic guess as a final answer.
Every answer is either proven correct or explicitly marked as unverified.

**Principle 2: Proof-Guided Learning**
Neural component weights are updated ONLY based on symbolic proof traces
and counterexamples from Z3. Not from random gradients. Not from data volume.

**Principle 3: Concept First**
The system stores abstract concepts, not specific examples.
After solving "2+3=5" and "10+7=17", it stores ADDITION as a concept,
not the specific instances.

**Principle 4: Minimal Neural, Maximal Symbolic**
The neural component is small (~10M parameters) and handles ONLY:
- Natural language → structured entity graph
- Intent classification
- Concept matching

All reasoning, verification, and learning signal generation is symbolic.

**Principle 5: Continuous Self-Improvement**
The system never stops learning. When idle, it runs the self-play engine
to generate hypotheses, prove them, and expand its concept library.

**Principle 6: Full Explainability**
Every output includes a complete reasoning trace. The system can explain
exactly which concepts it used, how it composed them, and the Z3 proof
that validates the answer.

---

## PART 2: COMPLETE ARCHITECTURE

### 2.1 System Overview

```
INPUT (natural language / structured data)
    |
    v
[LAYER 1: PERCEPTION]
    NeuralPerceiver (Graph Neural Network)
    - Converts input to EntityGraph
    - Classifies intent into axiom category
    - Extracts entities and relationships
    |
    v
[LAYER 2: KNOWLEDGE RETRIEVAL]
    KnowledgeBase
    - Queries ConceptLibrary for relevant concepts
    - Finds structural analogies via OntologyGraph
    - Retrieves similar episodes from EpisodeMemory
    |
    v
[LAYER 3: REASONING]
    ReasoningEngine
    - HTNPlanner decomposes problem into sub-goals
    - ConceptComposer combines relevant concepts
    - Builds candidate solution
    |
    v
[LAYER 4: VERIFICATION]
    Z3VerificationEngine
    - Formalizes candidate as Z3 constraints
    - Runs SMT solver to prove or disprove
    - If invalid: extracts counterexample
    - Counterexample feeds back to Layer 3 (CEGIS loop)
    |
    v
[LAYER 5: LEARNING]
    LearningEngine
    - Extracts new concept from proof trace (if novel)
    - Updates neural perceiver weights (proof-guided)
    - Stores episode in EpisodeMemory
    - Reinforces existing concepts (Hebbian)
    |
    v
OUTPUT (proven answer + full reasoning trace)
    |
    v
[BACKGROUND: SELF-PLAY ENGINE]
    Runs continuously when system is idle
    - Generates hypotheses from concept combinations
    - Proves/disproves them
    - Expands concept library autonomously
```

### 2.2 Data Flow Specification

```python
# Complete data flow — every field must be implemented

InputSignal:
    raw_text: str
    structured_data: Optional[Dict]  # JSON/CSV if provided
    timestamp: datetime
    session_id: str

PerceptionMap:
    entities: Dict[str, Any]         # extracted entities + values
    unknown_entities: List[str]      # entities to solve for
    relationships: List[Relationship] # how entities relate
    intent: AxiomType               # REDUCTION/COMPOSITION/SYNTHESIS/TRANSFORMATION
    confidence: float               # 0.0 to 1.0
    entity_graph: Graph             # full graph structure

ConceptQuery:
    intent: AxiomType
    entity_types: List[str]
    relationship_types: List[str]
    domain_hint: Optional[str]

KnowledgeResult:
    direct_matches: List[Concept]   # exact concept matches
    analogical_matches: List[Concept] # structural analogies
    episodes: List[Episode]         # similar past problems
    confidence: float

ReasoningPlan:
    sub_goals: List[SubGoal]        # decomposed tasks
    concept_assignments: Dict[SubGoal, Concept]
    composition_order: List[int]    # execution order
    candidate_solution: Expression  # mathematical expression

VerificationResult:
    valid: bool
    proof_trace: Optional[ProofTrace]  # if valid
    counterexample: Optional[Dict]     # if invalid
    z3_model: Optional[z3.ModelRef]
    confidence: float               # always 1.0 if valid (proven)
    correction_hint: Optional[str]  # guidance for repair

LearningResult:
    new_concept: Optional[Concept]  # if novel pattern found
    reinforced_concept: Optional[Concept]  # if existing strengthened
    weight_updates: List[WeightUpdate]     # neural weight changes
    episode_stored: Episode

FinalOutput:
    answer: Any                     # proven answer
    reasoning_trace: ReasoningTrace # complete explanation
    proof: ProofTrace               # Z3 proof
    concepts_used: List[Concept]    # which concepts applied
    confidence: float               # always 1.0 if proven
    is_verified: bool
```

---

## PART 3: LAYER-BY-LAYER IMPLEMENTATION

### 3.1 LAYER 1: Neural Perceiver

**File:** `hsci/neural/perceiver.py`

**Architecture:** Small Graph Neural Network (GNN)
- NOT a transformer, NOT an LLM
- Input: tokenized text → entity graph
- Output: PerceptionMap
- Size: ~10M parameters maximum
- Framework: PyTorch

```python
# IMPLEMENT EXACTLY THIS INTERFACE

class NeuralPerceiver:
    """
    Converts raw input into structured PerceptionMap.
    Uses a Graph Neural Network to encode entity relationships.
    Weights updated ONLY by ProofGuidedLearner, never by standard loss.
    """

    def __init__(self, config: PerceiverConfig):
        self.encoder = GraphEncoder(
            input_dim=config.input_dim,        # 256
            hidden_dim=config.hidden_dim,      # 512
            output_dim=config.output_dim,      # 128
            num_layers=config.num_layers       # 4
        )
        self.entity_extractor = EntityExtractor()
        self.intent_classifier = IntentClassifier(
            input_dim=128,
            num_classes=4  # REDUCTION/COMPOSITION/SYNTHESIS/TRANSFORMATION
        )
        self.relationship_detector = RelationshipDetector()
        self.weight_version = 0  # increments on every proof-guided update

    def perceive(self, input_signal: InputSignal) -> PerceptionMap:
        # Step 1: Extract entities from raw text
        entities = self.entity_extractor.extract(input_signal.raw_text)

        # Step 2: Build entity graph
        graph = self.build_entity_graph(entities, input_signal.raw_text)

        # Step 3: Encode graph
        embedding = self.encoder(graph)

        # Step 4: Classify intent
        intent = self.intent_classifier(embedding)

        # Step 5: Detect relationships
        relationships = self.relationship_detector.detect(graph, embedding)

        return PerceptionMap(
            entities=entities,
            relationships=relationships,
            intent=intent,
            confidence=intent.confidence,
            entity_graph=graph
        )

    def update_weights_from_proof(self, update: WeightUpdate):
        """
        CRITICAL: This is the ONLY way weights change.
        Called by LearningEngine after Z3 verification.
        Direction is either 'strengthen' or 'weaken'.
        """
        for param_name, delta in update.deltas.items():
            param = self.get_parameter(param_name)
            if update.direction == "strengthen":
                param.data += update.learning_rate * delta
            else:
                param.data -= update.learning_rate * delta * 0.1
        self.weight_version += 1
```

**EntityExtractor implementation requirements:**
- Must handle: numbers, variables, operators, units, unknowns
- Must identify: "find", "calculate", "solve for" as unknown markers
- Must parse: "salary=5000" as {salary: 5000, type: known}
- Must parse: "find take-home" as {take_home: None, type: unknown}

**IntentClassifier categories:**
```
REDUCTION:       Math/Logic — simplifying to primitive truth
                 Triggers: "solve", "calculate", "find", "compute"

COMPOSITION:     Linking entities via constraints
                 Triggers: "given...find", "if...then", "relationship between"

SYNTHESIS:       Constructing new procedural logic
                 Triggers: "write code", "build", "implement", "create algorithm"

TRANSFORMATION:  Converting information states
                 Triggers: "convert", "translate", "explain", "summarize"
```

---

### 3.2 LAYER 2: Knowledge Base

**File:** `hsci/knowledge/knowledge_base.py`

```python
class KnowledgeBase:
    """
    The brain's long-term memory.
    Stores concepts, not examples.
    Organized as an ontology graph.
    """

    def __init__(self):
        self.concept_library = ConceptLibrary()
        self.ontology = OntologyGraph()
        self.episode_memory = EpisodeMemory(max_episodes=10000)

    def query(self, perception: PerceptionMap) -> KnowledgeResult:
        # Direct match
        direct = self.concept_library.find_by_intent(
            perception.intent,
            perception.entity_types
        )

        # Analogical match — find structurally similar concepts
        # even from completely different domains
        analogies = self.ontology.find_structural_analogies(
            perception.entity_graph,
            top_k=5
        )

        # Episode match — similar past problems
        episodes = self.episode_memory.find_similar(
            perception,
            top_k=3
        )

        return KnowledgeResult(
            direct_matches=direct,
            analogical_matches=analogies,
            episodes=episodes
        )

    def store_concept(self, concept: Concept):
        self.concept_library.add(concept)
        self.ontology.integrate(concept)  # links to related concepts

    def reinforce_concept(self, concept: Concept, strength: float):
        self.concept_library.update_strength(concept.id, strength)
        self.ontology.strengthen_edges(concept.id, strength)
```

**Concept data structure — implement exactly:**
```python
@dataclass
class Concept:
    id: str                          # UUID
    name: str                        # "ADDITION", "PERCENTAGE", etc.
    axiom_type: AxiomType
    abstract_rule: str               # "result = a + b"
    z3_template: str                 # "result == Int('a') + Int('b')"
    domain: str                      # "arithmetic", "physics", etc.
    learned_from_domains: List[str]  # domains where confirmed
    strength: float                  # 0.0 to 1.0, increases with use
    proof_count: int                 # how many times proven
    created_at: datetime
    last_used: datetime
    generalizes_to: List[str]        # other concept IDs it subsumes
    required_entities: List[str]     # entity types needed to apply
    optional_entities: List[str]
    z3_verified: bool                # was this concept Z3-verified?
```

**OntologyGraph requirements:**
- Nodes: Concepts
- Edges: IS_A, PART_OF, GENERALIZES, COMPOSES, ANALOGOUS_TO
- Must support: structural similarity search
- Must support: concept composition paths
- Implementation: NetworkX or custom adjacency list

---

### 3.3 LAYER 3: Reasoning Engine

**File:** `hsci/reasoning/reasoning_engine.py`

```python
class ReasoningEngine:
    """
    Core intelligence layer.
    Decomposes problems, composes concepts, builds solutions.
    Uses HTN planning for decomposition.
    Uses ConceptComposer for cross-domain transfer.
    """

    def __init__(self):
        self.htn_planner = HTNPlanner()
        self.concept_composer = ConceptComposer()
        self.solution_builder = SolutionBuilder()

    def reason(
        self,
        perception: PerceptionMap,
        knowledge: KnowledgeResult,
        max_attempts: int = 5
    ) -> ReasoningPlan:

        # Step 1: Decompose problem
        sub_goals = self.htn_planner.decompose(perception)

        # Step 2: Assign concepts to sub-goals
        assignments = {}
        for sub_goal in sub_goals:
            best_concept = self.concept_composer.find_best(
                sub_goal,
                knowledge.direct_matches,
                knowledge.analogical_matches
            )
            assignments[sub_goal] = best_concept

        # Step 3: Build candidate solution
        candidate = self.solution_builder.build(
            sub_goals,
            assignments,
            perception.entities
        )

        return ReasoningPlan(
            sub_goals=sub_goals,
            concept_assignments=assignments,
            candidate_solution=candidate
        )

    def repair(
        self,
        plan: ReasoningPlan,
        counterexample: Dict,
        correction_hint: str
    ) -> ReasoningPlan:
        """
        Called when Z3 returns invalid.
        Uses counterexample to refine the plan.
        This implements the CEGIS repair loop.
        """
        refined_constraints = self.extract_refined_constraints(
            plan,
            counterexample
        )
        return self.reason_with_constraints(
            plan.perception,
            plan.knowledge,
            refined_constraints
        )
```

**HTNPlanner decomposition rules:**
```
REDUCTION problems:
    → [IDENTIFY_UNKNOWNS, BUILD_EQUATION, SOLVE_EQUATION]

COMPOSITION problems:
    → [EXTRACT_ENTITIES, IDENTIFY_RELATIONSHIPS, BUILD_CONSTRAINT_NETWORK]

SYNTHESIS problems:
    → [DEFINE_INPUTS_OUTPUTS, IDENTIFY_ALGORITHM_PATTERN,
       BUILD_PROCEDURE, VERIFY_INVARIANTS]

TRANSFORMATION problems:
    → [PARSE_SOURCE_STRUCTURE, IDENTIFY_TARGET_STRUCTURE,
       MAP_TRANSFORMATION_RULES, APPLY_TRANSFORMATION]
```

**ConceptComposer cross-domain transfer:**
```python
class ConceptComposer:
    def find_best(self, sub_goal, direct, analogical):
        # First try direct match
        if direct:
            return self.rank_by_strength(direct)[0]

        # Then try analogical transfer
        # "tax deduction" → never seen → 
        # finds PERCENTAGE + SUBTRACTION →
        # composes them structurally
        if analogical:
            return self.compose_analogies(sub_goal, analogical)

        # Last resort: attempt synthesis from primitives
        return self.synthesize_from_primitives(sub_goal)
```

---

### 3.4 LAYER 4: Z3 Verification Engine

**File:** `hsci/symbolic/z3_verifier.py`

**This is the most critical layer. Implement with extreme care.**

```python
class Z3VerificationEngine:
    """
    The Truth Gatekeeper.
    Uses Microsoft Z3 SMT Solver.
    Every candidate solution passes through here.
    No answer is returned to user without passing this layer.
    """

    def __init__(self):
        self.solver = z3.Solver()
        self.timeout_ms = 5000  # 5 second timeout per verification

    def verify(
        self,
        candidate: Expression,
        perception: PerceptionMap,
        concept: Concept
    ) -> VerificationResult:

        self.solver.reset()
        self.solver.set("timeout", self.timeout_ms)

        # Step 1: Build Z3 constraints from perception
        known_constraints = self.build_known_constraints(
            perception.entities
        )

        # Step 2: Build Z3 constraint from candidate solution
        solution_constraint = self.build_solution_constraint(
            candidate,
            concept.z3_template
        )

        # Step 3: Add all constraints
        for constraint in known_constraints:
            self.solver.add(constraint)
        self.solver.add(solution_constraint)

        # Step 4: Check satisfiability
        result = self.solver.check()

        if result == z3.sat:
            model = self.solver.model()
            proof_trace = self.extract_proof_trace(model, candidate)
            return VerificationResult(
                valid=True,
                proof_trace=proof_trace,
                z3_model=model,
                confidence=1.0
            )

        elif result == z3.unsat:
            # Get counterexample by negating and resolving
            counterexample = self.extract_counterexample()
            return VerificationResult(
                valid=False,
                counterexample=counterexample,
                correction_hint=self.analyze_failure(counterexample),
                confidence=0.0
            )

        else:  # unknown (timeout)
            return VerificationResult(
                valid=False,
                counterexample=None,
                correction_hint="Z3 timeout — problem may be undecidable",
                confidence=0.0
            )

    def build_known_constraints(self, entities: Dict) -> List[z3.BoolRef]:
        """
        Converts perception entities to Z3 constraints.

        Examples:
        {salary: 5000} → z3.Int('salary') == 5000
        {tax_rate: 0.20} → z3.Real('tax_rate') == 0.20
        {take_home: None} → z3.Int('take_home') (free variable)
        """
        constraints = []
        for name, value in entities.items():
            if value is not None:
                z3_var = self.create_z3_variable(name, value)
                constraints.append(z3_var == value)
        return constraints

    def extract_proof_trace(self, model, candidate) -> ProofTrace:
        """
        Extracts human-readable proof trace from Z3 model.
        This becomes the learning signal for the neural layer.
        """
        return ProofTrace(
            steps=self.model_to_steps(model),
            variables=self.extract_variable_assignments(model),
            concepts_applied=candidate.concepts_used,
            structural_pattern=self.extract_pattern(model)
        )
```

**Z3 template library — implement these first:**
```python
Z3_TEMPLATES = {
    "ADDITION": {
        "template": "result == a + b",
        "z3": lambda a, b, result: result == a + b,
        "domain": "arithmetic"
    },
    "SUBTRACTION": {
        "template": "result == a - b",
        "z3": lambda a, b, result: result == a - b,
        "domain": "arithmetic"
    },
    "MULTIPLICATION": {
        "template": "result == a * b",
        "z3": lambda a, b, result: result == a * b,
        "domain": "arithmetic"
    },
    "DIVISION": {
        "template": "result == a / b",
        "z3": lambda a, b, result: z3.And(result == a / b, b != 0),
        "domain": "arithmetic"
    },
    "PERCENTAGE": {
        "template": "result == base * (rate / 100)",
        "z3": lambda base, rate, result: result == base * (rate / 100),
        "domain": "arithmetic"
    },
    "LINEAR_EQUATION": {
        "template": "a*x + b == c → x == (c-b)/a",
        "z3": lambda a, b, c, x: a * x + b == c,
        "domain": "algebra"
    },
    "LOOP_INVARIANT": {
        "template": "ForAll i: inv(i) → inv(i+1)",
        "z3": lambda inv, i: z3.ForAll([i], z3.Implies(inv(i), inv(i+1))),
        "domain": "programming"
    },
}
```

---

### 3.5 LAYER 5: Learning Engine

**File:** `hsci/learning/learning_engine.py`

**This is the most novel component. This is the research contribution.**

```python
class LearningEngine:
    """
    Proof-Guided Learning Engine.

    NOVEL MECHANISM:
    Neural weights are updated based on Z3 proof traces,
    not gradient descent on prediction loss.

    Every weight change is mathematically grounded.
    This is the core research contribution of HSCI.
    """

    def __init__(self, neural_perceiver, knowledge_base):
        self.perceiver = neural_perceiver
        self.knowledge = knowledge_base
        self.concept_extractor = ConceptExtractor()
        self.proof_guided_updater = ProofGuidedWeightUpdater()
        self.learning_rate = 0.01

    def learn(
        self,
        perception: PerceptionMap,
        plan: ReasoningPlan,
        verification: VerificationResult
    ) -> LearningResult:

        if verification.valid:
            return self._learn_from_proof(
                perception, plan, verification
            )
        else:
            return self._learn_from_counterexample(
                perception, plan, verification
            )

    def _learn_from_proof(self, perception, plan, verification):
        """
        Proof succeeded. Extract concept. Strengthen pathways.
        """

        # 1. Extract concept from proof trace
        new_concept = self.concept_extractor.extract(
            perception,
            plan.candidate_solution,
            verification.proof_trace
        )

        # 2. Store or reinforce concept
        if self.knowledge.contains(new_concept):
            self.knowledge.reinforce_concept(
                new_concept,
                strength=self.learning_rate
            )
            learning_action = "reinforced"
        else:
            self.knowledge.store_concept(new_concept)
            learning_action = "new_concept_discovered"

        # 3. Update neural weights based on proof
        # The proof trace tells us EXACTLY which perception
        # features led to this correct formalization
        weight_update = self.proof_guided_updater.compute_update(
            perception=perception,
            proof_trace=verification.proof_trace,
            direction="strengthen",
            learning_rate=self.learning_rate
        )
        self.perceiver.update_weights_from_proof(weight_update)

        # 4. Store episode
        episode = Episode(
            input=perception,
            solution=plan.candidate_solution,
            proof=verification.proof_trace,
            concepts_used=plan.concepts_used,
            timestamp=datetime.now()
        )
        self.knowledge.episode_memory.store(episode)

        return LearningResult(
            new_concept=new_concept if learning_action == "new_concept_discovered" else None,
            reinforced_concept=new_concept if learning_action == "reinforced" else None,
            weight_updates=weight_update,
            episode_stored=episode
        )

    def _learn_from_counterexample(self, perception, plan, verification):
        """
        Proof failed. Counterexample teaches what is impossible.
        Weakens wrong neural pathways.
        """

        # 1. Analyze what went wrong
        failure_pattern = self.analyze_failure(
            perception,
            plan,
            verification.counterexample
        )

        # 2. Weaken neural pathways that led to wrong formalization
        weight_update = self.proof_guided_updater.compute_update(
            perception=perception,
            proof_trace=verification.counterexample,
            direction="weaken",
            learning_rate=self.learning_rate * 0.5
        )
        self.perceiver.update_weights_from_proof(weight_update)

        # 3. Store impossibility in knowledge base
        # "we tried X, Z3 disproved it because Y"
        # This is valuable negative knowledge
        self.knowledge.store_impossibility(
            pattern=failure_pattern,
            counterexample=verification.counterexample
        )

        return LearningResult(
            weight_updates=weight_update,
            failure_logged=failure_pattern
        )


class ProofGuidedWeightUpdater:
    """
    Computes neural weight updates from Z3 proof traces.

    Key insight: A proof trace tells us WHICH features of the
    perception were structurally relevant to the correct solution.
    We strengthen those features' contribution to the network.
    """

    def compute_update(
        self,
        perception: PerceptionMap,
        proof_trace: ProofTrace,
        direction: str,
        learning_rate: float
    ) -> WeightUpdate:

        # Extract which perception features appeared in proof
        contributing_features = self.extract_contributing_features(
            perception.entity_graph,
            proof_trace
        )

        # Compute delta for each contributing feature
        deltas = {}
        for feature in contributing_features:
            relevance_score = proof_trace.feature_relevance(feature)
            deltas[feature.param_name] = relevance_score * learning_rate

        # Features that did NOT contribute get slight weakening
        non_contributing = perception.all_features - contributing_features
        for feature in non_contributing:
            deltas[feature.param_name] = -0.001  # very slight weakening

        return WeightUpdate(
            deltas=deltas,
            direction=direction,
            learning_rate=learning_rate,
            proof_version=proof_trace.version
        )


class ConceptExtractor:
    """
    Extracts abstract concepts from proven (perception, solution) pairs.
    Uses structural induction — finds the minimal rule explaining the proof.
    Based on Inductive Logic Programming principles.
    """

    def extract(
        self,
        perception: PerceptionMap,
        solution: Expression,
        proof_trace: ProofTrace
    ) -> Concept:

        # Step 1: Abstract away specific values
        # "salary=5000, tax=0.20, take_home=4000"
        # → "amount_a, rate, result = amount_a - (amount_a * rate)"
        abstract_rule = self.abstract_values(
            perception.entities,
            solution,
            proof_trace
        )

        # Step 2: Find structural pattern
        pattern = self.extract_structural_pattern(
            proof_trace.steps
        )

        # Step 3: Build Z3 template
        z3_template = self.build_z3_template(abstract_rule)

        # Step 4: Determine domain
        domain = self.infer_domain(perception, proof_trace)

        # Step 5: Find generalizations
        generalizations = self.find_generalizations(
            abstract_rule,
            self.knowledge_base.concept_library
        )

        return Concept(
            id=str(uuid4()),
            name=self.generate_concept_name(pattern),
            axiom_type=perception.intent,
            abstract_rule=abstract_rule,
            z3_template=z3_template,
            domain=domain,
            learned_from_domains=[domain],
            strength=0.5,  # starts at 0.5, grows with use
            proof_count=1,
            generalizes_to=generalizations,
            required_entities=self.extract_required_entities(abstract_rule),
            z3_verified=True
        )
```

---

### 3.6 SELF-PLAY ENGINE

**File:** `hsci/self_play/engine.py`

```python
class SelfPlayEngine:
    """
    Autonomous knowledge discovery.
    Runs in background thread when system is idle.
    Generates hypotheses, proves them, expands knowledge.

    This is HSCI's equivalent of human "thinking" and "dreaming".
    """

    def __init__(self, knowledge_base, reasoning_engine, z3_verifier, learning_engine):
        self.knowledge = knowledge_base
        self.reasoning = reasoning_engine
        self.verifier = z3_verifier
        self.learning = learning_engine
        self.running = False

    def start(self):
        self.running = True
        thread = Thread(target=self._run_loop, daemon=True)
        thread.start()

    def _run_loop(self):
        while self.running:
            try:
                # 1. Generate a hypothesis
                hypothesis = self._generate_hypothesis()

                # 2. Attempt to solve and verify
                plan = self.reasoning.reason(hypothesis, self.knowledge.query(hypothesis))
                result = self.verifier.verify(plan.candidate_solution, hypothesis, plan.primary_concept)

                # 3. Learn from result
                self.learning.learn(hypothesis, plan, result)

                # 4. Target weak concepts
                weak = self.knowledge.concept_library.get_weakest(n=3)
                for concept in weak:
                    practice = self._generate_targeted_practice(concept)
                    self._solve_and_learn(practice)

                time.sleep(0.1)  # prevent CPU monopolization

            except Exception as e:
                self.logger.error(f"Self-play error: {e}")
                continue

    def _generate_hypothesis(self) -> PerceptionMap:
        """
        Generates a novel problem by:
        1. Selecting 2-3 concepts from library
        2. Combining them into a new problem structure
        3. Returns as PerceptionMap for standard processing
        """
        concepts = self.knowledge.concept_library.sample(n=2)
        return self.hypothesis_builder.build_from_concepts(concepts)

    def _generate_targeted_practice(self, concept: Concept) -> PerceptionMap:
        """
        Generates a problem specifically designed to
        strengthen a weak concept.
        """
        return self.hypothesis_builder.build_for_concept(
            concept,
            difficulty=concept.strength  # harder as concept strengthens
        )
```

---

## PART 4: MAIN RIR LOOP ORCHESTRATION

**File:** `hsci/core/rir_loop.py`

```python
class RIRLoop:
    """
    Reinforced Intuitive Reasoning Loop.
    Orchestrates all layers end-to-end.
    Entry point for all user inputs.
    """

    def __init__(self):
        self.perceiver = NeuralPerceiver(PerceiverConfig())
        self.knowledge_base = KnowledgeBase()
        self.reasoning_engine = ReasoningEngine()
        self.verifier = Z3VerificationEngine()
        self.learning_engine = LearningEngine(
            self.perceiver,
            self.knowledge_base
        )
        self.self_play = SelfPlayEngine(
            self.knowledge_base,
            self.reasoning_engine,
            self.verifier,
            self.learning_engine
        )
        self.self_play.start()  # always running in background

    def process(self, raw_input: str) -> FinalOutput:
        """
        Complete RIR cycle for one input.
        CEGIS repair loop built in — retries up to 5 times.
        """

        # Step 1: Perceive
        perception = self.perceiver.perceive(
            InputSignal(raw_text=raw_input)
        )

        # Step 2: Retrieve knowledge
        knowledge = self.knowledge_base.query(perception)

        # Step 3-5: Reason → Verify → Repair loop (CEGIS)
        plan = self.reasoning_engine.reason(perception, knowledge)

        for attempt in range(5):
            result = self.verifier.verify(
                plan.candidate_solution,
                perception,
                plan.primary_concept
            )

            if result.valid:
                break

            # Repair using counterexample
            plan = self.reasoning_engine.repair(
                plan,
                result.counterexample,
                result.correction_hint
            )

        # Step 6: Learn regardless of outcome
        learning_result = self.learning_engine.learn(
            perception, plan, result
        )

        # Step 7: Build output
        return FinalOutput(
            answer=self.extract_answer(result),
            reasoning_trace=self.build_trace(perception, plan, result),
            proof=result.proof_trace,
            concepts_used=plan.concepts_used,
            confidence=result.confidence,
            is_verified=result.valid
        )
```

---

## PART 5: TECHNICAL STACK

### 5.1 Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"

# Symbolic reasoning
z3-solver = "^4.12.0"

# Neural perception
torch = "^2.1.0"
torch-geometric = "^2.4.0"     # Graph Neural Networks

# NLP / Entity extraction
spacy = "^3.7.0"
en_core_web_sm = "*"           # spacy English model

# Knowledge graph
networkx = "^3.2.0"

# ILP / Concept extraction
popper = "^2.0.0"              # Inductive Logic Programming

# HTN Planning
pyhop = "^1.0.0"               # HTN planner

# Storage
sqlite3 = "*"                  # Episode memory
json = "*"                     # Concept library

# Monitoring
loguru = "^0.7.0"
rich = "^13.0.0"               # Beautiful console output
```

### 5.2 Project Structure

```
hsci/
├── core/
│   ├── __init__.py
│   ├── rir_loop.py            # Main orchestrator
│   ├── data_types.py          # All dataclasses
│   └── config.py              # System configuration
│
├── neural/
│   ├── perceiver.py           # NeuralPerceiver
│   ├── encoder.py             # GraphEncoder (GNN)
│   ├── entity_extractor.py    # EntityExtractor
│   ├── intent_classifier.py   # IntentClassifier
│   └── relationship_detector.py
│
├── knowledge/
│   ├── knowledge_base.py      # KnowledgeBase
│   ├── concept_library.py     # ConceptLibrary
│   ├── ontology_graph.py      # OntologyGraph
│   └── episode_memory.py      # EpisodeMemory
│
├── reasoning/
│   ├── reasoning_engine.py    # ReasoningEngine
│   ├── htn_planner.py         # HTNPlanner
│   ├── concept_composer.py    # ConceptComposer
│   └── solution_builder.py    # SolutionBuilder
│
├── symbolic/
│   ├── z3_verifier.py         # Z3VerificationEngine
│   ├── formalizer.py          # Expression → Z3
│   ├── counterexample.py      # Counterexample analysis
│   └── z3_templates.py        # Z3_TEMPLATES library
│
├── learning/
│   ├── learning_engine.py     # LearningEngine
│   ├── proof_guided_updater.py # ProofGuidedWeightUpdater
│   └── concept_extractor.py   # ConceptExtractor (ILP)
│
├── self_play/
│   ├── engine.py              # SelfPlayEngine
│   └── hypothesis_builder.py  # HypothesisBuilder
│
├── training/
│   ├── math_trainer.py        # Phase 1: Math training
│   ├── coding_trainer.py      # Phase 2: Coding training
│   └── evaluation.py          # Transfer learning evaluation
│
├── api/
│   ├── cli.py                 # Command line interface
│   └── server.py              # REST API (optional)
│
└── tests/
    ├── test_perception.py
    ├── test_verification.py
    ├── test_learning.py
    ├── test_transfer.py
    └── test_self_play.py
```

---

## PART 6: TRAINING PIPELINE

### 6.1 Phase 1: Math Training (Start Here)

```python
# hsci/training/math_trainer.py

MATH_TRAINING_EXAMPLES = [
    # Basic arithmetic
    ("2 + 3", 5),
    ("10 + 7", 17),
    ("100 + 50", 150),
    ("15 - 8", 7),
    ("100 - 37", 63),
    ("4 * 6", 24),
    ("12 * 11", 132),
    ("20 / 4", 5),
    ("100 / 8", 12.5),

    # Percentage
    ("20% of 500", 100),
    ("15% of 200", 30),
    ("tax is 18%, amount is 1000, find tax amount", 180),

    # Equations
    ("x + 5 = 10, find x", {"x": 5}),
    ("2x = 14, find x", {"x": 7}),
    ("x - 3 = 7, find x", {"x": 10}),

    # Multi-step
    ("salary is 5000, tax rate is 20%, find take-home pay", {"take_home": 4000}),
    ("base price 1000, discount 15%, find final price", {"final_price": 850}),
    ("rectangle length 8, width 5, find area", {"area": 40}),
]

# After training on these 20 examples:
# System should solve ANY arithmetic/algebra problem
# Not because it memorized — because it learned concepts
```

### 6.2 Validation — Transfer Test

```python
# These problems were NEVER in training data
# System must solve them using transferred concepts

TRANSFER_TEST_CASES = [
    # Physics (never trained on)
    ("velocity is 20 m/s, time is 5s, find distance", {"distance": 100}),
    ("force is 50N, mass is 10kg, find acceleration", {"acceleration": 5}),

    # Finance (never trained on)
    ("principal 10000, rate 8% per year, find interest after 2 years", {"interest": 1600}),

    # Novel compositions
    ("monthly salary 8000, deductions 25%, find annual take-home", {"annual_take_home": 72000}),
]

# Target: >80% accuracy on transfer tests
# This proves genuine concept transfer, not memorization
```

---

## PART 7: EVALUATION METRICS

Track these metrics throughout development:

```python
METRICS = {
    # Core correctness
    "verification_rate": "% of answers that pass Z3 verification",
    "target": ">95% on trained domains",

    # Learning efficiency
    "concepts_per_example": "concepts extracted / training examples",
    "target": ">0.3 (learn something new from 30% of examples)",

    # Transfer learning
    "transfer_accuracy": "accuracy on never-seen domains",
    "target": ">80% on structurally similar domains",

    # Self-improvement
    "self_play_discovery_rate": "new concepts per hour of self-play",
    "target": ">2 concepts per hour initially",

    # Efficiency
    "training_examples_needed": "examples to learn a new concept",
    "target": "<10 examples per concept",

    # Speed
    "verification_latency_ms": "Z3 verification time",
    "target": "<500ms per verification",
}
```

---

## PART 8: IMPLEMENTATION ORDER

**Follow this exact order. Do not skip steps.**

```
WEEK 1-2: Foundation
□ data_types.py — all dataclasses defined
□ z3_templates.py — 10 core templates working
□ z3_verifier.py — verify() working for arithmetic
□ Test: verify("2+3=5") returns valid=True
□ Test: verify("2+3=6") returns valid=False with counterexample

WEEK 3-4: Perception
□ entity_extractor.py — parse entities from text
□ intent_classifier.py — classify 4 axiom types
□ perceiver.py — full PerceptionMap generation
□ Test: perceive("salary=5000, tax=20%, find take-home")
        returns correct entities and REDUCTION intent

WEEK 5-6: Knowledge + Reasoning
□ concept_library.py — store/retrieve concepts
□ ontology_graph.py — basic graph structure
□ htn_planner.py — decompose simple problems
□ reasoning_engine.py — build candidate solutions
□ Test: reason about arithmetic problem end-to-end

WEEK 7-8: Learning (Core Research Contribution)
□ concept_extractor.py — extract abstract rules from proofs
□ proof_guided_updater.py — weight updates from Z3 traces
□ learning_engine.py — full learn() cycle
□ Test: train on 5 addition examples
        verify ADDITION concept extracted
        verify neural weights updated

WEEK 9-10: Full RIR Loop
□ rir_loop.py — orchestrate all layers
□ CEGIS repair loop working
□ Test: end-to-end on all math training examples
□ Measure: verification rate, concept extraction rate

WEEK 11-12: Transfer + Self-Play
□ self_play engine running in background
□ Transfer test: math concepts → physics problems
□ Measure all metrics defined in Part 7
□ Begin paper draft
```

---

## PART 9: WHAT SUCCESS LOOKS LIKE

### Minimum Viable HSCI (End of Week 10)
```
Input:  "if base salary is 6000 and bonus is 15%, find total"
Output: {
    answer: 6900,
    is_verified: true,
    confidence: 1.0,
    concepts_used: ["MULTIPLICATION", "PERCENTAGE", "ADDITION"],
    reasoning_trace: [
        "Identified entities: base_salary=6000, bonus_rate=0.15",
        "Applied PERCENTAGE: bonus_amount = 6000 * 0.15 = 900",
        "Applied ADDITION: total = 6000 + 900 = 6900",
        "Z3 verified: base_salary + (base_salary * bonus_rate) == total"
    ],
    proof: "Z3 SAT: {base_salary: 6000, bonus_rate: 0.15, total: 6900}"
}
```

### Transfer Success (End of Week 12)
```
Input:  "velocity is 30 m/s, time is 4 seconds, find distance"
(Never trained on physics)
Output: {
    answer: 120,
    is_verified: true,
    concepts_used: ["MULTIPLICATION"],  # transferred from math
    reasoning_trace: [
        "Identified multiplicative relationship between velocity, time, distance",
        "Matched MULTIPLICATION concept from arithmetic domain",
        "Applied: distance = velocity * time = 30 * 4 = 120",
        "Z3 verified"
    ]
}
```

---

## PART 10: CRITICAL CONSTRAINTS

These are non-negotiable architectural constraints:

1. **NEVER return unverified answer as final output**
   If Z3 cannot verify, return: `{is_verified: false, answer: candidate, warning: "unverified"}`

2. **NEVER update neural weights except through ProofGuidedWeightUpdater**
   No standard loss functions. No optimizer.step() outside of proof-guided updates.

3. **NEVER store specific values in concept library**
   Always abstract: "result = a + b" not "5 = 2 + 3"

4. **ALWAYS run CEGIS repair loop before giving up**
   Minimum 3 attempts with counterexample-guided repair before returning unverified.

5. **ALWAYS run self-play in background**
   System should be learning even when not actively processing inputs.

6. **ALWAYS log full reasoning trace**
   Every decision must be explainable. No black-box steps anywhere.

---

## FINAL NOTE TO IMPLEMENTER

This architecture represents a genuine research contribution to
neurosymbolic AI. The core novelty is the proof-guided weight
update mechanism — neural learning grounded entirely in symbolic
verification rather than statistical gradients.

Build it carefully. Test each layer independently before integrating.
The Z3 verifier is the foundation — get that right first.

The goal is not to build something that looks intelligent.
The goal is to build something that IS intelligent — provably,
verifiably, transparently.

Start with Week 1. Get Z3 verification working for basic arithmetic.
Everything else follows from that foundation.
