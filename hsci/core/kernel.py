import logging
import uuid
import time
import z3
from typing import Dict, List, Optional, Any, Tuple, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from hsci.core.config import SystemConfig
from hsci.core.data_types import (
    FinalOutput, AxiomType, ProofTrace, VerificationStatus
)

# ─────────────────────────────────────────────
# CUSTOM EXCEPTIONS
# ─────────────────────────────────────────────

class HSCIError(Exception):
    """Base exception for all HSCI system errors."""
    pass

class ValidationError(HSCIError):
    """Raised when request validation, input tokenization, or schema constraints fail."""
    pass

class SolverError(HSCIError):
    """Raised when an internal solver plugin encounters a runtime error."""
    pass

class UKMError(HSCIError):
    """Raised when database persistent locks or transactions fail."""
    pass

class VerificationError(HSCIError):
    """Raised when Z3 verification fails or encounters a timeout."""
    pass

# ─────────────────────────────────────────────
# INTERFACES
# ─────────────────────────────────────────────

from hsci.core.working_memory import WorkingMemory, IWorkingMemory


class CognitiveContext:
    """
    Transaction-scoped context manager tracking session context and isolated resources.
    Conforms to Z3 Context deallocation and thread isolation guidelines.
    """
    def __init__(self, request_id: str, session_id: str, stimulus: str):
        self.request_id: str = request_id
        self.session_id: str = session_id
        self.stimulus: str = stimulus
        self.working_memory: WorkingMemory = WorkingMemory(
            request_id=request_id, session_id=session_id, stimulus=stimulus
        )
        self.z3_context: Optional[z3.Context] = None
        self.logger: logging.Logger = logging.getLogger(f"HSCI.Context.{request_id}")
        self.is_active: bool = False

    def __enter__(self) -> 'CognitiveContext':
        self.is_active = True
        # Spawning thread-isolated Z3 solver context
        self.z3_context = z3.Context()
        self.logger.debug(f"[RequestID: {self.request_id}] CognitiveContext initialized and Z3 context spawned.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.is_active = False
        # Explicitly clean up WorkingMemory references
        if self.working_memory is not None:
            self.working_memory.dispose()
        # Guarantee resource deallocation to prevent python memory leaks
        if self.z3_context is not None:
            del self.z3_context
            self.z3_context = None
        self.logger.debug(f"[RequestID: {self.request_id}] CognitiveContext deallocated and Z3 resources released.")


class IStageExecutor(ABC):
    """
    Standard interface for all 10 stages of the BrainKernel execution pipeline.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def execute(self, context: CognitiveContext) -> None:
        """
        Processes working memory structures inside the Context.
        """
        pass


class ISolverPlugin(ABC):
    """
    Standard interface for all deterministic domain-specific solvers.
    """
    @property
    @abstractmethod
    def domain(self) -> str:
        pass

    @abstractmethod
    def can_solve(self, subgoal_id: str, axiom_type: AxiomType) -> bool:
        pass

    @abstractmethod
    def solve(self, subgoal_id: str, context: CognitiveContext) -> Any:
        pass

# ─────────────────────────────────────────────
# EVENT BUS & NOTIFICATIONS
# ─────────────────────────────────────────────

class EventBus:
    """
    Cognitive Operating System Event Bus facilitating decoupled lifecycle tracking.
    """
    def __init__(self):
        self._listeners: Dict[str, List[Callable[[CognitiveContext], None]]] = {
            "on_start": [],
            "on_stage_start": [],
            "on_stage_success": [],
            "on_stage_failure": [],
            "on_success": [],
            "on_stop": []
        }

    def subscribe(self, event_name: str, callback: Callable[[CognitiveContext], None]) -> None:
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def emit(self, event_name: str, context: CognitiveContext) -> None:
        if event_name in self._listeners:
            for callback in self._listeners[event_name]:
                try:
                    callback(context)
                except Exception as e:
                    logging.error(f"[EventBus] Error executing subscriber callback: {e}")

# ─────────────────────────────────────────────
# REGISTRIES
# ─────────────────────────────────────────────

class StageRegistry:
    """
    Maintains and orders the 10-stage execution pipeline.
    """
    def __init__(self):
        self._stages: List[IStageExecutor] = []

    def register_stage(self, stage: IStageExecutor) -> None:
        self._stages.append(stage)

    def get_stages(self) -> List[IStageExecutor]:
        return self._stages


class SolverRegistry:
    """
    Dispatches task goals dynamically to registered domain-specific solvers.
    """
    def __init__(self):
        self._solvers: List[ISolverPlugin] = []

    def register_solver(self, solver: ISolverPlugin) -> None:
        self._solvers.append(solver)

    def dispatch(self, subgoal_id: str, axiom_type: AxiomType, context: CognitiveContext) -> Any:
        for solver in self._solvers:
            if solver.can_solve(subgoal_id, axiom_type):
                context.logger.info(f"[RequestID: {context.request_id}] Dispatched subgoal '{subgoal_id}' to solver '{solver.domain}'")
                return solver.solve(subgoal_id, context)
        raise SolverError(f"No solver registered capable of solving subgoal: '{subgoal_id}' with type '{axiom_type.value}'")

# ─────────────────────────────────────────────
# SHELL STAGE EXECUTORS (PLACEHOLDERS)
# ─────────────────────────────────────────────

class ShellStage(IStageExecutor):
    def __init__(self, stage_name: str):
        self._name = stage_name

    @property
    def name(self) -> str:
        return self._name

    def execute(self, context: CognitiveContext) -> None:
        context.logger.debug(f"[RequestID: {context.request_id}] Running shell stage: {self._name}")
        # Simulated shell processing logic
        time.sleep(0.001)

# ─────────────────────────────────────────────
# THE BRAIN KERNEL ORCHESTRATOR
# ─────────────────────────────────────────────

class BrainKernel:
    """
    The orchestrator of the 10-stage Reinforced Intuitive Reasoning (RIR) pipeline.
    """
    def __init__(self, config: SystemConfig):
        self.config: SystemConfig = config
        self.stage_registry: StageRegistry = StageRegistry()
        self.solver_registry: SolverRegistry = SolverRegistry()
        self.event_bus: EventBus = EventBus()
        self.logger: logging.Logger = logging.getLogger("HSCI.BrainKernel")
        self._is_initialized: bool = False

        # Pre-emption Teach Gate Hook
        self._teach_preempt_callback: Optional[Callable[[str], Optional[str]]] = None

    def set_teach_preempt_handler(self, handler: Callable[[str], Optional[str]]) -> None:
        """
        Installs the pre-emption gate (Stage -1) called before LanguageBridge.
        """
        self._teach_preempt_callback = handler

    def initialize(self) -> None:
        """
        Initializes resources, loads pipelines, and sets registries.
        """
        if self._is_initialized:
            return
        
        self.logger.info("Initializing BrainKernel (v4.0.0)...")
        
        # Load the 10 stages in sequence
        self.stage_registry.register_stage(ShellStage("Stage 0: LanguageBridge"))
        self.stage_registry.register_stage(ShellStage("Stage 0.5: UnderstandingEngine"))
        self.stage_registry.register_stage(ShellStage("Stage 1: NeuralPerceiver"))
        self.stage_registry.register_stage(ShellStage("Stage 1.5: MentalModelEngine"))
        self.stage_registry.register_stage(ShellStage("Stage 2: ConceptActivationEngine"))
        self.stage_registry.register_stage(ShellStage("Stage 2.5: SkillMemory"))
        self.stage_registry.register_stage(ShellStage("Stage 3: SolverRegistry & ReasoningEngine"))
        self.stage_registry.register_stage(ShellStage("Stage 4: Z3VerificationEngine"))
        self.stage_registry.register_stage(ShellStage("Stage 5: LearningEngine"))
        self.stage_registry.register_stage(ShellStage("Stage 6: ResponseBridge"))

        self._is_initialized = True
        self.logger.info("BrainKernel initialized successfully.")

    def process(self, stimulus: str, session_id: str = "default_session") -> FinalOutput:
        """
        Primary execution entry point orchestrating context lifecycles.
        """
        if not self._is_initialized:
            raise HSCIError("BrainKernel is not initialized. Run initialize() first.")

        request_id = str(uuid.uuid4())
        self.logger.info(f"[RequestID: {request_id}] Received stimulus: '{stimulus}'")

        # Stage -1: Pre-emption Teaching Check
        if self._teach_preempt_callback is not None:
            teach_response = self._teach_preempt_callback(stimulus)
            if teach_response is not None:
                self.logger.info(f"[RequestID: {request_id}] Stimulus pre-empted by TeachingProtocol. Standard loop bypassed.")
                return FinalOutput(
                    answer=teach_response,
                    is_verified=True,
                    confidence=1.0,
                    concepts_used=["universal_concept"],
                    reasoning_trace=["Pre-empted Teaching: Extracted definition and registered directly."],
                    proof=None
                )

        # Allocate CognitiveContext
        with CognitiveContext(request_id=request_id, session_id=session_id, stimulus=stimulus) as context:
            self.event_bus.emit("on_start", context)

            try:
                # Stage machine execution loop
                for stage in self.stage_registry.get_stages():
                    self.logger.debug(f"[RequestID: {request_id}] Transitioning to {stage.name}")
                    self.event_bus.emit("on_stage_start", context)
                    
                    start_time = time.perf_counter()
                    
                    # Execute Stage
                    stage.execute(context)
                    
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    context.working_memory.record_duration(stage.name, duration_ms)
                    
                    self.event_bus.emit("on_stage_success", context)
                    self.logger.debug(f"[RequestID: {request_id}] Finished {stage.name} in {duration_ms:.2f}ms")

                # Successful loop execution
                context.working_memory.verification_passed = True
                self.event_bus.emit("on_success", context)

                return FinalOutput(
                    answer="conversational_response" if context.working_memory.stimulus else "dummy_answer",
                    is_verified=True,
                    confidence=1.0,
                    concepts_used=context.working_memory.get_active_concepts(),
                    reasoning_trace=[f"{k}: {v:.2f}ms" for k, v in context.working_memory.stage_durations.items()],
                    proof=context.working_memory.proof_trace,
                    attempts=context.working_memory.attempts
                )

            except Exception as e:
                self.logger.error(f"[RequestID: {request_id}] Subsystem loop execution error: {e}", exc_info=True)
                self.event_bus.emit("on_stage_failure", context)
                
                # Recover failure or timeout
                return FinalOutput(
                    answer="HSCI could not mathematically verify the proposed logical solution.",
                    is_verified=False,
                    confidence=0.0,
                    concepts_used=[],
                    reasoning_trace=[f"Execution exception: {str(e)}"],
                    proof=None,
                    attempts=context.working_memory.attempts
                )
            
            finally:
                self.event_bus.emit("on_stop", context)

    def shutdown(self) -> None:
        """
        Orderly releases registries and logs exit parameters.
        """
        if not self._is_initialized:
            return
        self.logger.info("Deallocating BrainKernel resources...")
        self._is_initialized = False
        self.logger.info("BrainKernel shutdown complete.")
