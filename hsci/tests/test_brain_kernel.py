import pytest
import time
import z3
import threading
from typing import Optional, Dict, Any, List
from hsci.core.config import SystemConfig
from hsci.core.data_types import AxiomType, Expression
from hsci.core.kernel import (
    BrainKernel, IStageExecutor, CognitiveContext, ISolverPlugin,
    SolverError, VerificationError
)
from hsci.core.working_memory import WorkingMemory

# Mock Stage Executor for testing
class MockStage(IStageExecutor):
    def __init__(self, name: str, fail: bool = False):
        self._name = name
        self._fail = fail
        self.called = False

    @property
    def name(self) -> str:
        return self._name

    def execute(self, context: CognitiveContext) -> None:
        self.called = True
        if self._fail:
            raise VerificationError("Mock stage verification failure.")
        # V4-compliant concept activation
        context.working_memory.activate_concepts([self._name], {self._name: 1.0})

# Mock Solver Plugin for testing
class MockSolver(ISolverPlugin):
    @property
    def domain(self) -> str:
        return "mock_domain"

    def can_solve(self, subgoal_id: str, axiom_type: AxiomType) -> bool:
        return subgoal_id == "mock_subgoal"

    def solve(self, subgoal_id: str, context: CognitiveContext) -> str:
        return "solved_value"

def test_cognitive_context_z3_cleanup():
    """Unit test checking thread-isolated Z3 Context allocation and cleanups."""
    ctx_manager = CognitiveContext(request_id="test_req", session_id="test_sess", stimulus="solve x=5")
    assert ctx_manager.z3_context is None
    
    with ctx_manager as context:
        assert context.z3_context is not None
        assert isinstance(context.z3_context, z3.Context)
        assert context.is_active is True
        
    assert ctx_manager.z3_context is None
    assert ctx_manager.is_active is False

def test_brain_kernel_sequential_execution():
    """Integration test validating that all registered stages execute sequentially."""
    config = SystemConfig()
    kernel = BrainKernel(config)
    kernel.initialize()

    # Verify that stages are pre-populated
    assert len(kernel.stage_registry.get_stages()) == 10

    # Execute request
    output = kernel.process("Verify equations", session_id="test_session")
    assert output.is_verified is True
    assert output.answer == "conversational_response"
    assert len(output.reasoning_trace) == 10  # Timing metrics for all 10 stages

def test_brain_kernel_preemption_gate():
    """Unit test validating that TeachingProtocol pre-empts normal loop execution."""
    config = SystemConfig()
    kernel = BrainKernel(config)
    kernel.initialize()

    # Install intercept handler
    def mock_teach_intercept(stimulus: str) -> Optional[str]:
        if "TEACH:" in stimulus:
            return "Learned concept from teach input"
        return None

    kernel.set_teach_preempt_handler(mock_teach_intercept)

    # Standard loop is bypassed
    output = kernel.process("TEACH: concept definition", session_id="test_session")
    assert output.is_verified is True
    assert output.answer == "Learned concept from teach input"
    assert "Pre-empted Teaching" in output.reasoning_trace[0]

def test_brain_kernel_exception_recovery():
    """Integration test checking fallback recovery on execution failure."""
    config = SystemConfig()
    kernel = BrainKernel(config)
    kernel.initialize()

    # Inject a failing stage to trigger recovery
    failing_stage = MockStage("FailingStage", fail=True)
    kernel.stage_registry.get_stages().append(failing_stage)

    output = kernel.process("Stimulus containing errors", session_id="test_session")
    assert output.is_verified is False
    assert "HSCI could not mathematically verify" in output.answer
    assert "Mock stage verification failure" in output.reasoning_trace[0]

def test_solver_registry_dispatch():
    """Unit test validating dynamic solver registration and dispatching."""
    config = SystemConfig()
    kernel = BrainKernel(config)
    kernel.initialize()

    mock_solver = MockSolver()
    kernel.solver_registry.register_solver(mock_solver)

    with CognitiveContext("req_id", "sess_id", "stimulus") as context:
        result = kernel.solver_registry.dispatch("mock_subgoal", AxiomType.REDUCTION, context)
        assert result == "solved_value"

        with pytest.raises(SolverError):
            kernel.solver_registry.dispatch("unknown_subgoal", AxiomType.REDUCTION, context)

def test_startup_overhead_benchmark():
    """Benchmark test measuring the cold start initialization overhead."""
    config = SystemConfig()
    kernel = BrainKernel(config)

    start_time = time.perf_counter()
    kernel.initialize()
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    # Enforce startup latency limit
    assert duration_ms < 50.0  # Cold start initialization must be sub-50ms
    print(f"Startup overhead: {duration_ms:.2f}ms")

# ─────────────────────────────────────────────
# SPRINT 5 WORKING MEMORY SPECIFIC TESTS
# ─────────────────────────────────────────────

def test_working_memory_lifecycle():
    """Tests allocation, mutation, clearing, and disposal of WorkingMemory."""
    wm = WorkingMemory(request_id="req_123", session_id="sess_123", stimulus="test")
    
    # Assert initial states
    assert wm.metadata.request_id == "req_123"
    assert wm.stimulus == "test"
    assert wm.goal_context is None
    
    # Mutate
    wm.activate_concepts(["concept_A"], {"concept_A": 0.8})
    assert "concept_A" in wm.get_active_concepts()
    
    # Store goals & expressions
    wm.store_goal("primary_test_goal", [])
    assert wm.goal_context is not None
    assert wm.goal_context.primary_goal == "primary_test_goal"
    
    # Clear
    wm.clear()
    assert wm.goal_context is None
    assert len(wm.get_active_concepts()) == 0
    assert wm.metadata.request_id == "req_123"  # Metadata preserved
    
    # Dispose
    wm.dispose()
    # Explicit dereferencing of sub-contexts
    with pytest.raises(AttributeError):
        _ = wm.attention_buffer

def test_working_memory_snapshot_restore_serialization():
    """Verifies Z3 expression S-expression conversion and float-list conversions in snapshots."""
    wm = WorkingMemory(request_id="req_123", session_id="sess_123", stimulus="solve x=5")
    
    # Create Z3 context and expression
    z3_ctx = z3.Context()
    x = z3.Int('x', ctx=z3_ctx)
    formula = (x + 5 == 10)
    
    expr = Expression(value=formula, concepts_used=["z3_arithmetic"])
    wm.store_expression(expr)
    
    # Snapshot (triggers Z3 sexpr conversion)
    snap = wm.snapshot()
    serialized_expr = snap["candidate_expressions"][0]
    assert isinstance(serialized_expr["value"], str)
    assert "(+ x 5)" in serialized_expr["value"] or "x + 5" in serialized_expr["value"] or "x" in serialized_expr["value"]
    
    # Restore
    wm2 = WorkingMemory(request_id="other", session_id="other", stimulus="")
    wm2.restore(snap)
    assert wm2.stimulus == "solve x=5"
    assert len(wm2.reasoning_context.candidate_expressions) == 1
    assert wm2.reasoning_context.candidate_expressions[0].value == serialized_expr["value"]

def test_concurrent_request_isolation():
    """Verifies that WorkingMemory instances remain completely isolated across request threads."""
    errors = []
    
    def worker(thread_id: int):
        try:
            # Each thread allocates its own isolated context
            with CognitiveContext(request_id=f"req_{thread_id}", session_id="sess", stimulus=f"stim_{thread_id}") as ctx:
                ctx.working_memory.activate_concepts([f"concept_{thread_id}"], {f"concept_{thread_id}": 0.9})
                time.sleep(0.01) # Force thread overlap
                active = ctx.working_memory.get_active_concepts()
                # Assert no other thread concepts leaked in
                assert len(active) == 1
                assert active[0] == f"concept_{thread_id}"
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(errors) == 0

def test_working_memory_allocation_benchmarks():
    """Benchmarks WorkingMemory allocation and cleanup latencies against targets."""
    start_time = time.perf_counter()
    iterations = 500
    
    for i in range(iterations):
        wm = WorkingMemory(request_id=f"req_{i}", session_id="sess", stimulus="test")
        wm.activate_concepts(["A", "B"], {"A": 0.5, "B": 0.9})
        wm.dispose()
        
    total_duration_ms = (time.perf_counter() - start_time) * 1000.0
    avg_duration_ms = total_duration_ms / iterations
    
    print(f"\nAverage WorkingMemory allocation/disposal latency: {avg_duration_ms:.4f}ms")
    # Target is sub-0.1ms per cycle
    assert avg_duration_ms < 0.1
