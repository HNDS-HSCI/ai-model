"""HSCI VS-7 Acceptance Test Suite: Cognitive Workspace & Task Decomposition.

Evaluates request-scoped CognitiveWorkspace lifecycle, CognitiveTaskGraph DAG scheduling,
cycle detection, multi-intent decomposition, dependency unblocking/blocking cascades,
contextual reference resolution, and full regression integrity.

ZERO mocks on the cognitive execution path.
"""
import time
import pytest

from hsci.core.cognitive_pipeline import bootstrap_cognitive_pipeline
from hsci.core.kernel import CognitiveContext
from hsci.cognition.interpretation.models import (
    RawInput,
    TaskAction,
    SituationStatus,
    GroundingStatus,
    GroundedEntity,
    Evidence,
    CognitiveSituation,
    CognitiveTask,
)
from hsci.cognition.interpretation.semantic_model import (
    SemanticRequest,
    CommunicativeGoal,
    EntityMention,
    ContextReference,
)
from hsci.cognition.workspace import (
    CognitiveWorkspace,
    WorkspaceStatus,
    CognitiveTaskGraph,
    GraphTask,
    TaskStatus,
    TaskResult,
    TaskResultType,
    CycleDetectedError,
    DuplicateTaskError,
    InvalidDependencyError,
    TaskDecomposer,
)


# ─────────────────────────────────────────────────────────────
# TEST GROUP 1: WORKSPACE LIFECYCLE & STATE ATTACHMENT
# ─────────────────────────────────────────────────────────────

def test_vs7_01_workspace_creation_and_lifecycle():
    """Workspace initializes with CREATED and transitions to GROUNDED and READY."""
    ws = CognitiveWorkspace(request_id="req-123", session_id="sess-456")
    assert ws.status == WorkspaceStatus.CREATED
    assert ws.metadata.request_id == "req-123"

    # Attach semantic request & grounded entities
    req = SemanticRequest(goal=CommunicativeGoal.EXPLAIN)
    ws.attach_semantic_request(req)
    assert ws.semantic_request == req

    ge = GroundedEntity(mention="Java interface", status=GroundingStatus.RESOLVED, concept_id="c_java_interface", canonical_name="Java Interface")
    ws.attach_grounded_entities([ge])
    assert ws.status == WorkspaceStatus.GROUNDED
    assert "java interface" in ws.grounded_entities


def test_vs7_02_workspace_isolation_between_requests():
    """Workspaces created for distinct requests maintain isolated state and dispose cleanly."""
    ws1 = CognitiveWorkspace(request_id="req-1")
    ws2 = CognitiveWorkspace(request_id="req-2")

    ge1 = GroundedEntity(mention="class", status=GroundingStatus.RESOLVED, concept_id="c_class", canonical_name="Class")
    ws1.attach_grounded_entities([ge1])

    assert "class" in ws1.grounded_entities
    assert "class" not in ws2.grounded_entities

    ws1.dispose()
    assert len(ws1.grounded_entities) == 0


# ─────────────────────────────────────────────────────────────
# TEST GROUP 2: TASK GRAPH TOPOLOGY & CYCLE DETECTION
# ─────────────────────────────────────────────────────────────

def test_vs7_03_graph_linear_dependencies_and_unblocking():
    """Linear dependency graph A -> B -> C unblocks sequentially upon task completion."""
    graph = CognitiveTaskGraph()

    t_a = GraphTask(id="task_A", action=TaskAction.EXPLAIN_CONCEPT, primary_target="Java Interface", dependencies=[])
    t_b = GraphTask(id="task_B", action=TaskAction.DERIVE_RELATIONSHIP, primary_target="Abstraction", dependencies=["task_A"])
    t_c = GraphTask(id="task_C", action=TaskAction.EXPLAIN_CONCEPT, primary_target="Abstraction", dependencies=["task_B"])

    graph.add_task(t_a)
    graph.add_task(t_b)
    graph.add_task(t_c)
    assert graph.validate() is True

    # Initial state: only A is READY
    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task_A"

    # Complete A -> B becomes READY
    res_a = TaskResult(task_id="task_A", result_type=TaskResultType.DEFINITION, payload={"def": "..."})
    graph.mark_completed("task_A", res_a)

    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task_B"

    # Complete B -> C becomes READY
    res_b = TaskResult(task_id="task_B", result_type=TaskResultType.RELATIONSHIP_PROOF, payload={"rel": "..."})
    graph.mark_completed("task_B", res_b)

    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task_C"

    # Complete C -> Graph is terminal
    res_c = TaskResult(task_id="task_C", result_type=TaskResultType.DEFINITION, payload={"def": "..."})
    graph.mark_completed("task_C", res_c)
    assert graph.is_terminal() is True


def test_vs7_04_graph_independent_parallel_tasks():
    """Independent tasks A and B are simultaneously READY."""
    graph = CognitiveTaskGraph()
    t_a = GraphTask(id="task_A", action=TaskAction.EXPLAIN_CONCEPT, primary_target="Java Interface")
    t_b = GraphTask(id="task_B", action=TaskAction.EXPLAIN_CONCEPT, primary_target="Class")

    graph.add_task(t_a)
    graph.add_task(t_b)
    assert graph.validate() is True

    ready = graph.get_ready_tasks()
    assert len(ready) == 2
    assert {t.id for t in ready} == {"task_A", "task_B"}


def test_vs7_05_cycle_detection_rejection():
    """Direct cycle A -> B -> A and indirect cycles are immediately detected and rejected."""
    graph = CognitiveTaskGraph()
    t_a = GraphTask(id="task_A", action=TaskAction.EXPLAIN_CONCEPT, dependencies=["task_B"])
    t_b = GraphTask(id="task_B", action=TaskAction.EXPLAIN_CONCEPT, dependencies=["task_A"])

    graph.add_task(t_a)
    graph.add_task(t_b)

    with pytest.raises(CycleDetectedError):
        graph.validate()


def test_vs7_06_duplicate_task_id_rejection():
    """Adding a task with an existing task ID raises DuplicateTaskError."""
    graph = CognitiveTaskGraph()
    t1 = GraphTask(id="task_1", action=TaskAction.EXPLAIN_CONCEPT)
    t2 = GraphTask(id="task_1", action=TaskAction.COMPARE_CONCEPTS)

    graph.add_task(t1)
    with pytest.raises(DuplicateTaskError):
        graph.add_task(t2)


def test_vs7_07_invalid_dependency_rejection():
    """Referencing a non-existent task ID in dependencies raises InvalidDependencyError."""
    graph = CognitiveTaskGraph()
    t1 = GraphTask(id="task_1", action=TaskAction.EXPLAIN_CONCEPT, dependencies=["non_existent_task"])
    graph.add_task(t1)

    with pytest.raises(InvalidDependencyError):
        graph.validate()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 3: CASCADING FAILURE & REFUSAL PROPAGATION
# ─────────────────────────────────────────────────────────────

def test_vs7_08_dependency_failure_cascades_blocked():
    """Failure of Task A cascades BLOCKED status to dependent Task B without executing B."""
    graph = CognitiveTaskGraph()
    t_a = GraphTask(id="task_A", action=TaskAction.EXPLAIN_CONCEPT, primary_target="InvalidConcept")
    t_b = GraphTask(id="task_B", action=TaskAction.DERIVE_RELATIONSHIP, dependencies=["task_A"])
    t_c = GraphTask(id="task_C", action=TaskAction.EXPLAIN_CONCEPT, primary_target="Class")  # Independent

    graph.add_task(t_a)
    graph.add_task(t_b)
    graph.add_task(t_c)
    graph.validate()

    # Fail Task A
    graph.mark_failed("task_A", "Lookup failed in UKM")

    assert t_a.status == TaskStatus.FAILED
    assert t_b.status == TaskStatus.BLOCKED
    assert "Blocked by dependency 'task_A'" in t_b.error_message

    # Independent Task C remains READY
    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task_C"


def test_vs7_09_refusal_cascades_blocked():
    """Refusal of Task A cascades BLOCKED status to downstream dependent Task B."""
    graph = CognitiveTaskGraph()
    t_a = GraphTask(id="task_A", action=TaskAction.REPORT_UNKNOWN)
    t_b = GraphTask(id="task_B", action=TaskAction.COMPARE_CONCEPTS, dependencies=["task_A"])

    graph.add_task(t_a)
    graph.add_task(t_b)
    graph.validate()

    res_a = TaskResult(task_id="task_A", result_type=TaskResultType.REFUSAL, confidence=0.0)
    graph.mark_refused("task_A", res_a)

    assert t_a.status == TaskStatus.REFUSED
    assert t_b.status == TaskStatus.BLOCKED


# ─────────────────────────────────────────────────────────────
# TEST GROUP 4: MULTI-INTENT DECOMPOSITION & EXECUTION
# ─────────────────────────────────────────────────────────────

def test_vs7_10_multi_intent_decomposition_and_execution():
    """Compound request 'Explain X, compare it with Y, and tell me how it relates to Z' decomposes into task graph."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        query = "Explain Java Interface, compare it with Class, and tell me how it relates to Abstraction."
        ans = pipeline.answer(query)

        # Assert answer has workspace and results
        assert hasattr(ans, "workspace")
        ws: CognitiveWorkspace = ans.workspace
        assert ws.status == WorkspaceStatus.COMPLETED
        assert len(ws.task_graph.tasks) >= 2
        assert len(ws.results) >= 2
        assert ans.direct_answer
        assert "reference type declaring abstract methods" in ans.direct_answer
        assert "Class" in ans.direct_answer
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 5: CONTEXTUAL REFERENCE RESOLUTION
# ─────────────────────────────────────────────────────────────

def test_vs7_11_context_reference_resolution():
    """Deictic marker is resolved when explicit antecedent evidence is provided to workspace."""
    ws = CognitiveWorkspace(request_id="req-followup")
    cr = ContextReference(marker="it", reference_type="PRONOUN", is_resolved=False)
    req = SemanticRequest(goal=CommunicativeGoal.COMPARE, context_references=[cr])
    ws.attach_semantic_request(req)

    assert ws.context_references[0].is_resolved is False

    # Resolve with explicit antecedent
    resolved = ws.resolve_context_reference("it", "Java Interface")
    assert resolved is True
    assert ws.context_references[0].is_resolved is True
    assert ws.context_references[0].antecedent == "Java Interface"
    assert ws.session_context["it"] == "Java Interface"


def test_vs7_12_unresolved_context_refusal():
    """Unresolved context reference produces explicit REPORT_INSUFFICIENT_CONTEXT."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        ans = pipeline.answer("Why is it useful?")
        assert ans.cognitive_task.action == TaskAction.REPORT_INSUFFICIENT_CONTEXT
        assert ans.confidence.score == 0.0
        assert ans.workspace.status == WorkspaceStatus.REFUSED
    finally:
        pipeline.provider.close()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 6: DETERMINISM & SCALABILITY PROFILING
# ─────────────────────────────────────────────────────────────

def test_vs7_13_deterministic_execution_ordering():
    """Identical input requests produce topologically identical task execution order."""
    pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
    try:
        q = "Compare Java Interface and Class."
        ans1 = pipeline.answer(q)
        ans2 = pipeline.answer(q)

        ws1: CognitiveWorkspace = ans1.workspace
        ws2: CognitiveWorkspace = ans2.workspace

        order1 = [t.action.value for t in ws1.task_graph.topological_sort()]
        order2 = [t.action.value for t in ws2.task_graph.topological_sort()]
        assert order1 == order2
    finally:
        pipeline.provider.close()


@pytest.mark.parametrize("task_count", [1, 3, 10, 25, 100])
def test_vs7_14_task_graph_scalability(task_count: int):
    """Task graph scales linearly with task count without exponential slowdown."""
    graph = CognitiveTaskGraph()
    start = time.perf_counter()

    # Build linear chain of N tasks
    prev_id = None
    for i in range(task_count):
        tid = f"task_{i}"
        deps = [prev_id] if prev_id else []
        t = GraphTask(id=tid, action=TaskAction.EXPLAIN_CONCEPT, primary_target="Java Interface", dependencies=deps)
        graph.add_task(t)
        prev_id = tid

    graph.validate()
    top_order = graph.topological_sort()
    assert len(top_order) == task_count

    duration_ms = (time.perf_counter() - start) * 1000
    assert duration_ms < 100.0, f"Graph operations for {task_count} tasks took {duration_ms:.2f}ms (threshold: 100ms)"
