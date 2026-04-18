from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
from uuid import uuid4

# ─────────────────────────────────────────────
# CORE TYPES
# ─────────────────────────────────────────────

Graph = Dict[str, Any]

@dataclass
class Expression:
    value: Any
    concepts_used: List[str]

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
    entity_graph: Graph
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
    candidate_solution: Expression
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

    def feature_relevance(self, feature_name: str) -> float:
        return 1.0 if feature_name in self.concepts_applied else 0.1

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
    new_concept: Optional[Concept] = None
    reinforced_concept: Optional[Concept] = None
    weight_updates: Optional[WeightUpdate] = None
    episode_stored: Optional[Episode] = None
    failure_logged: Optional[str] = None

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
    hsci_response: str
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
