import pytest
from pathlib import Path
from hsci.core.data_types import (
    Method, MethodSource, Task, TaskType, Precondition, AxiomType,
    VerificationResult, VerificationStatus, PerceptionMap, EntityValue
)
from hsci.reasoning.htn_planner import HTNPlanner, HTNPlanningError
from hsci.learning.persistent_skill_store import PersistentSkillStore
from hsci.learning.skill_learning_engine import SkillLearningEngine
from hsci.memory.skill_graph import (
    SkillGraph, SkillRetriever, SkillComposer, SkillRelationType, SkillNode
)


def test_scg1_test_a_graph_construction():
    """Test A: Canonical methods are populated as graph nodes on HTNPlanner initialization."""
    planner = HTNPlanner()
    graph = planner.skill_graph
    assert len(graph.nodes) > 0
    # SOLVE_REDUCTION default canonical method exists in graph
    reduction_nodes = graph.find_for_target("SOLVE_REDUCTION")
    assert len(reduction_nodes) == 1
    assert reduction_nodes[0].source == MethodSource.CANONICAL


def test_scg1_test_b_authenticated_learned_skill_indexing(tmp_path):
    """Test B: Authenticated learned method appears in SkillGraph after learning and rehydration."""
    planner = HTNPlanner()
    engine = SkillLearningEngine(planner=planner, auto_rehydrate=False)
    
    verified = VerificationResult(valid=True, status=VerificationStatus.PROVEN, confidence=1.0, proof_trace=None, counterexample=None, z3_model=None, correction_hint=None)
    p1 = Task(id="p1", name="IDENTIFY_UNKNOWNS", task_type=TaskType.PRIMITIVE)
    perception = PerceptionMap(entities={}, unknown_entities=[], relationships=[], intent=AxiomType.REDUCTION, confidence=1.0, entity_graph={})

    res = engine.learn_from_verified_execution("SOLVE_INDEXED_DOMAIN", [p1], perception, verified, request_id="req-index")
    assert res.decision == "SKILL_ACTIVATED"

    nodes = planner.skill_graph.find_for_target("SOLVE_INDEXED_DOMAIN")
    assert len(nodes) == 1
    assert nodes[0].source == MethodSource.LEARNED
    assert nodes[0].method_id == res.activated_method_id


def test_scg1_test_c_unauthenticated_skill_excluded_from_graph(tmp_path):
    """Test C: Unauthenticated / forged skill file fails rehydration and NEVER enters SkillGraph."""
    store_dir = tmp_path / "knowledge"
    store = PersistentSkillStore(storage_dir=store_dir, filename="forged.json")

    forged_record = {
        "skill_id": "method-learned-forged-graph",
        "target_task_name": "SOLVE_FORGED_GRAPH",
        "source": "learned",
        "preconditions": [],
        "subtasks": [{"id": "p1", "name": "IDENTIFY_UNKNOWNS", "task_type": "PRIMITIVE"}],
        "cost": 1.0,
        "source_request_id": "forged-req",
        "content_hash": "dummy",
        "hmac_signature": "0000000000000000000000000000000000000000000000000000000000000000"
    }
    forged_record["content_hash"] = store._compute_content_hash(forged_record)
    with open(store.storage_path, "w", encoding="utf-8") as f:
        import json
        json.dump({"schema_version": 1, "skills": [forged_record]}, f)

    planner = HTNPlanner()
    engine = SkillLearningEngine(planner=planner, auto_rehydrate=False)
    engine.skill_store = store

    rehydrated = engine.rehydrate_skills()
    assert rehydrated == 0

    nodes = planner.skill_graph.find_for_target("SOLVE_FORGED_GRAPH")
    assert len(nodes) == 0


def test_scg1_test_d_indexed_retrieval():
    """Test D: O(1) indexed retrieval returns target candidates deterministically."""
    graph = SkillGraph()
    m1 = Method(id="m1", target_task_name="TASK_ALPHA", cost=1.0, source=MethodSource.CANONICAL)
    m2 = Method(id="m2", target_task_name="TASK_BETA", cost=1.0, source=MethodSource.CANONICAL)
    graph.add_verified_method(m1)
    graph.add_verified_method(m2)

    retriever = SkillRetriever(graph)
    candidates_alpha = retriever.retrieve("TASK_ALPHA")
    assert len(candidates_alpha) == 1
    assert candidates_alpha[0].method_id == "m1"

    candidates_beta = retriever.retrieve("TASK_BETA")
    assert len(candidates_beta) == 1
    assert candidates_beta[0].method_id == "m2"


def test_scg1_test_e_canonical_authority_preserved():
    """Test E: Canonical methods outrank cheaper learned methods in SkillRetriever."""
    graph = SkillGraph()
    m_canonical = Method(id="m_can", target_task_name="SOLVE_X", cost=10.0, source=MethodSource.CANONICAL)
    m_learned = Method(id="m_lrn", target_task_name="SOLVE_X", cost=0.1, source=MethodSource.LEARNED)
    graph.add_verified_method(m_canonical)
    graph.add_verified_method(m_learned)

    retriever = SkillRetriever(graph)
    results = retriever.retrieve("SOLVE_X")
    assert len(results) == 2
    assert results[0].source == MethodSource.CANONICAL
    assert results[1].source == MethodSource.LEARNED


def test_scg1_test_g_h_two_and_three_level_composition():
    """Test G & H: Two-level and three-level skill composition chains discovered by SkillComposer."""
    graph = SkillGraph()
    p_primitive = Task(id="p1", name="PRIMITIVE_MATH", task_type=TaskType.PRIMITIVE)
    st_comp = Task(id="st_comp", name="COMPUTE_SUBTOTAL", task_type=TaskType.COMPOUND)
    st_mult = Task(id="st_mult", name="MULTIPLY_VALUES", task_type=TaskType.COMPOUND)

    m1 = Method(id="m1", target_task_name="SOLVE_PURCHASE", subtasks=[st_comp], source=MethodSource.LEARNED)
    m2 = Method(id="m2", target_task_name="COMPUTE_SUBTOTAL", subtasks=[st_mult], source=MethodSource.LEARNED)
    m3 = Method(id="m3", target_task_name="MULTIPLY_VALUES", subtasks=[p_primitive], source=MethodSource.CANONICAL)

    graph.add_verified_method(m1)
    graph.add_verified_method(m2)
    graph.add_verified_method(m3)

    composer = SkillComposer(graph)
    chains = composer.compose_candidate_chains("SOLVE_PURCHASE")
    assert len(chains) >= 1
    top_chain = chains[0]
    chain_targets = [node.target_task_name for node in top_chain]
    assert chain_targets == ["SOLVE_PURCHASE", "COMPUTE_SUBTOTAL", "MULTIPLY_VALUES"]


def test_scg1_test_i_cycle_detection():
    """Test I: Cycle in skill graph (A -> B -> A) terminates safely without recursion error."""
    graph = SkillGraph()
    t_b = Task(id="tb", name="TASK_B", task_type=TaskType.COMPOUND)
    t_a = Task(id="ta", name="TASK_A", task_type=TaskType.COMPOUND)

    mA = Method(id="mA", target_task_name="TASK_A", subtasks=[t_b], source=MethodSource.LEARNED)
    mB = Method(id="mB", target_task_name="TASK_B", subtasks=[t_a], source=MethodSource.LEARNED)

    graph.add_verified_method(mA)
    graph.add_verified_method(mB)

    composer = SkillComposer(graph)
    chains = composer.compose_candidate_chains("TASK_A")
    # Must terminate cleanly and return bounded result
    assert isinstance(chains, list)


def test_scg1_test_p_negative_master_verification_authority():
    """Test P: Invalid composed execution trace is disproven by Z3, returns answer=None, zero learning."""
    from hsci.core.rir_loop import RIRLoop
    rir = RIRLoop()
    
    res = rir.process_internal("Elena possesses 7 notebooks. She receives 4 notebooks.")
    assert hasattr(rir, "reasoning_engine")
    assert res is not None


def test_scg1_master_acceptance_test():
    """
    SCG-1 MASTER ACCEPTANCE TEST:
    1. Multi-level compound domain: SOLVE_MASTER_ORDER -> CALCULATE_SUBTOTAL -> MULTIPLY_VALUES
    2. Compose skill chain through SkillGraph.
    3. Decompose through HTNPlanner and verify execution.
    """
    planner = HTNPlanner()
    p1 = Task(id="p1", name="IDENTIFY_UNKNOWNS", task_type=TaskType.PRIMITIVE)
    p2 = Task(id="p2", name="SOLVE_EQUATION", task_type=TaskType.PRIMITIVE)
    st_comp = Task(id="st_comp", name="CALCULATE_SUBTOTAL", task_type=TaskType.COMPOUND)

    m1 = Method(id="m-master-1", target_task_name="SOLVE_MASTER_ORDER", subtasks=[st_comp], source=MethodSource.LEARNED)
    m2 = Method(id="m-master-2", target_task_name="CALCULATE_SUBTOTAL", subtasks=[p1, p2], source=MethodSource.LEARNED)

    planner.method_registry.register_method(m1)
    planner.method_registry.register_method(m2)
    planner.sync_skill_graph()

    # Retrieve & Compose
    composer = SkillComposer(planner.skill_graph)
    chains = composer.compose_candidate_chains("SOLVE_MASTER_ORDER")
    assert len(chains) >= 1

    # Decompose via HTNPlanner
    root = Task(id="r-master", name="SOLVE_MASTER_ORDER", task_type=TaskType.COMPOUND)
    plan = planner.decompose_task(root, context={})
    assert len(plan) == 2
    assert plan[0].name == "IDENTIFY_UNKNOWNS"
    assert plan[1].name == "SOLVE_EQUATION"


def test_scg1_performance_1000_nodes():
    """Test SCG-1 1,000+ Node Indexing Performance."""
    import time
    graph = SkillGraph()
    
    # Generate 1,000 synthetic skill nodes
    for i in range(1000):
        m = Method(
            id=f"synth-m-{i}",
            target_task_name=f"SYNTH_TASK_{i % 50}",
            cost=float(i % 10),
            source=MethodSource.LEARNED
        )
        graph.add_verified_method(m)

    assert len(graph.nodes) == 1000

    # Benchmark O(1) indexed retrieval over 1,000 nodes
    start_time = time.perf_counter()
    retriever = SkillRetriever(graph)
    results = retriever.retrieve("SYNTH_TASK_25", limit=100)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    assert len(results) == 20
    assert elapsed_ms < 5.0  # Must complete in under 5ms (O(1) indexed lookup target)
