# HSCI: Hyper-Symbolic Cognitive Intelligence
## Complete Master Document
## System Explanation + Full Implementation Prompt
### Version 3.0 — Neurosymbolic AGI Architecture

---

# SECTION A: WHAT THIS SYSTEM IS AND HOW IT WORKS
## Read This First — Understand Before Building

---

## A.1 THE BIG PICTURE

HSCI is a new kind of AI system. It is not an LLM like GPT or Claude.
It is not a simple rule-based expert system. It is something new:

> A system that LEARNS concepts from proven examples,
> REASONS using those concepts to solve problems,
> PROVES every answer mathematically before showing it,
> and IMPROVES itself continuously without human intervention.

This is how human intelligence actually works — not by memorizing
billions of examples, but by learning abstract concepts and applying
them to new situations.

---

## A.2 THE HUMAN BRAIN ANALOGY

To understand HSCI, understand how a human child learns:

```
AGE 5: Child sees "2 apples + 3 apples = 5 apples"
       Child sees "1 ball + 4 balls = 5 balls"
       Child sees "3 fingers + 2 fingers = 5 fingers"

       Brain does NOT memorize these three examples.
       Brain EXTRACTS the concept: "combining things increases count"
       Brain stores: ADDITION as an abstract rule.

AGE 6: Child sees money for first time.
       Never studied money. Never seen this before.
       But brain recognizes: "this is combining things"
       Applies ADDITION concept. Gets the right answer.
       This is TRANSFER — using old knowledge in new situations.

AGE 10: Child learns multiplication.
        Recognizes: "this is repeated addition"
        Connects new concept to existing ADDITION concept.
        Knowledge COMPOUNDS — each new concept builds on existing ones.
```

HSCI does exactly this:
- Learns CONCEPTS not examples
- TRANSFERS concepts across domains
- COMPOUNDS knowledge over time
- VERIFIES every answer with mathematical proof

---

## A.3 WHY THIS IS DIFFERENT FROM LLMs

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM (GPT, Claude, Gemini)                    │
├─────────────────────────────────────────────────────────────────┤
│ Training:   Reads billions of text examples                     │
│ Learning:   Adjusts 175 billion number weights                  │
│ Answering:  Predicts what token (word) comes next               │
│ Certainty:  None — it guesses based on patterns                 │
│ Errors:     Hallucinations — confidently wrong answers          │
│ Resources:  Requires massive GPU clusters                       │
│ Updating:   Cannot update without full retraining               │
│ Explainability: Black box — cannot show its working             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    HSCI (This System)                           │
├─────────────────────────────────────────────────────────────────┤
│ Training:   Learns from hundreds of proven examples             │
│ Learning:   Extracts abstract concepts from proofs              │
│ Answering:  Composes concepts and proves the answer             │
│ Certainty:  Mathematical proof — not a guess                    │
│ Errors:     Cannot output wrong verified answer (proven)        │
│ Resources:  Runs on a laptop                                    │
│ Updating:   Learns continuously from every interaction          │
│ Explainability: Shows every step of every reasoning             │
└─────────────────────────────────────────────────────────────────┘
```

---

## A.4 THE SEVEN LAYERS — HOW THE SYSTEM WORKS

HSCI has 7 layers. Every input passes through all 7 layers.
Here is what each layer does in plain language:

```
┌─────────────────────────────────────────────────────────────────┐
│  USER TYPES: "salary is 5000, tax is 20%, find take-home"       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0: LANGUAGE BRIDGE                                       │
│                                                                 │
│  Job: Understand what the user is saying                        │
│  How: Converts natural language → structured data               │
│                                                                 │
│  Input:  "salary is 5000, tax is 20%, find take-home"           │
│  Output: {                                                      │
│            salary: 5000 (known),                                │
│            tax_rate: 0.20 (known),                              │
│            take_home: unknown (solve for this),                 │
│            intent: REDUCTION,                                   │
│            domain: finance                                      │
│          }                                                      │
│                                                                 │
│  NEVER answers the question. Only extracts structure.           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: NEURAL PERCEIVER                                      │
│                                                                 │
│  Job: Build a graph of how entities relate to each other        │
│  How: Small graph neural network (~10M parameters)              │
│                                                                 │
│  Input:  Structured data from Layer 0                           │
│  Output: Entity graph with relationships encoded                │
│          salary ──[deduct]──► tax_rate                          │
│          salary ──[result]──► take_home                         │
│                                                                 │
│  Weights updated ONLY by symbolic proofs (Layer 4)              │
│  NOT by standard gradient descent                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: KNOWLEDGE BASE                                        │
│                                                                 │
│  Job: Find what the system already knows about this problem     │
│  How: Searches concept library and past episodes                │
│                                                                 │
│  Input:  Entity graph from Layer 1                              │
│  Output: Relevant concepts from memory                          │
│          Direct match: PERCENTAGE concept                       │
│          Direct match: SUBTRACTION concept                      │
│          Analogy: DISCOUNT (structurally similar)               │
│                                                                 │
│  Stores CONCEPTS not examples                                   │
│  "result = base - (base * rate)" not "4000 = 5000 - 1000"      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: REASONING ENGINE                                      │
│                                                                 │
│  Job: Figure out HOW to solve the problem                       │
│  How: HTN planning + concept composition                        │
│                                                                 │
│  Input:  Entity graph + relevant concepts                       │
│  Output: Candidate solution (not yet verified)                  │
│                                                                 │
│  Steps:                                                         │
│  1. Decompose: [FIND_DEDUCTION, SUBTRACT_FROM_BASE]             │
│  2. Compose:   deduction = salary * tax_rate = 5000 * 0.20      │
│  3. Compose:   take_home = salary - deduction                   │
│  4. Build:     take_home = 5000 - (5000 * 0.20) = 4000          │
│                                                                 │
│  This is REASONING — not pattern matching                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: VERIFICATION ENGINE (Z3 SMT SOLVER)                   │
│                                                                 │
│  Job: Prove the answer is mathematically correct                │
│  How: Microsoft Z3 formal verification                          │
│                                                                 │
│  Input:  Candidate solution from Layer 3                        │
│  Output: PROVEN or DISPROVEN + counterexample                   │
│                                                                 │
│  Checks: take_home == salary - (salary * tax_rate)              │
│          5000 - (5000 * 0.20) == 4000                           │
│          4000 == 4000  ✓  PROVEN                                │
│                                                                 │
│  If DISPROVEN: counterexample feeds back to Layer 3             │
│  This is the CEGIS loop — keeps trying until proven             │
│  Maximum 5 attempts before declaring unverifiable               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: LEARNING ENGINE                                       │
│                                                                 │
│  Job: Learn from this solved problem                            │
│  How: Extract concept + update neural weights from proof        │
│                                                                 │
│  Input:  Proof trace from Layer 4                               │
│  Output: Updated knowledge base + updated neural weights        │
│                                                                 │
│  If proof SUCCEEDED:                                            │
│    Extract abstract pattern: "result = base - (base * rate)"    │
│    Store as TAX_DEDUCTION concept if new                        │
│    Strengthen neural pathways that led to correct formalization │
│    Store episode in memory                                      │
│                                                                 │
│  If proof FAILED:                                               │
│    Store impossibility: "this approach does not work because X" │
│    Weaken neural pathways that led to wrong formalization       │
│    This is also valuable knowledge                              │
│                                                                 │
│  HEBBIAN PRINCIPLE: Neurons that fire together wire together    │
│  Pathways that lead to proofs get stronger                      │
│  Pathways that lead to failures get weaker                      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 6: RESPONSE BRIDGE                                       │
│                                                                 │
│  Job: Explain the answer in natural human language              │
│  How: Domain-aware templates + conversation management          │
│                                                                 │
│  Input:  Proven answer + reasoning trace + proof                │
│  Output: Natural language response with full explanation        │
│                                                                 │
│  "Your take-home pay is ₹4000.00                                │
│                                                                 │
│   Here is how I worked it out:                                  │
│     Step 1 → Tax: 20% of ₹5000 = ₹1000                         │
│     Step 2 → Take-home: ₹5000 − ₹1000 = ₹4000                  │
│                                                                 │
│   ✓ Mathematically verified                                     │
│   Concepts used: PERCENTAGE, SUBTRACTION"                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  BACKGROUND: SELF-PLAY ENGINE                                   │
│                                                                 │
│  Job: Keep learning even when no user is active                 │
│  How: Generate hypotheses, prove them, store new knowledge      │
│                                                                 │
│  Runs: Continuously in background thread                        │
│                                                                 │
│  Cycle:                                                         │
│  1. Pick 2 existing concepts from library                       │
│  2. Generate a new hypothesis by combining them                 │
│  3. Try to prove the hypothesis with Z3                         │
│  4. If proven: store as new concept. Brain grows.               │
│  5. If disproven: store as impossibility. Also valuable.        │
│  6. Find weakest concepts. Generate targeted practice.          │
│  7. Repeat forever.                                             │
│                                                                 │
│  This is HSCI's equivalent of human "thinking" and "studying"   │
│  The system gets smarter even while idle                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## A.5 THE LEARNING CYCLE IN DETAIL

This is the most important thing to understand about HSCI.

### How it learns from ONE interaction:

```
INTERACTION 1: User asks "2 + 3 = ?"

Layer 0: Parses → {a:2, b:3, result:unknown, intent:REDUCTION}
Layer 1: Builds entity graph
Layer 2: No concepts yet (first time learning)
Layer 3: Attempts primitive combination: result = a + b = 5
Layer 4: Z3 verifies: 2 + 3 == 5 → TRUE
Layer 5: Extracts concept ADDITION: "result = a + b"
         Stores in knowledge base
         Neural weights updated: "when I see two numbers
         and 'find result', use ADDITION"
Layer 6: "The answer is 5. Step 1: 2 + 3 = 5. ✓ Verified"

RESULT: HSCI now knows ADDITION.
```

```
INTERACTION 2: User asks "10 + 7 = ?"

Layer 0: Parses → {a:10, b:7, result:unknown}
Layer 2: Finds ADDITION concept (learned in interaction 1)
Layer 3: Applies: result = 10 + 7 = 17
Layer 4: Z3 verifies → TRUE
Layer 5: ADDITION concept STRENGTHENED (used again, proven again)
Layer 6: "The answer is 17. ✓ Verified"

RESULT: HSCI's ADDITION concept is now stronger.
```

```
INTERACTION 10: User asks "salary 5000, tax 20%, find take-home"
(HSCI has never seen finance before)

Layer 0: Parses → {salary:5000, tax_rate:0.20, take_home:unknown}
Layer 2: No direct match. But finds ANALOGY:
         "salary * tax_rate" looks like MULTIPLICATION
         "salary - deduction" looks like SUBTRACTION
         Composes: MULTIPLICATION + SUBTRACTION
Layer 3: take_home = salary - (salary * tax_rate) = 4000
Layer 4: Z3 verifies → TRUE
Layer 5: Extracts NEW concept: TAX_DEDUCTION
         "result = base - (base * rate)"
         Links to MULTIPLICATION and SUBTRACTION
Layer 6: "Your take-home is ₹4000. ✓ Verified"

RESULT: HSCI learned finance from math concepts.
        Never needed finance training data.
        This is genuine TRANSFER LEARNING.
```

---

## A.6 THE INTELLIGENCE GROWTH CURVE

```
DAY 1 (first 20 math examples):
  Concepts learned: ADDITION, SUBTRACTION, MULTIPLICATION,
                    DIVISION, PERCENTAGE, EQUATION_SOLVING
  Can solve: Any arithmetic or basic algebra problem
  Transfer: None yet

WEEK 1 (self-play running):
  Concepts learned: 20-30 concepts
  Discovers: PERCENTAGE = MULTIPLICATION + DIVISION
  Discovers: EQUATION_SOLVING = REDUCTION + SUBSTITUTION
  Can solve: Algebra, percentages, multi-step arithmetic
  Transfer: Math concepts composing with each other

MONTH 1 (100+ concepts):
  Domain transfer happening:
    Math → Finance (salary, tax, interest)
    Math → Physics (velocity, force, energy)
    Math → Statistics (average, probability)
  Can solve: Problems in domains never explicitly trained
  Self-play: Discovering new relationships every hour

MONTH 3 (500+ concepts):
  Deep concept hierarchy:
    Concrete: 2+3, velocity*time
    Abstract: ADDITIVE_COMBINATION, RATE_TIMES_TIME
    Meta: DIMENSIONAL_ANALYSIS, CONSERVATION_LAW
  Can solve: Complex multi-domain problems
  Transfer: Automatic across any structural analogy

MONTH 6 (1000+ concepts):
  Calculus concepts emerging from algebra concepts
  Physics concepts linking to geometry concepts
  Programming concepts linking to logic concepts
  Knowledge depth approaching domain expert level
  in trained domains
```

---

## A.7 WHAT MAKES THIS "INTELLIGENT"

True intelligence requires four things.
HSCI has all four:

```
1. UNDERSTANDING
   Not just reading words — understanding STRUCTURE
   "salary is 5000" → entity with value, type, role
   Relationship between entities matters, not just words

2. REASONING  
   Not looking up answers — DERIVING them
   Takes known concepts, composes them, builds solution
   Each step follows logically from the previous

3. VERIFICATION
   Not guessing — PROVING
   Z3 mathematically confirms every answer
   Cannot output a wrong verified answer

4. LEARNING
   Not static — GROWING
   Every proven interaction strengthens knowledge
   Every failed attempt teaches what does not work
   Self-play generates knowledge autonomously
```

---

## A.8 COMPLETE SYSTEM FLOW DIAGRAM

```
                    ┌──────────────────────────┐
                    │      USER INPUT           │
                    │  (any natural language)   │
                    └──────────┬───────────────┘
                               │
                               ▼
                    ┌──────────────────────────┐
                    │   LAYER 0: LANGUAGE       │
                    │   BRIDGE                  │
                    │   spaCy + Local LLM       │
                    │   → Structured JSON       │
                    └──────────┬───────────────┘
                               │
                               ▼
                    ┌──────────────────────────┐
                    │   LAYER 1: NEURAL         │
                    │   PERCEIVER               │
                    │   Graph Neural Network    │
                    │   → Entity Graph          │
                    └──────────┬───────────────┘
                               │
                    ┌──────────┴──────────────┐
                    │                         │
                    ▼                         ▼
         ┌─────────────────┐      ┌──────────────────────┐
         │  LAYER 2:        │      │  BACKGROUND:          │
         │  KNOWLEDGE       │◄─────│  SELF-PLAY ENGINE     │
         │  BASE            │      │  (always running)     │
         │  Concepts +      │─────►│  Generates + proves   │
         │  Episodes        │      │  new knowledge        │
         └────────┬────────┘      └──────────────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  LAYER 3:        │
         │  REASONING       │◄──────────────────┐
         │  ENGINE          │                   │
         │  HTN + Compose   │                   │ CEGIS
         └────────┬────────┘                   │ REPAIR
                  │                             │ LOOP
                  ▼                             │
         ┌─────────────────┐                   │
         │  LAYER 4:        │                   │
         │  Z3 VERIFIER     │───── FAIL ────────┘
         │  SMT Solver      │
         │  Proves/Disproves│───── PASS ─────────┐
         └─────────────────┘                     │
                                                 ▼
                                       ┌──────────────────┐
                                       │  LAYER 5:         │
                                       │  LEARNING ENGINE  │
                                       │  Concept Extract  │
                                       │  Weight Update    │
                                       └────────┬─────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │  LAYER 6:         │
                                       │  RESPONSE BRIDGE  │
                                       │  Natural language │
                                       │  + Explanation    │
                                       └────────┬─────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │   USER SEES:      │
                                       │   Proven answer   │
                                       │   Step-by-step    │
                                       │   reasoning       │
                                       │   ✓ Verified      │
                                       └──────────────────┘
```

---

# SECTION B: COMPLETE IMPLEMENTATION PROMPT
## For Gemini CLI — Senior Principal Engineer Implementation

---

## B.1 PROJECT OVERVIEW

You are implementing HSCI — Hyper-Symbolic Cognitive Intelligence.
This is a complete neurosymbolic AI system. Not a chatbot. Not a
wrapper around an existing LLM. A genuinely new AI architecture.

Build every component exactly as specified.
Do not simplify. Do not substitute. Do not skip.
Test each layer before building the next.

---

## B.2 COMPLETE PROJECT STRUCTURE

```
hsci/
├── core/
│   ├── __init__.py
│   ├── rir_loop.py              # Main orchestrator — all 7 layers
│   ├── data_types.py            # All dataclasses and enums
│   └── config.py                # System configuration
│
├── language/                    # LAYER 0
│   ├── bridge.py                # LanguageBridge orchestrator
│   ├── spacy_parser.py          # Stage 1: rule-based
│   └── llm_parser.py            # Stage 2: local LLM (Ollama)
│
├── neural/                      # LAYER 1
│   ├── perceiver.py             # NeuralPerceiver (GNN)
│   ├── encoder.py               # GraphEncoder
│   ├── entity_extractor.py      # EntityExtractor
│   └── intent_classifier.py     # IntentClassifier
│
├── knowledge/                   # LAYER 2
│   ├── knowledge_base.py        # KnowledgeBase
│   ├── concept_library.py       # ConceptLibrary
│   ├── ontology_graph.py        # OntologyGraph
│   └── episode_memory.py        # EpisodeMemory
│
├── reasoning/                   # LAYER 3
│   ├── reasoning_engine.py      # ReasoningEngine
│   ├── htn_planner.py           # HTNPlanner
│   ├── concept_composer.py      # ConceptComposer
│   └── solution_builder.py      # SolutionBuilder
│
├── symbolic/                    # LAYER 4
│   ├── z3_verifier.py           # Z3VerificationEngine
│   ├── formalizer.py            # Expression to Z3
│   ├── counterexample.py        # Counterexample analysis
│   └── z3_templates.py          # Z3 template library
│
├── learning/                    # LAYER 5
│   ├── learning_engine.py       # LearningEngine
│   ├── proof_guided_updater.py  # ProofGuidedWeightUpdater
│   └── concept_extractor.py     # ConceptExtractor (ILP)
│
├── response/                    # LAYER 6
│   ├── response_bridge.py       # ResponseBridge
│   ├── template_engine.py       # TemplateEngine
│   ├── formatters.py            # Domain formatters
│   ├── conversation_manager.py  # ConversationManager
│   └── tone_engine.py           # ToneEngine
│
├── self_play/                   # BACKGROUND ENGINE
│   ├── engine.py                # SelfPlayEngine
│   └── hypothesis_builder.py    # HypothesisBuilder
│
├── training/
│   ├── math_trainer.py          # Phase 1 training data
│   ├── coding_trainer.py        # Phase 2 training data
│   └── evaluator.py             # Transfer learning tests
│
├── cli/
│   └── main.py                  # Command line interface
│
└── tests/
    ├── test_language_bridge.py
    ├── test_perceiver.py
    ├── test_knowledge_base.py
    ├── test_reasoning.py
    ├── test_verifier.py
    ├── test_learning.py
    ├── test_response_bridge.py
    └── test_end_to_end.py
```

---

## B.3 ALL DATA TYPES

```python
# hsci/core/data_types.py
# Define ALL data structures here first.
# Every other module imports from here.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
from uuid import uuid4


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class AxiomType(Enum):
    REDUCTION       = "REDUCTION"       # solve/find/calculate
    COMPOSITION     = "COMPOSITION"     # given...find, constraints
    SYNTHESIS       = "SYNTHESIS"       # write code, build
    TRANSFORMATION  = "TRANSFORMATION"  # convert, explain

class ResponseType(Enum):
    VERIFIED            = "verified"
    UNVERIFIED          = "unverified"
    CANNOT_SOLVE        = "cannot_solve"
    NEW_CONCEPT_LEARNED = "new_concept_learned"

class VerificationStatus(Enum):
    PROVEN      = "proven"
    DISPROVEN   = "disproven"
    TIMEOUT     = "timeout"
    UNKNOWN     = "unknown"


# ─────────────────────────────────────────────
# LAYER 0: LANGUAGE BRIDGE TYPES
# ─────────────────────────────────────────────

@dataclass
class EntityValue:
    value: Optional[Any]          # numeric value or None if unknown
    unit: Optional[str]           # currency, percentage, time, etc.
    known: bool                   # True if given, False if to solve
    raw_text: str                 # original text this came from

@dataclass
class StructuredInput:
    entities: Dict[str, EntityValue]
    intent: str                   # AxiomType string
    axiom: str                    # same as intent
    unknowns: List[str]           # entity names to solve for
    domain: str                   # finance, physics, etc.
    operation_hint: str           # structural operation hint
    confidence: float             # 0.0 to 1.0
    raw_normalized: str           # cleaned input text
    parse_method: str             # "spacy" or "llm"
    is_followup: bool = False     # is this a follow-up question?


# ─────────────────────────────────────────────
# LAYER 1: PERCEPTION TYPES
# ─────────────────────────────────────────────

@dataclass
class Relationship:
    source: str                   # entity name
    target: str                   # entity name
    relation_type: str            # "deduct", "multiply", "equals", etc.
    strength: float               # 0.0 to 1.0

@dataclass
class PerceptionMap:
    entities: Dict[str, EntityValue]
    unknown_entities: List[str]
    relationships: List[Relationship]
    intent: AxiomType
    confidence: float
    entity_graph: Any             # NetworkX graph
    domain: str
    operation_hint: str


# ─────────────────────────────────────────────
# LAYER 2: KNOWLEDGE TYPES
# ─────────────────────────────────────────────

@dataclass
class Concept:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    axiom_type: AxiomType = AxiomType.REDUCTION
    abstract_rule: str = ""       # "result = a + b"
    z3_template: str = ""         # Z3-compatible constraint string
    domain: str = "arithmetic"
    learned_from_domains: List[str] = field(default_factory=list)
    strength: float = 0.5         # 0.0 to 1.0
    proof_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    generalizes_to: List[str] = field(default_factory=list)
    required_entities: List[str] = field(default_factory=list)
    z3_verified: bool = False

@dataclass
class Episode:
    id: str = field(default_factory=lambda: str(uuid4()))
    input_summary: str = ""
    domain: str = ""
    solution: str = ""
    concepts_used: List[str] = field(default_factory=list)
    was_verified: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class KnowledgeResult:
    direct_matches: List[Concept]
    analogical_matches: List[Concept]
    episodes: List[Episode]
    confidence: float


# ─────────────────────────────────────────────
# LAYER 3: REASONING TYPES
# ─────────────────────────────────────────────

@dataclass
class SubGoal:
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    required_entities: List[str] = field(default_factory=list)
    target_entity: str = ""
    axiom_type: AxiomType = AxiomType.REDUCTION

@dataclass
class ReasoningPlan:
    sub_goals: List[SubGoal]
    concept_assignments: Dict[str, Concept]
    candidate_solution: str        # mathematical expression
    concepts_used: List[str]
    primary_concept: Optional[Concept]
    perception: Optional[PerceptionMap] = None
    knowledge: Optional[KnowledgeResult] = None


# ─────────────────────────────────────────────
# LAYER 4: VERIFICATION TYPES
# ─────────────────────────────────────────────

@dataclass
class ProofStep:
    step_number: int
    operation: str
    input_values: Dict[str, Any]
    output_value: Any
    concept_applied: str

@dataclass
class ProofTrace:
    steps: List[ProofStep]
    variable_assignments: Dict[str, Any]
    concepts_applied: List[str]
    structural_pattern: str
    version: int = 0

    def feature_relevance(self, feature) -> float:
        # Returns how relevant a perception feature was to this proof
        return 1.0 if feature.name in self.concepts_applied else 0.1

@dataclass
class VerificationResult:
    valid: bool
    status: VerificationStatus
    proof_trace: Optional[ProofTrace]
    counterexample: Optional[Dict]
    z3_model: Optional[Any]
    confidence: float
    correction_hint: Optional[str]


# ─────────────────────────────────────────────
# LAYER 5: LEARNING TYPES
# ─────────────────────────────────────────────

@dataclass
class WeightUpdate:
    deltas: Dict[str, float]       # param_name → delta value
    direction: str                 # "strengthen" or "weaken"
    learning_rate: float
    proof_version: int
    source: str                    # "proof" or "counterexample"

@dataclass
class LearningResult:
    new_concept: Optional[Concept]
    reinforced_concept: Optional[Concept]
    weight_updates: Optional[WeightUpdate]
    episode_stored: Optional[Episode]
    failure_logged: Optional[str]


# ─────────────────────────────────────────────
# LAYER 6: RESPONSE TYPES
# ─────────────────────────────────────────────

@dataclass
class ResponseContext:
    answer: Any
    is_verified: bool
    confidence: float
    concepts_used: List[str]
    reasoning_trace: List[str]
    proof: Optional[str]
    domain: str
    original_input: str
    new_concept: Optional[str]
    counterexample: Optional[Dict]
    correction_hint: Optional[str]
    units: Optional[str]
    session_history: List[Any]

@dataclass
class ConversationTurn:
    user_input: str
    structured_input: dict
    hsci_output: dict
    response: str
    concepts_used: List[str]
    domain: str
    timestamp: datetime = field(default_factory=datetime.now)


# ─────────────────────────────────────────────
# FINAL OUTPUT TYPE
# ─────────────────────────────────────────────

@dataclass
class FinalOutput:
    answer: Any
    is_verified: bool
    confidence: float
    concepts_used: List[str]
    reasoning_trace: List[str]
    proof: Optional[ProofTrace]
    new_concept_learned: Optional[str] = None
    counterexample: Optional[Dict] = None
    correction_hint: Optional[str] = None
    attempts: int = 1
```

---

## B.4 LAYER 0: LANGUAGE BRIDGE

```python
# hsci/language/bridge.py

class LanguageBridge:
    """
    LAYER 0: Language Bridge
    Only entry point for raw human language into HSCI.
    Converts ANY natural language to StructuredInput.
    NEVER answers questions. Only extracts structure.
    """

    CONFIDENCE_THRESHOLD = 0.70

    def __init__(self, use_llm: bool = True):
        self.spacy_parser = SpacyParser()
        self.llm_parser = LLMParser("phi3:mini") if use_llm else None

    def parse(self, raw_input: str) -> StructuredInput:
        # Try spaCy first (fast)
        result = self.spacy_parser.parse(raw_input)

        # Escalate to LLM if confidence low
        if result.confidence < self.CONFIDENCE_THRESHOLD:
            if self.llm_parser and self.llm_parser.available:
                llm_result = self.llm_parser.parse(raw_input)
                if llm_result.confidence > result.confidence:
                    return llm_result

        return result

# IMPLEMENT FULL SpacyParser and LLMParser
# as specified in Language Bridge prompt document
# Key requirements:
# - Extract entities with values and units
# - Identify unknown entities (to solve for)
# - Classify intent: REDUCTION/COMPOSITION/SYNTHESIS/TRANSFORMATION
# - Classify domain: finance/physics/algebra/geometry/programming/etc
# - Detect operation hint
# - Normalize: "5k" → 5000, "20 percent" → 0.20
# - Handle follow-up questions
# - NEVER produce a final answer
```

---

## B.5 LAYER 1: NEURAL PERCEIVER

```python
# hsci/neural/perceiver.py
import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv, global_mean_pool

class GraphEncoder(nn.Module):
    """
    Graph Neural Network encoder.
    Converts entity graph to dense embedding.
    ~10M parameters maximum.
    """
    def __init__(self, input_dim=256, hidden_dim=512, output_dim=128):
        super().__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.conv3 = GCNConv(hidden_dim, output_dim)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.1)

    def forward(self, x, edge_index, batch):
        x = self.relu(self.conv1(x, edge_index))
        x = self.dropout(x)
        x = self.relu(self.conv2(x, edge_index))
        x = self.relu(self.conv3(x, edge_index))
        return global_mean_pool(x, batch)


class NeuralPerceiver:
    """
    LAYER 1: Neural Perceiver
    Converts StructuredInput to PerceptionMap.
    Weights updated ONLY by ProofGuidedWeightUpdater.
    NEVER by standard gradient descent.
    """

    def __init__(self):
        self.encoder = GraphEncoder()
        self.intent_classifier = nn.Linear(128, 4)
        self.weight_version = 0
        self.entity_embeddings = self._init_entity_embeddings()

    def perceive(self, structured: StructuredInput) -> PerceptionMap:
        # Build entity graph
        graph = self._build_graph(structured)

        # Encode
        with torch.no_grad():
            embedding = self.encoder(
                graph.x,
                graph.edge_index,
                graph.batch
            )

        # Classify intent (refine from bridge classification)
        intent_logits = self.intent_classifier(embedding)
        intent_idx = intent_logits.argmax().item()
        intent = list(AxiomType)[intent_idx]

        # Extract relationships from graph structure
        relationships = self._extract_relationships(graph, structured)

        return PerceptionMap(
            entities=structured.entities,
            unknown_entities=structured.unknowns,
            relationships=relationships,
            intent=intent,
            confidence=structured.confidence,
            entity_graph=graph,
            domain=structured.domain,
            operation_hint=structured.operation_hint
        )

    def update_weights_from_proof(self, update: WeightUpdate):
        """
        CRITICAL: ONLY way weights change.
        Called by LearningEngine after Z3 verification.
        """
        for param_name, delta in update.deltas.items():
            for name, param in self.named_parameters():
                if name == param_name:
                    if update.direction == "strengthen":
                        param.data += update.learning_rate * delta
                    else:
                        param.data -= update.learning_rate * abs(delta) * 0.1
        self.weight_version += 1

    def _build_graph(self, structured: StructuredInput):
        # Convert entities to graph nodes
        # Convert relationships to graph edges
        # Return PyTorch Geometric Data object
        # Each entity becomes a node with feature vector
        # Relationships become directed edges
        pass  # IMPLEMENT FULLY

    def _init_entity_embeddings(self):
        # Pre-trained embeddings for common entity names
        # "salary", "tax", "velocity", "distance", etc.
        # Use simple lookup table, not full word embeddings
        pass  # IMPLEMENT FULLY
```

---

## B.6 LAYER 2: KNOWLEDGE BASE

```python
# hsci/knowledge/knowledge_base.py

class ConceptLibrary:
    """Stores and retrieves learned concepts."""

    # Seed concepts — system starts with these
    # All others are learned from proofs
    SEED_CONCEPTS = [
        Concept(
            name="ADDITION",
            abstract_rule="result = a + b",
            z3_template="result == a + b",
            domain="arithmetic",
            z3_verified=True,
            strength=1.0
        ),
        Concept(
            name="SUBTRACTION",
            abstract_rule="result = a - b",
            z3_template="result == a - b",
            domain="arithmetic",
            z3_verified=True,
            strength=1.0
        ),
        Concept(
            name="MULTIPLICATION",
            abstract_rule="result = a * b",
            z3_template="result == a * b",
            domain="arithmetic",
            z3_verified=True,
            strength=1.0
        ),
        Concept(
            name="DIVISION",
            abstract_rule="result = a / b (b != 0)",
            z3_template="And(result == a / b, b != 0)",
            domain="arithmetic",
            z3_verified=True,
            strength=1.0
        ),
        Concept(
            name="PERCENTAGE",
            abstract_rule="result = base * (rate / 100)",
            z3_template="result == base * (rate / 100)",
            domain="arithmetic",
            z3_verified=True,
            strength=1.0
        ),
        Concept(
            name="LINEAR_EQUATION",
            abstract_rule="a*x + b = c → x = (c-b)/a",
            z3_template="a * x + b == c",
            domain="algebra",
            z3_verified=True,
            strength=1.0
        ),
    ]

    def __init__(self):
        self.concepts = {c.name: c for c in self.SEED_CONCEPTS}
        self.domain_index = self._build_domain_index()

    def find_by_intent(self, intent, entity_types):
        matches = []
        for concept in self.concepts.values():
            if concept.axiom_type == intent:
                matches.append(concept)
        return sorted(matches, key=lambda c: c.strength, reverse=True)

    def add(self, concept: Concept):
        self.concepts[concept.name] = concept
        self._update_domain_index(concept)

    def update_strength(self, concept_name: str, delta: float):
        if concept_name in self.concepts:
            c = self.concepts[concept_name]
            c.strength = min(1.0, c.strength + delta)
            c.proof_count += 1
            c.last_used = datetime.now()

    def get_weakest(self, n: int = 3) -> List[Concept]:
        sorted_concepts = sorted(
            self.concepts.values(),
            key=lambda c: c.strength
        )
        return sorted_concepts[:n]

    def sample(self, n: int = 2) -> List[Concept]:
        import random
        concepts = list(self.concepts.values())
        return random.sample(concepts, min(n, len(concepts)))


class OntologyGraph:
    """
    Graph of concept relationships.
    Enables analogical matching across domains.
    """

    EDGE_TYPES = [
        "IS_A",         # PERCENTAGE IS_A MULTIPLICATION
        "PART_OF",      # ADDITION PART_OF ARITHMETIC
        "GENERALIZES",  # MULTIPLICATION GENERALIZES ADDITION
        "COMPOSES",     # TAX_DEDUCTION COMPOSES [PERCENTAGE, SUBTRACTION]
        "ANALOGOUS_TO", # KINEMATICS_DISTANCE ANALOGOUS_TO MULTIPLICATION
    ]

    def __init__(self):
        import networkx as nx
        self.graph = nx.DiGraph()
        self._seed_ontology()

    def _seed_ontology(self):
        # Seed relationships between primitive concepts
        edges = [
            ("PERCENTAGE", "MULTIPLICATION", "IS_A"),
            ("MULTIPLICATION", "ADDITION", "GENERALIZES"),
            ("SUBTRACTION", "ADDITION", "ANALOGOUS_TO"),
            ("LINEAR_EQUATION", "SUBTRACTION", "COMPOSES"),
            ("LINEAR_EQUATION", "DIVISION", "COMPOSES"),
        ]
        for src, tgt, rel in edges:
            self.graph.add_edge(src, tgt, relation=rel)

    def integrate(self, concept: Concept):
        """Add new concept and link to related concepts."""
        self.graph.add_node(concept.name)
        # Find structurally similar existing concepts
        # Add IS_A, COMPOSES, ANALOGOUS_TO edges as appropriate
        pass  # IMPLEMENT

    def find_structural_analogies(self, entity_graph, top_k=5):
        """Find concepts structurally similar to given entity graph."""
        # Compare graph structure to stored concepts
        # Return most structurally similar ones
        pass  # IMPLEMENT


class EpisodeMemory:
    """Stores past solved problems for retrieval."""

    def __init__(self, max_episodes=10000):
        self.episodes = []
        self.max_episodes = max_episodes

    def store(self, episode: Episode):
        self.episodes.append(episode)
        if len(self.episodes) > self.max_episodes:
            # Remove weakest (least verified, oldest)
            self.episodes.sort(
                key=lambda e: (e.was_verified, e.timestamp),
                reverse=True
            )
            self.episodes = self.episodes[:self.max_episodes]

    def find_similar(self, perception: PerceptionMap, top_k=3):
        # Find episodes with similar domain and entity structure
        domain_matches = [
            e for e in self.episodes
            if e.domain == perception.domain
        ]
        return domain_matches[:top_k]


class KnowledgeBase:
    def __init__(self):
        self.concept_library = ConceptLibrary()
        self.ontology = OntologyGraph()
        self.episode_memory = EpisodeMemory()

    def query(self, perception: PerceptionMap) -> KnowledgeResult:
        direct = self.concept_library.find_by_intent(
            perception.intent,
            [e for e in perception.entities.keys()]
        )
        analogies = self.ontology.find_structural_analogies(
            perception.entity_graph, top_k=5
        )
        episodes = self.episode_memory.find_similar(perception, top_k=3)
        confidence = 1.0 if direct else (0.7 if analogies else 0.3)

        return KnowledgeResult(
            direct_matches=direct,
            analogical_matches=analogies or [],
            episodes=episodes,
            confidence=confidence
        )
```

---

## B.7 LAYER 3: REASONING ENGINE

```python
# hsci/reasoning/reasoning_engine.py

class HTNPlanner:
    """
    Hierarchical Task Network planner.
    Decomposes complex goals into solvable sub-goals.
    """

    DECOMPOSITION_RULES = {
        AxiomType.REDUCTION: [
            "IDENTIFY_UNKNOWNS",
            "BUILD_CONSTRAINT",
            "SOLVE_CONSTRAINT"
        ],
        AxiomType.COMPOSITION: [
            "EXTRACT_ENTITIES",
            "IDENTIFY_RELATIONSHIPS",
            "BUILD_CONSTRAINT_NETWORK",
            "SOLVE_NETWORK"
        ],
        AxiomType.SYNTHESIS: [
            "DEFINE_INPUTS_OUTPUTS",
            "IDENTIFY_ALGORITHM_PATTERN",
            "BUILD_PROCEDURE",
            "VERIFY_INVARIANTS"
        ],
        AxiomType.TRANSFORMATION: [
            "PARSE_SOURCE",
            "IDENTIFY_TARGET",
            "MAP_RULES",
            "APPLY_TRANSFORMATION"
        ],
    }

    def decompose(self, perception: PerceptionMap) -> List[SubGoal]:
        steps = self.DECOMPOSITION_RULES[perception.intent]
        sub_goals = []
        for step in steps:
            sub_goal = SubGoal(
                description=step,
                required_entities=list(perception.entities.keys()),
                target_entity=perception.unknown_entities[0]
                    if perception.unknown_entities else "result",
                axiom_type=perception.intent
            )
            sub_goals.append(sub_goal)
        return sub_goals


class ConceptComposer:
    """
    Composes concepts to solve sub-goals.
    Enables cross-domain transfer.
    """

    def find_best(
        self,
        sub_goal: SubGoal,
        direct: List[Concept],
        analogical: List[Concept]
    ) -> Optional[Concept]:

        # Direct match first
        if direct:
            return max(direct, key=lambda c: c.strength)

        # Analogical transfer
        if analogical:
            return self._compose_analogies(sub_goal, analogical)

        return None

    def _compose_analogies(self, sub_goal, analogical):
        # Find the most structurally relevant analog
        # Create a composed concept on the fly
        best = max(analogical, key=lambda c: c.strength)
        # Return adapted version for this domain
        return best


class SolutionBuilder:
    """Builds candidate solutions from plan and concepts."""

    def build(
        self,
        sub_goals: List[SubGoal],
        assignments: Dict[str, Concept],
        entities: Dict[str, EntityValue]
    ) -> str:
        """
        Builds mathematical expression for candidate solution.
        Example: "take_home = salary - (salary * tax_rate)"
        """
        # Extract known values
        known = {k: v.value for k, v in entities.items() if v.known}

        # Extract unknowns
        unknowns = [k for k, v in entities.items() if not v.known]

        if not unknowns:
            return "no_unknown_found"

        target = unknowns[0]

        # Apply best concept template
        best_concept = None
        for concept in assignments.values():
            if concept:
                best_concept = concept
                break

        if best_concept:
            return self._instantiate_template(
                best_concept.abstract_rule,
                known,
                target
            )

        return f"{target} = unknown"

    def _instantiate_template(self, template, known, target):
        # Replace abstract variables with actual entity names
        result = template
        for i, (k, v) in enumerate(known.items()):
            result = result.replace(f"var_{i}", k, 1)
        return result


class ReasoningEngine:
    def __init__(self):
        self.htn_planner = HTNPlanner()
        self.concept_composer = ConceptComposer()
        self.solution_builder = SolutionBuilder()

    def reason(
        self,
        perception: PerceptionMap,
        knowledge: KnowledgeResult
    ) -> ReasoningPlan:

        sub_goals = self.htn_planner.decompose(perception)

        assignments = {}
        for sub_goal in sub_goals:
            best = self.concept_composer.find_best(
                sub_goal,
                knowledge.direct_matches,
                knowledge.analogical_matches
            )
            assignments[sub_goal.id] = best

        candidate = self.solution_builder.build(
            sub_goals, assignments, perception.entities
        )

        primary_concept = (
            knowledge.direct_matches[0]
            if knowledge.direct_matches
            else knowledge.analogical_matches[0]
            if knowledge.analogical_matches
            else None
        )

        return ReasoningPlan(
            sub_goals=sub_goals,
            concept_assignments=assignments,
            candidate_solution=candidate,
            concepts_used=[
                c.name for c in assignments.values() if c
            ],
            primary_concept=primary_concept,
            perception=perception,
            knowledge=knowledge
        )

    def repair(self, plan, counterexample, hint) -> ReasoningPlan:
        # Use counterexample to try alternative concept
        # Remove the concept that led to failure
        # Try next best concept from knowledge
        pass  # IMPLEMENT
```

---

## B.8 LAYER 4: Z3 VERIFICATION ENGINE

```python
# hsci/symbolic/z3_verifier.py
import z3

# Z3 TEMPLATES — implement all of these
Z3_TEMPLATES = {
    "ADDITION": lambda a, b, result: result == a + b,
    "SUBTRACTION": lambda a, b, result: result == a - b,
    "MULTIPLICATION": lambda a, b, result: result == a * b,
    "DIVISION": lambda a, b, result: z3.And(result == a / b, b != 0),
    "PERCENTAGE": lambda base, rate, result: result == base * (rate / 100),
    "PERCENTAGE_DECIMAL": lambda base, rate, result: result == base * rate,
    "PERCENTAGE_SUBTRACTION": lambda base, rate, result:
        result == base - (base * rate),
    "LINEAR_EQUATION_1VAR": lambda a, b, c, x: a * x + b == c,
    "AREA_RECTANGLE": lambda l, w, area: area == l * w,
    "AREA_TRIANGLE": lambda base, h, area: area == (base * h) / 2,
    "SIMPLE_INTEREST": lambda p, r, t, i: i == p * r * t,
    "LOOP_INVARIANT": lambda inv, i:
        z3.ForAll([i], z3.Implies(inv(i), z3.And(inv(i+1), i >= 0))),
    "DISTANCE_RATE_TIME": lambda d, r, t: d == r * t,
    "FORCE_MASS_ACCEL": lambda f, m, a: f == m * a,
}


class Z3VerificationEngine:
    """
    LAYER 4: Z3 Verification Engine
    The Truth Gatekeeper.
    Every candidate solution must pass here.
    No answer reaches the user unverified.
    """

    def __init__(self):
        self.timeout_ms = 5000

    def verify(
        self,
        candidate: str,
        perception: PerceptionMap,
        concept: Optional[Concept]
    ) -> VerificationResult:

        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        try:
            # Build constraints from known entities
            z3_vars = self._create_z3_variables(perception.entities)
            constraints = self._build_constraints(
                perception.entities, z3_vars
            )

            # Add solution constraint
            solution_constraint = self._parse_solution(
                candidate, z3_vars, concept
            )

            for c in constraints:
                solver.add(c)
            if solution_constraint is not None:
                solver.add(solution_constraint)

            result = solver.check()

            if result == z3.sat:
                model = solver.model()
                trace = self._extract_proof_trace(model, z3_vars, concept)
                answer = self._extract_answer(
                    model, perception.unknown_entities, z3_vars
                )

                return VerificationResult(
                    valid=True,
                    status=VerificationStatus.PROVEN,
                    proof_trace=trace,
                    counterexample=None,
                    z3_model=model,
                    confidence=1.0,
                    correction_hint=None
                )

            elif result == z3.unsat:
                ce = self._extract_counterexample(solver, z3_vars)
                return VerificationResult(
                    valid=False,
                    status=VerificationStatus.DISPROVEN,
                    proof_trace=None,
                    counterexample=ce,
                    z3_model=None,
                    confidence=0.0,
                    correction_hint=self._analyze_failure(ce, concept)
                )

            else:
                return VerificationResult(
                    valid=False,
                    status=VerificationStatus.TIMEOUT,
                    proof_trace=None,
                    counterexample=None,
                    z3_model=None,
                    confidence=0.0,
                    correction_hint="Z3 timeout — problem may be undecidable"
                )

        except Exception as e:
            return VerificationResult(
                valid=False,
                status=VerificationStatus.UNKNOWN,
                proof_trace=None,
                counterexample=None,
                z3_model=None,
                confidence=0.0,
                correction_hint=f"Verification error: {str(e)}"
            )

    def _create_z3_variables(self, entities):
        z3_vars = {}
        for name, entity in entities.items():
            if entity.unit in ["percentage", "rate"]:
                z3_vars[name] = z3.Real(name)
            else:
                z3_vars[name] = z3.Real(name)
        return z3_vars

    def _build_constraints(self, entities, z3_vars):
        constraints = []
        for name, entity in entities.items():
            if entity.known and entity.value is not None:
                if name in z3_vars:
                    constraints.append(
                        z3_vars[name] == float(entity.value)
                    )
        return constraints

    def _parse_solution(self, candidate, z3_vars, concept):
        # Parse "take_home = salary - (salary * tax_rate)" into Z3
        # This is the critical translation step
        try:
            import ast
            # Simple expression parser for common patterns
            # IMPLEMENT full parser for mathematical expressions
            return None  # placeholder
        except Exception:
            return None

    def _extract_proof_trace(self, model, z3_vars, concept):
        assignments = {}
        for name, var in z3_vars.items():
            try:
                val = model[var]
                if val is not None:
                    assignments[name] = float(val.as_decimal(10))
            except Exception:
                pass

        return ProofTrace(
            steps=[],
            variable_assignments=assignments,
            concepts_applied=[concept.name] if concept else [],
            structural_pattern=concept.abstract_rule if concept else "",
            version=0
        )

    def _extract_answer(self, model, unknowns, z3_vars):
        for unknown in unknowns:
            if unknown in z3_vars:
                val = model[z3_vars[unknown]]
                if val is not None:
                    return float(val.as_decimal(10))
        return None

    def _extract_counterexample(self, solver, z3_vars):
        return {"reason": "constraints unsatisfiable"}

    def _analyze_failure(self, counterexample, concept):
        if concept:
            return f"Concept {concept.name} did not satisfy constraints"
        return "No applicable concept found"
```

---

## B.9 LAYER 5: LEARNING ENGINE

```python
# hsci/learning/learning_engine.py

class ProofGuidedWeightUpdater:
    """
    THE CORE RESEARCH CONTRIBUTION OF HSCI.

    Neural weights are updated based ONLY on symbolic proof traces.
    Not gradient descent. Not prediction loss.
    Every weight change is mathematically grounded.
    """

    def compute_update(
        self,
        perception: PerceptionMap,
        proof_trace,
        direction: str,
        learning_rate: float
    ) -> WeightUpdate:

        deltas = {}

        if hasattr(proof_trace, 'concepts_applied'):
            # Features that appeared in proof → strengthen
            for concept_name in proof_trace.concepts_applied:
                param_name = f"concept_weight_{concept_name}"
                deltas[param_name] = learning_rate

        # Features that did NOT contribute → slight weakening
        all_features = set(perception.entities.keys())
        contributing = set(
            getattr(proof_trace, 'concepts_applied', [])
        )
        non_contributing = all_features - contributing
        for feature in non_contributing:
            deltas[f"entity_weight_{feature}"] = -0.001

        return WeightUpdate(
            deltas=deltas,
            direction=direction,
            learning_rate=learning_rate,
            proof_version=getattr(proof_trace, 'version', 0),
            source="proof" if direction == "strengthen" else "counterexample"
        )


class ConceptExtractor:
    """
    Extracts abstract concepts from proven examples.
    Uses structural induction — minimal rule explaining the proof.
    Based on Inductive Logic Programming principles.
    """

    def extract(
        self,
        perception: PerceptionMap,
        solution: str,
        proof_trace: ProofTrace
    ) -> Concept:

        # Abstract away specific values
        abstract_rule = self._abstract_values(
            perception.entities, solution
        )

        # Build Z3 template
        z3_template = self._build_z3_template(abstract_rule)

        # Infer domain
        domain = perception.domain

        # Generate concept name from pattern
        name = self._generate_name(abstract_rule, domain)

        return Concept(
            name=name,
            axiom_type=perception.intent,
            abstract_rule=abstract_rule,
            z3_template=z3_template,
            domain=domain,
            learned_from_domains=[domain],
            strength=0.5,
            proof_count=1,
            z3_verified=True
        )

    def _abstract_values(self, entities, solution):
        abstracted = solution
        for name, entity in entities.items():
            if entity.known and entity.value is not None:
                abstracted = abstracted.replace(str(entity.value), name)
        return abstracted

    def _build_z3_template(self, abstract_rule):
        return abstract_rule.replace("=", "==").replace("**", "^")

    def _generate_name(self, rule, domain):
        domain_upper = domain.upper()
        if "+" in rule:
            return f"{domain_upper}_ADDITION"
        if "-" in rule and "*" in rule:
            return f"{domain_upper}_DEDUCTION"
        if "*" in rule:
            return f"{domain_upper}_PRODUCT"
        if "/" in rule:
            return f"{domain_upper}_RATIO"
        return f"{domain_upper}_RULE"


class LearningEngine:
    def __init__(self, neural_perceiver, knowledge_base):
        self.perceiver = neural_perceiver
        self.knowledge = knowledge_base
        self.concept_extractor = ConceptExtractor()
        self.updater = ProofGuidedWeightUpdater()
        self.learning_rate = 0.01

    def learn(
        self,
        perception: PerceptionMap,
        plan: ReasoningPlan,
        verification: VerificationResult
    ) -> LearningResult:

        if verification.valid and verification.proof_trace:
            return self._learn_from_proof(perception, plan, verification)
        else:
            return self._learn_from_failure(perception, plan, verification)

    def _learn_from_proof(self, perception, plan, verification):
        # Extract concept
        new_concept = self.concept_extractor.extract(
            perception,
            plan.candidate_solution,
            verification.proof_trace
        )

        # Store or reinforce
        if new_concept.name in self.knowledge.concept_library.concepts:
            self.knowledge.concept_library.update_strength(
                new_concept.name, self.learning_rate
            )
            learned = None
            reinforced = new_concept
        else:
            self.knowledge.concept_library.add(new_concept)
            self.knowledge.ontology.integrate(new_concept)
            learned = new_concept
            reinforced = None

        # Update neural weights from proof
        weight_update = self.updater.compute_update(
            perception,
            verification.proof_trace,
            "strengthen",
            self.learning_rate
        )
        self.perceiver.update_weights_from_proof(weight_update)

        # Store episode
        episode = Episode(
            input_summary=perception.operation_hint,
            domain=perception.domain,
            solution=plan.candidate_solution,
            concepts_used=plan.concepts_used,
            was_verified=True
        )
        self.knowledge.episode_memory.store(episode)

        return LearningResult(
            new_concept=learned,
            reinforced_concept=reinforced,
            weight_updates=weight_update,
            episode_stored=episode,
            failure_logged=None
        )

    def _learn_from_failure(self, perception, plan, verification):
        weight_update = self.updater.compute_update(
            perception,
            verification.counterexample or {},
            "weaken",
            self.learning_rate * 0.5
        )
        self.perceiver.update_weights_from_proof(weight_update)

        return LearningResult(
            new_concept=None,
            reinforced_concept=None,
            weight_updates=weight_update,
            episode_stored=None,
            failure_logged=verification.correction_hint
        )
```

---

## B.10 LAYER 6: RESPONSE BRIDGE

```python
# hsci/response/response_bridge.py
# IMPLEMENT full ResponseBridge as specified
# in Response Bridge prompt document.
# Key requirements:
# - Domain-aware formatters (finance, physics, algebra, geometry, etc.)
# - Always show reasoning trace step by step
# - Always show verification status honestly
# - Handle follow-up questions with conversation context
# - Currency symbols for finance domain
# - Physics units in responses
# - ✓ for verified, ⚠ for unverified, ✗ for cannot solve
# - Never empty response
# - Suggest teach: command when cannot solve
```

---

## B.11 SELF-PLAY ENGINE

```python
# hsci/self_play/engine.py
from threading import Thread
import time
import random

class HypothesisBuilder:
    """Builds novel hypotheses from existing concepts."""

    def build_from_concepts(self, concepts: List[Concept]) -> PerceptionMap:
        # Combine 2 concepts into a new problem
        # Example: PERCENTAGE + ADDITION → "X% of A plus B = ?"
        # Returns as PerceptionMap for standard processing
        pass  # IMPLEMENT

    def build_for_concept(
        self,
        concept: Concept,
        difficulty: float
    ) -> PerceptionMap:
        # Generate practice problem targeting this specific concept
        # Difficulty 0.0 = simple values, 1.0 = complex multi-step
        pass  # IMPLEMENT


class SelfPlayEngine:
    """
    BACKGROUND ENGINE: Autonomous Knowledge Discovery
    Runs continuously. Makes HSCI smarter without user interaction.
    This is HSCI's equivalent of human "thinking" and "studying".
    """

    def __init__(self, knowledge_base, reasoning_engine,
                 z3_verifier, learning_engine):
        self.knowledge = knowledge_base
        self.reasoning = reasoning_engine
        self.verifier = z3_verifier
        self.learning = learning_engine
        self.running = False
        self.cycles_completed = 0
        self.new_concepts_discovered = 0

    def start(self):
        self.running = True
        Thread(target=self._run_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _run_loop(self):
        while self.running:
            try:
                # 1. Generate hypothesis
                concepts = self.knowledge.concept_library.sample(n=2)
                if len(concepts) < 2:
                    time.sleep(1)
                    continue

                hypothesis = HypothesisBuilder().build_from_concepts(concepts)
                if hypothesis is None:
                    time.sleep(0.1)
                    continue

                # 2. Reason
                knowledge_result = self.knowledge.query(hypothesis)
                plan = self.reasoning.reason(hypothesis, knowledge_result)

                # 3. Verify
                result = self.verifier.verify(
                    plan.candidate_solution,
                    hypothesis,
                    plan.primary_concept
                )

                # 4. Learn
                learning_result = self.learning.learn(
                    hypothesis, plan, result
                )

                if learning_result.new_concept:
                    self.new_concepts_discovered += 1

                # 5. Target weak concepts
                weak_concepts = self.knowledge.concept_library.get_weakest(n=2)
                for concept in weak_concepts:
                    practice = HypothesisBuilder().build_for_concept(
                        concept, difficulty=concept.strength
                    )
                    if practice:
                        self._solve_and_learn(practice)

                self.cycles_completed += 1
                time.sleep(0.05)  # prevent CPU monopolization

            except Exception as e:
                time.sleep(0.1)
                continue

    def _solve_and_learn(self, perception):
        try:
            knowledge_result = self.knowledge.query(perception)
            plan = self.reasoning.reason(perception, knowledge_result)
            result = self.verifier.verify(
                plan.candidate_solution, perception, plan.primary_concept
            )
            self.learning.learn(perception, plan, result)
        except Exception:
            pass

    @property
    def stats(self):
        return {
            "cycles": self.cycles_completed,
            "new_concepts": self.new_concepts_discovered,
            "total_concepts": len(
                self.knowledge.concept_library.concepts
            )
        }
```

---

## B.12 MAIN RIR LOOP ORCHESTRATOR

```python
# hsci/core/rir_loop.py

class RIRLoop:
    """
    Main Orchestrator — Reinforced Intuitive Reasoning Loop
    Coordinates all 7 layers + background self-play.
    Single entry point for all interactions.
    """

    def __init__(self, use_llm: bool = True):
        print("Initializing HSCI...")

        # Layer 0
        self.language_bridge = LanguageBridge(use_llm=use_llm)

        # Layer 1
        self.perceiver = NeuralPerceiver()

        # Layer 2
        self.knowledge_base = KnowledgeBase()

        # Layer 3
        self.reasoning_engine = ReasoningEngine()

        # Layer 4
        self.verifier = Z3VerificationEngine()

        # Layer 5
        self.learning_engine = LearningEngine(
            self.perceiver,
            self.knowledge_base
        )

        # Layer 6
        self.response_bridge = ResponseBridge()

        # Background
        self.self_play = SelfPlayEngine(
            self.knowledge_base,
            self.reasoning_engine,
            self.verifier,
            self.learning_engine
        )
        self.self_play.start()

        print("HSCI initialized. Self-play engine running.")
        print(f"Concepts loaded: {len(self.knowledge_base.concept_library.concepts)}")

    def process(self, raw_input: str) -> str:
        """
        Complete pipeline: raw human input → natural language response.
        This is the ONLY public method needed to use HSCI.
        """

        # LAYER 0: Understand language
        structured = self.language_bridge.parse(raw_input)

        # Handle follow-up context
        structured = self.response_bridge.conversation_manager\
            .resolve_followup(raw_input, structured.__dict__)

        # LAYER 1: Perceive structure
        if not isinstance(structured, StructuredInput):
            structured = self.language_bridge.spacy_parser\
                ._dict_to_structured(structured)
        perception = self.perceiver.perceive(structured)

        # LAYER 2: Retrieve knowledge
        knowledge = self.knowledge_base.query(perception)

        # LAYER 3: Initial reasoning
        plan = self.reasoning_engine.reason(perception, knowledge)

        # LAYERS 3+4: CEGIS repair loop
        verification = None
        for attempt in range(5):
            verification = self.verifier.verify(
                plan.candidate_solution,
                perception,
                plan.primary_concept
            )

            if verification.valid:
                break

            # Repair using counterexample
            if verification.counterexample:
                plan = self.reasoning_engine.repair(
                    plan,
                    verification.counterexample,
                    verification.correction_hint
                )

        # LAYER 5: Learn regardless of outcome
        learning_result = self.learning_engine.learn(
            perception, plan, verification
        )

        # Build final output
        answer = self._extract_answer(verification, perception)
        output = FinalOutput(
            answer=answer,
            is_verified=verification.valid if verification else False,
            confidence=verification.confidence if verification else 0.0,
            concepts_used=plan.concepts_used,
            reasoning_trace=self._build_trace(perception, plan, verification),
            proof=verification.proof_trace if verification else None,
            new_concept_learned=learning_result.new_concept.name
                if learning_result and learning_result.new_concept else None,
            counterexample=verification.counterexample if verification else None,
            correction_hint=verification.correction_hint if verification else None
        )

        # LAYER 6: Generate natural language response
        response = self.response_bridge.generate(
            hsci_output=output,
            original_input=raw_input,
            structured_input=structured.__dict__
                if hasattr(structured, '__dict__') else structured
        )

        return response

    def _extract_answer(self, verification, perception):
        if not verification or not verification.valid:
            return None
        if verification.proof_trace:
            unknowns = perception.unknown_entities
            for unknown in unknowns:
                val = verification.proof_trace.variable_assignments.get(unknown)
                if val is not None:
                    return val
        return None

    def _build_trace(self, perception, plan, verification):
        trace = []
        entities_str = ", ".join(
            f"{k}={v.value}" for k, v in perception.entities.items()
        )
        trace.append(f"Given values: {entities_str}")

        for concept_name in plan.concepts_used:
            trace.append(f"Applied concept: {concept_name}")

        if plan.candidate_solution:
            trace.append(f"Solution: {plan.candidate_solution}")

        if verification and verification.proof_trace:
            for name, val in \
                    verification.proof_trace.variable_assignments.items():
                trace.append(f"Computed: {name} = {val}")

        return trace

    @property
    def knowledge_stats(self):
        return {
            "total_concepts": len(
                self.knowledge_base.concept_library.concepts
            ),
            "self_play_cycles": self.self_play.cycles_completed,
            "new_concepts_discovered": self.self_play.new_concepts_discovered
        }
```

---

## B.13 CLI INTERFACE

```python
# hsci/cli/main.py

import sys
from hsci.core.rir_loop import RIRLoop


def main():
    print("=" * 60)
    print("HSCI — Hyper-Symbolic Cognitive Intelligence")
    print("Neurosymbolic AI with Mathematical Verification")
    print("=" * 60)
    print()

    hsci = RIRLoop(use_llm=True)

    print("Ready. Type your question or:")
    print("  'stats'  — show knowledge base statistics")
    print("  'teach: <domain> | <concept> | <axiom>'")
    print("  'quit'   — exit")
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("Shutting down self-play engine...")
                hsci.self_play.stop()
                break

            if user_input.lower() == "stats":
                stats = hsci.knowledge_stats
                print(f"\nKnowledge Base Statistics:")
                print(f"  Concepts learned: {stats['total_concepts']}")
                print(f"  Self-play cycles: {stats['self_play_cycles']}")
                print(f"  New concepts discovered: "
                      f"{stats['new_concepts_discovered']}")
                print()
                continue

            response = hsci.process(user_input)
            print(f"\nHSCI: {response}\n")

        except KeyboardInterrupt:
            print("\nShutting down...")
            hsci.self_play.stop()
            break
        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == "__main__":
    main()
```

---

## B.14 TRAINING PIPELINE

```python
# hsci/training/math_trainer.py

MATH_PHASE_1 = [
    # Arithmetic
    ("2 + 3", 5),
    ("10 + 7", 17),
    ("15 - 8", 7),
    ("4 * 6", 24),
    ("20 / 4", 5),
    # Percentage
    ("20% of 500", 100),
    ("15% of 200", 30),
    # Equations
    ("x + 5 = 10, find x", {"x": 5}),
    ("2x = 14, find x", {"x": 7}),
    # Multi-step finance
    ("salary 5000 tax 20% find take-home", {"take_home": 4000}),
    ("price 1000 discount 15% find final", {"final": 850}),
    ("principal 10000 rate 8% 2 years find interest",
     {"interest": 1600}),
]

# TRANSFER TEST — never seen during training
TRANSFER_TESTS = [
    ("velocity 20 ms time 5s find distance", {"distance": 100}),
    ("force 50N mass 10kg find acceleration", {"acceleration": 5}),
    ("monthly salary 8000 deductions 25% find annual take-home",
     {"annual_take_home": 72000}),
]

def run_training(hsci_system, examples):
    results = {"correct": 0, "total": len(examples)}
    for problem, expected in examples:
        response = hsci_system.process(problem)
        print(f"Problem: {problem}")
        print(f"Response: {response}")
        print()
    return results
```

---

## B.15 SETUP AND INSTALLATION

```bash
# Create project
mkdir hsci && cd hsci
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install z3-solver
pip install torch torchvision torchaudio
pip install torch-geometric
pip install spacy
python -m spacy download en_core_web_sm
pip install networkx
pip install ollama
pip install pytest pytest-cov
pip install rich loguru

# Install Ollama for LLM parser
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull phi3:mini

# Run HSCI
python -m hsci.cli.main

# Run tests
pytest hsci/tests/ -v --cov=hsci
```

---

## B.16 IMPLEMENTATION ORDER — EXACT SEQUENCE

```
WEEK 1: Foundation
□ data_types.py — ALL dataclasses defined
□ z3_templates.py — 12 core templates working
□ z3_verifier.py — verify() working
□ TEST: verify("2+3=5") → valid=True
□ TEST: verify("2+3=6") → valid=False + counterexample

WEEK 2: Language
□ spacy_parser.py — full implementation
□ llm_parser.py — Ollama integration
□ bridge.py — routing logic
□ TEST: all language bridge tests passing

WEEK 3: Knowledge + Perception
□ concept_library.py — seed concepts + CRUD
□ ontology_graph.py — basic graph
□ episode_memory.py
□ perceiver.py — GNN encoder
□ TEST: perceive() returns correct PerceptionMap

WEEK 4: Reasoning
□ htn_planner.py — decomposition rules
□ concept_composer.py — direct + analogical
□ solution_builder.py — expression building
□ reasoning_engine.py — full reason()
□ TEST: reason about arithmetic end-to-end

WEEK 5: Learning (THE CORE CONTRIBUTION)
□ concept_extractor.py — abstract rule extraction
□ proof_guided_updater.py — weight updates from proofs
□ learning_engine.py — full learn() cycle
□ TEST: train on 5 examples, verify concept extracted
□ TEST: neural weights changed after proof

WEEK 6: Response Bridge
□ formatters.py — all domain formatters
□ template_engine.py — full generation
□ conversation_manager.py — follow-up handling
□ response_bridge.py — full integration
□ TEST: all response bridge tests passing

WEEK 7: Integration
□ rir_loop.py — full 7-layer pipeline
□ self_play/engine.py — background learning
□ cli/main.py — interactive interface
□ TEST: end-to-end on all math training examples

WEEK 8: Transfer + Evaluation
□ Run transfer tests (physics, finance never trained)
□ Measure: >80% transfer accuracy
□ Self-play running, concepts growing
□ Full test suite: 50+ tests all passing

WEEK 9-10: Polish + Paper
□ Performance optimization
□ Edge cases handled
□ Documentation complete
□ Begin research paper draft
```

---

## B.17 SUCCESS CRITERIA — MUST ALL PASS

```
LAYER 0 (Language Bridge):
□ Parses any finance/math/physics input correctly
□ Never produces final answers
□ Confidence correctly scored
□ Follow-ups resolved with context

LAYER 1 (Perceiver):
□ Entity graph correctly built
□ Intent correctly classified
□ Weights update after proof

LAYER 2 (Knowledge):
□ Seed concepts loaded
□ New concepts stored correctly
□ Analogical matching working

LAYER 3 (Reasoning):
□ Problems decomposed into sub-goals
□ Concepts correctly assigned
□ Candidate solutions built

LAYER 4 (Verification):
□ Z3 proves correct answers
□ Z3 disproves wrong answers
□ Counterexamples extracted
□ CEGIS repair loop functional

LAYER 5 (Learning):
□ Concepts extracted from proofs
□ Neural weights updated from proofs only
□ Episodes stored
□ New concepts appear after training

LAYER 6 (Response):
□ Natural language generated
□ Reasoning trace shown
□ Verification status honest
□ Follow-up context used

SELF-PLAY:
□ Running in background thread
□ Cycles completing without errors
□ New concepts being discovered

END-TO-END:
□ Math training: >95% accuracy
□ Transfer test: >80% accuracy
□ No crashes on edge cases
□ Full reasoning trace in every response
```

---

## B.18 CRITICAL NON-NEGOTIABLE RULES

```
1. NEVER return unverified answer as FINAL OUTPUT
   Always mark clearly if not Z3-proven

2. NEVER update neural weights except through ProofGuidedWeightUpdater
   No optimizer.step(). No standard loss functions.

3. NEVER store specific values in ConceptLibrary
   Always abstract: "result = a + b" not "5 = 2 + 3"

4. ALWAYS run CEGIS repair loop minimum 3 times before giving up

5. ALWAYS run self-play engine in background from startup

6. ALWAYS show reasoning trace in every response

7. NEVER call external APIs for reasoning or answering
   Everything runs locally

8. ALWAYS be honest about uncertainty
   ✓ = proven, ⚠ = estimated, ✗ = cannot solve
```

---

## APPENDIX: WHAT THIS SYSTEM ACHIEVES

When fully built, HSCI:

```
✓ Understands natural language (Layer 0)
✓ Perceives problem structure (Layer 1)
✓ Retrieves relevant knowledge (Layer 2)
✓ Reasons to find solutions (Layer 3)
✓ Proves answers mathematically (Layer 4)
✓ Learns from every interaction (Layer 5)
✓ Responds in natural language (Layer 6)
✓ Keeps learning autonomously (Self-play)
✓ Runs fully locally, no cloud
✓ Explains every decision
✓ Never hallucinates verified answers
✓ Transfers knowledge across domains
✓ Gets smarter continuously
```

This is not a better LLM.
This is a different kind of intelligence entirely.
Provably correct. Continuously learning. Fully explainable.
