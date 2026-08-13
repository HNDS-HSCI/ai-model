from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from datetime import datetime
from uuid import uuid4

# ─────────────────────────────────────────────
# CORE TYPES
# ─────────────────────────────────────────────

Graph = Dict[str, Any]

@dataclass
class InputSignal:
    raw_text: str
    structured_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = "default_session"

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
# HTN DOMAIN TYPES (HP4A-01)
# ─────────────────────────────────────────────

class TaskType(Enum):
    COMPOUND  = "COMPOUND"   # Requires HTN decomposition via Method selection
    PRIMITIVE = "PRIMITIVE"  # Executable operator

@dataclass
class Task:
    id: str
    name: str
    task_type: TaskType
    parameters: Dict[str, Any] = field(default_factory=dict)
    axiom_type: Optional[AxiomType] = None

@dataclass
class Precondition:
    predicate: str                  # e.g., "HAS_REQUIRED_ENTITIES", "Z3_SATISFIABLE"
    required_state: Any = None      # expected state value or entity list
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Postcondition:
    effect_key: str                 # e.g., "EQUATION_BUILT", "STATE_UPDATED"
    resulting_state: Any = None
    parameters: Dict[str, Any] = field(default_factory=dict)

class MethodSource(Enum):
    CANONICAL = "canonical"
    LEARNED   = "learned"

@dataclass
class Method:
    id: str
    target_task_name: str           # Name of the compound task this method satisfies
    preconditions: List[Precondition] = field(default_factory=list)
    subtasks: List[Task] = field(default_factory=list)
    cost: float = 1.0
    description: str = ""
    source: MethodSource = MethodSource.CANONICAL


@dataclass
class Operator:
    id: str
    primitive_task_name: str        # Name of the primitive task this operator executes
    preconditions: List[Precondition] = field(default_factory=list)
    postconditions: List[Postcondition] = field(default_factory=list)
    execution_handler: str = ""     # Associated solver or handler name
    description: str = ""

@dataclass
class PlanningFailure:
    failed_task_id: str
    failed_task_name: str
    attempted_methods: List[str] = field(default_factory=list)
    failed_precondition: Optional[Precondition] = None
    z3_counterexample: Optional[Dict[str, Any]] = None
    depth_reached: int = 0
    reason: str = "UNSATISFIABLE_PRECONDITION"

@dataclass
class PlanningContext:
    """
    Request-scoped immutable snapshot of planning-relevant state extracted from WorkingMemory.
    Provides safe fact lookups, entity bindings, active concepts, and intent metadata for HTNPlanner.
    """
    facts: Dict[str, Any] = field(default_factory=dict)
    entities: Dict[str, Any] = field(default_factory=dict)
    active_concepts: List[str] = field(default_factory=list)
    intent: Optional[str] = None
    request_id: str = ""
    session_id: str = ""

    def get_fact(self, key: str, default: Any = None) -> Any:
        return self.facts.get(key, default)

    def has_fact(self, key: str) -> bool:
        return key in self.facts

    def to_dict(self) -> Dict[str, Any]:
        """Flatten facts, entity values, and concepts into a unified dictionary representation."""
        unified = dict(self.facts)
        for k, v in self.entities.items():
            if hasattr(v, "value"):
                unified[k] = v.value
            else:
                unified[k] = v
        for concept in self.active_concepts:
            unified[f"CONCEPT_{concept}"] = True
        if self.intent:
            unified["INTENT"] = self.intent
        return unified

# ─────────────────────────────────────────────
# PHASE 4B REFLECTION DATA MODELS
# ─────────────────────────────────────────────

class ReflectionFailureType(Enum):
    PRECONDITION_UNSAT                = "PRECONDITION_UNSAT"
    NO_METHOD                         = "NO_METHOD"
    DECOMPOSITION_CYCLE               = "DECOMPOSITION_CYCLE"
    MAX_DEPTH_EXCEEDED                = "MAX_DEPTH_EXCEEDED"
    STRUCTURAL_DECOMPOSITION_FAILURE  = "STRUCTURAL_DECOMPOSITION_FAILURE"
    SOLVER_UNSAT                      = "SOLVER_UNSAT"
    SOLVER_TIMEOUT                    = "SOLVER_TIMEOUT"
    SOLUTION_VERIFICATION_FAILURE     = "SOLUTION_VERIFICATION_FAILURE"
    UNSUPPORTED_TASK                  = "UNSUPPORTED_TASK"

@dataclass
class ReflectionResult:
    """
    Deterministic, typed failure diagnosis artifact produced by ReflectionEngine.
    """
    reflection_id: str
    request_id: str
    failure_category: ReflectionFailureType
    failed_stage: str                   # "PLANNING", "SOLUTION_VERIFICATION", "SOLVER"
    failed_task_id: str = ""
    failed_task_name: str = ""
    attempted_methods: List[str] = field(default_factory=list)
    failed_precondition: Optional[Precondition] = None
    counterexample: Optional[Dict[str, Any]] = None
    depth_reached: int = 0
    root_cause: str = ""
    correction_hint: str = ""
    retry_recommended: bool = False

# ─────────────────────────────────────────────
# PHASE 4C SKILL & METHOD LEARNING DATA MODELS
# ─────────────────────────────────────────────

class SkillCandidateStatus(Enum):
    PROPOSED    = "PROPOSED"
    VALIDATING  = "VALIDATING"
    VERIFIED    = "VERIFIED"
    REJECTED    = "REJECTED"
    ACTIVE      = "ACTIVE"

@dataclass
class SkillCandidate:
    """
    Typed, declarative artifact representing a proposed HTN Method compiled from verified execution.
    Must undergo strict multi-stage validation (structural, formal, replay) before MethodRegistry activation.
    """
    candidate_id: str
    source_request_id: str
    target_task_name: str
    proposed_preconditions: List[Precondition] = field(default_factory=list)
    proposed_subtasks: List[Task] = field(default_factory=list)
    source_reflection_id: Optional[str] = None
    provenance_trace: List[str] = field(default_factory=list)
    status: SkillCandidateStatus = SkillCandidateStatus.PROPOSED
    validation_failures: List[str] = field(default_factory=list)
    cost: float = 1.0

@dataclass
class SkillLearningResult:
    """
    Structured outcome of a SkillLearningEngine evaluation or skill acquisition attempt.
    """
    decision: str                       # "NO_LEARNING", "PROPOSE_SKILL", "SKILL_ACTIVATED", "SKILL_REJECTED"
    candidate_id: Optional[str] = None
    activated_method_id: Optional[str] = None
    validation_passed: bool = False
    reason: str = ""

@dataclass
class GraphPlanCandidate:
    """
    SCG2-03: Request-local representation of a graph-composed candidate procedural chain.
    Remains transactional and request-local until verified by Z3.
    """
    candidate_id: str
    root_task_name: str
    ordered_subtasks: List[Task] = field(default_factory=list)
    source_skill_ids: List[str] = field(default_factory=list)
    source_method_ids: List[str] = field(default_factory=list)
    depth: int = 1
    estimated_cost: float = 1.0


@dataclass
class PlanningTrace:
    """
    SCG3-01: Request-local planning trace capturing exact candidate and method provenance.
    Enforces exact candidate outcome attribution without global telemetry leakage.
    """
    selected_candidate_id: Optional[str] = None
    executed_method_ids: List[str] = field(default_factory=list)
    executed_graph_node_ids: List[str] = field(default_factory=list)
    graph_fallback_used: bool = False



# ─────────────────────────────────────────────
# PHASE 5A NEUROSYMBOLIC SEMANTIC GROUNDING & AST
# ─────────────────────────────────────────────

class ASTNodeType(Enum):
    VARIABLE  = "VARIABLE"
    CONSTANT  = "CONSTANT"
    BINARY_OP = "BINARY_OP"

@dataclass
class ASTNode:
    """Base class for typed declarative symbolic AST nodes."""
    node_type: ASTNodeType


@dataclass
class VariableNode(ASTNode):
    name: str

    def __init__(self, name: str):
        super().__init__(node_type=ASTNodeType.VARIABLE)
        self.name = name

@dataclass
class ConstantNode(ASTNode):
    value: Union[int, float, bool, str]

    def __init__(self, value: Union[int, float, bool, str]):
        super().__init__(node_type=ASTNodeType.CONSTANT)
        self.value = value

class BinaryOperator(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    EQ  = "=="
    GT  = ">"
    LT  = "<"
    GTE = ">="
    LTE = "<="
    AND = "AND"
    OR  = "OR"

@dataclass
class BinaryOpNode(ASTNode):
    op: BinaryOperator
    left: ASTNode
    right: ASTNode

    def __init__(self, op: BinaryOperator, left: ASTNode, right: ASTNode):
        super().__init__(node_type=ASTNodeType.BINARY_OP)
        self.op = op
        self.left = left
        self.right = right

@dataclass
class RelationTriple:
    subject: str
    relation: str                   # "HAS", "GREATER_THAN", "LESS_THAN", "EQUALS", "REQUIRES"
    object: Union[str, int, float]

@dataclass
class SemanticIR:
    """
    Canonical, inspectable Intermediate Representation produced by SemanticCompiler.
    Bridged directly to HTN root tasks, Z3 expressions, and PlanningContext.
    """
    raw_text: str
    entities: Dict[str, Any] = field(default_factory=dict)
    relations: List[RelationTriple] = field(default_factory=list)
    ast_constraints: List[ASTNode] = field(default_factory=list)
    target_goal: str = ""
    domain: str = "general"
    intent: Optional[str] = None
    confidence: float = 1.0
    provenance_spans: Dict[str, str] = field(default_factory=dict)

@dataclass
class SemanticCompilationFailure:
    failed_input: str
    reason: str
    category: str                   # "UNKNOWN_RELATION", "UNSUPPORTED_STRUCTURE", "AMBIGUOUS_ENTITY"






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
    semantic_ir: Optional[Any] = None # Canonical SemanticIR preserved from SemanticCompiler (NSG-3)

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
    domain: str = "general"
    operation_hint: str = ""
    semantic_ir: Optional[Any] = None # Canonical SemanticIR preserved from LanguageBridge (NSG-3)

# ─────────────────────────────────────────────
# LAYER 2: KNOWLEDGE TYPES
# ─────────────────────────────────────────────

@dataclass(unsafe_hash=True)
class Concept:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    namespace: str = "general"
    version: int = 1
    status: str = "ACTIVE"
    aliases: List[str] = field(default_factory=list, hash=False)
    axiom_type: AxiomType = AxiomType.REDUCTION
    abstract_rule: str = ""       # "result = a + b"
    z3_template: str = ""         # Z3-compatible constraint string
    domain: str = "arithmetic"
    learned_from_domains: List[str] = field(default_factory=list, hash=False)
    strength: float = 0.5         # 0.0 to 1.0
    proof_count: int = 0
    created_at: datetime = field(default_factory=datetime.now, hash=False)
    last_used: datetime = field(default_factory=datetime.now, hash=False)
    generalizes_to: List[str] = field(default_factory=list, hash=False)
    required_entities: List[str] = field(default_factory=list, hash=False)
    optional_entities: List[str] = field(default_factory=list, hash=False)
    z3_verified: bool = False

@dataclass
class Episode:
    id: str = field(default_factory=lambda: str(uuid4()))
    input: Optional[PerceptionMap] = None # Added for test compatibility
    input_summary: str = ""
    domain: str = ""
    solution: Any = None # Changed from str to Any for Expression
    proof: Optional['ProofTrace'] = None # Added for test compatibility
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

@dataclass(unsafe_hash=True)
class SubGoal:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "" # Added for test compatibility
    description: str = ""
    required_entities: List[str] = field(default_factory=list, hash=False)
    target_entity: str = ""
    axiom_type: AxiomType = AxiomType.REDUCTION

@dataclass
class ReasoningPlan:
    sub_goals: List[SubGoal]
    concept_assignments: Dict[SubGoal, Concept] # Changed from str to SubGoal for test compatibility
    candidate_solution: Expression
    concepts_used: List[str] = field(default_factory=list) # Added default
    primary_concept: Optional[Concept] = None # Added default
    composition_order: List[Any] = field(default_factory=list) # Added for test compatibility
    perception: Optional[PerceptionMap] = None
    knowledge: Optional[KnowledgeResult] = None
    planning_trace: Optional[PlanningTrace] = None

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

    @property
    def variables(self):
        return self.variable_assignments

    def __init__(self, steps, variable_assignments=None, concepts_applied=None, structural_pattern=None, version=0, variables=None):
        self.steps = steps
        self.variable_assignments = variable_assignments or variables or {}
        self.concepts_applied = concepts_applied or []
        self.structural_pattern = structural_pattern or ""
        self.version = version

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
    direction_hint: str = ""       # Phase 3: AxiomType.value used, passed to perceiver

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
