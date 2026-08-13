import pytest
from typing import Dict, Any

from hsci.core.data_types import (
    Task, TaskType, Precondition, PerceptionMap, AxiomType,
    VerificationResult, VerificationStatus, ReflectionResult, ReflectionFailureType,
    SkillCandidate, SkillCandidateStatus, Method, EntityValue
)
from hsci.core.working_memory import WorkingMemory, SemanticFrame
from hsci.reasoning.htn_planner import HTNPlanner, HTNPlanningError
from hsci.reasoning.reasoning_engine import ReasoningEngine
from hsci.symbolic.z3_verifier import Z3VerificationEngine
from hsci.learning.skill_learning_engine import SkillLearningEngine, SkillValidator, SkillLearningPolicy


def test_hp4c_test_a_precondition_unsat_does_not_create_method():
    """Test A: PRECONDITION_UNSAT reflection alone does not create a skill candidate."""
    policy = SkillLearningPolicy()
    ref = ReflectionResult(
        reflection_id="r1",
        request_id="req-1",
        failure_category=ReflectionFailureType.PRECONDITION_UNSAT,
        failed_stage="PLANNING",
        failed_task_name="SOLVE_REDUCTION",
        root_cause="Precondition failed"
    )
    decision = policy.evaluate_reflection(ref)
    assert decision == "NO_LEARNING"


def test_hp4c_test_b_cycle_does_not_create_method():
    """Test B: CYCLE failure reflection does not generate a skill candidate."""
    policy = SkillLearningPolicy()
    ref = ReflectionResult(
        reflection_id="r2",
        request_id="req-2",
        failure_category=ReflectionFailureType.DECOMPOSITION_CYCLE,
        failed_stage="PLANNING",
        failed_task_name="CYCLE_TASK",
        root_cause="Cycle detected"
    )
    decision = policy.evaluate_reflection(ref)
    assert decision == "NO_LEARNING"


def test_hp4c_test_c_max_depth_does_not_create_method():
    """Test C: MAX_DEPTH failure reflection does not generate a skill candidate."""
    policy = SkillLearningPolicy()
    ref = ReflectionResult(
        reflection_id="r3",
        request_id="req-3",
        failure_category=ReflectionFailureType.MAX_DEPTH_EXCEEDED,
        failed_stage="PLANNING",
        failed_task_name="DEEP_TASK",
        root_cause="Max depth exceeded"
    )
    decision = policy.evaluate_reflection(ref)
    assert decision == "NO_LEARNING"


def test_hp4c_test_d_failed_verification_never_learned():
    """Test D: Unverified or failed solution execution is refused by SkillLearningEngine."""
    planner = HTNPlanner()
    engine = SkillLearningEngine(planner=planner)
    unverified = VerificationResult(
        valid=False,
        status=VerificationStatus.DISPROVEN,
        confidence=0.0,
        proof_trace=None,
        counterexample=None,
        z3_model=None,
        correction_hint=None
    )
    p1 = Task(id="p1", name="PRIM1", task_type=TaskType.PRIMITIVE)
    res = engine.learn_from_verified_execution("SOLVE_X", [p1], None, unverified, request_id="req-unverified")
    assert res.decision == "NO_LEARNING"
    assert "not proven" in res.reason.lower()


def test_hp4c_test_e_no_method_without_evidence_produces_no_active_skill():
    """Test E: NO_METHOD reflection policy evaluation returns PROPOSE_SKILL signal, but no skill is active until verified execution occurs."""
    planner = HTNPlanner()
    policy = SkillLearningPolicy()
    ref = ReflectionResult(
        reflection_id="r4",
        request_id="req-4",
        failure_category=ReflectionFailureType.NO_METHOD,
        failed_stage="PLANNING",
        failed_task_name="MISSING_TASK"
    )
    decision = policy.evaluate_reflection(ref)
    assert decision == "PROPOSE_SKILL"
    # Verify MethodRegistry still has no method for MISSING_TASK
    methods = planner.method_registry.get_methods_for_task("MISSING_TASK")
    assert len(methods) == 0


def test_hp4c_test_f_verified_successful_trace_produces_and_validates_candidate():
    """Test F: Verified execution produces a SkillCandidate that passes validation."""
    planner = HTNPlanner()
    engine = SkillLearningEngine(planner=planner)
    verified = VerificationResult(
        valid=True,
        status=VerificationStatus.PROVEN,
        confidence=1.0,
        proof_trace=None,
        counterexample=None,
        z3_model=None,
        correction_hint=None
    )
    p1 = Task(id="p1", name="IDENTIFY_UNKNOWNS", task_type=TaskType.PRIMITIVE)
    p2 = Task(id="p2", name="SOLVE_EQUATION", task_type=TaskType.PRIMITIVE)

    perception = PerceptionMap(
        entities={"x": EntityValue(value=10, unit=None, known=True, raw_text="10")},
        unknown_entities=[],
        relationships=[],
        intent=AxiomType.REDUCTION,
        confidence=1.0,
        entity_graph={}
    )

    res = engine.learn_from_verified_execution("SOLVE_CUSTOM", [p1, p2], perception, verified, request_id="req-f")
    assert res.decision == "SKILL_ACTIVATED"
    assert res.validation_passed is True
    assert res.activated_method_id.startswith("method-learned-")

    # Verify method is active in planner MethodRegistry
    learned_methods = planner.method_registry.get_methods_for_task("SOLVE_CUSTOM")
    assert len(learned_methods) == 1
    assert learned_methods[0].subtasks == [p1, p2]


def test_hp4c_test_g_candidate_inactive_before_validation():
    """Test G: SkillCandidate remains inactive until validation succeeds."""
    planner = HTNPlanner()
    validator = SkillValidator(planner=planner)
    p1 = Task(id="p1", name="PRIM1", task_type=TaskType.PRIMITIVE)
    candidate = SkillCandidate(
        candidate_id="cand-g",
        source_request_id="req-g",
        target_task_name="NEW_TASK",
        proposed_subtasks=[p1]
    )
    assert candidate.status == SkillCandidateStatus.PROPOSED
    assert len(planner.method_registry.get_methods_for_task("NEW_TASK")) == 0

    is_valid = validator.validate(candidate)
    assert is_valid is True
    assert candidate.status == SkillCandidateStatus.VERIFIED


def test_hp4c_test_h_structural_validation_failure():
    """Test H: Malformed empty candidate is rejected by SkillValidator."""
    planner = HTNPlanner()
    validator = SkillValidator(planner=planner)
    candidate = SkillCandidate(
        candidate_id="cand-h",
        source_request_id="req-h",
        target_task_name="EMPTY_TASK",
        proposed_subtasks=[]
    )
    is_valid = validator.validate(candidate)
    assert is_valid is False
    assert candidate.status == SkillCandidateStatus.REJECTED
    assert "Empty proposed_subtasks list" in candidate.validation_failures[0]


def test_hp4c_test_i_cycle_validation_failure():
    """Test I: Candidate introducing direct self-cycle is rejected."""
    planner = HTNPlanner()
    validator = SkillValidator(planner=planner)
    self_sub = Task(id="s1", name="CYCLE_TASK", task_type=TaskType.COMPOUND)
    candidate = SkillCandidate(
        candidate_id="cand-i",
        source_request_id="req-i",
        target_task_name="CYCLE_TASK",
        proposed_subtasks=[self_sub]
    )
    is_valid = validator.validate(candidate)
    assert is_valid is False
    assert candidate.status == SkillCandidateStatus.REJECTED
    assert any("self-cycle" in err for err in candidate.validation_failures)


def test_hp4c_test_j_provenance_preservation():
    """Test J: Activated learned Method retains provenance trace."""
    planner = HTNPlanner()
    engine = SkillLearningEngine(planner=planner)
    verified = VerificationResult(valid=True, status=VerificationStatus.PROVEN, confidence=1.0, proof_trace=None, counterexample=None, z3_model=None, correction_hint=None)
    p1 = Task(id="p1", name="PRIM1", task_type=TaskType.PRIMITIVE)

    res = engine.learn_from_verified_execution("SOLVE_PROV", [p1], None, verified, request_id="req-provenance-123")
    method = planner.method_registry.get_methods_for_task("SOLVE_PROV")[0]

    assert "req-provenance-123" in method.description


def test_hp4c_test_k_master_phase_4c_acceptance_test():
    """
    MASTER ACCEPTANCE TEST — PHASE 4C:
    End-to-End dynamic skill acquisition flow:
    1. Attempt decomposition of unknown target task -> NO_METHOD planning failure.
    2. Execute verified solution experience trace.
    3. SkillLearningEngine validates and activates new HTN Method.
    4. Re-run HTNPlanner on the previously unknown task -> Learned Method selected and decomposed successfully!
    """
    planner = HTNPlanner()
    re = ReasoningEngine()
    re.htn_planner = planner
    engine = SkillLearningEngine(planner=planner)

    unknown_root = Task(id="u1", name="SOLVE_DYNAMIC_DOMAIN", task_type=TaskType.COMPOUND)

    # 1. Before learning: NO_METHOD error
    with pytest.raises(HTNPlanningError) as exc_info:
        planner.decompose_task(unknown_root, context={})
    assert exc_info.value.failure.failed_task_name == "SOLVE_DYNAMIC_DOMAIN"

    # 2. Verified execution experience
    verified = VerificationResult(valid=True, status=VerificationStatus.PROVEN, confidence=1.0, proof_trace=None, counterexample=None, z3_model=None, correction_hint=None)
    p1 = Task(id="p1", name="IDENTIFY_UNKNOWNS", task_type=TaskType.PRIMITIVE)
    p2 = Task(id="p2", name="SOLVE_EQUATION", task_type=TaskType.PRIMITIVE)

    perception = PerceptionMap(entities={"a": EntityValue(value=1, unit=None, known=True, raw_text="1")}, unknown_entities=[], relationships=[], intent=AxiomType.REDUCTION, confidence=1.0, entity_graph={})

    # 3. Dynamic Skill Acquisition
    learn_res = engine.learn_from_verified_execution(
        target_task_name="SOLVE_DYNAMIC_DOMAIN",
        verified_subtasks=[p1, p2],
        perception=perception,
        verification=verified,
        request_id="req-master-4c"
    )
    assert learn_res.decision == "SKILL_ACTIVATED"
    assert learn_res.validation_passed is True

    # 4. After learning: HTNPlanner decomposes target task successfully!
    plan = planner.decompose_task(unknown_root, context={})
    assert len(plan) == 2
    assert plan[0].name == "IDENTIFY_UNKNOWNS"
    assert plan[1].name == "SOLVE_EQUATION"


def test_hp4c_test_l_invalid_learning_never_pollutes_planner():
    """Test L: Invalid candidate rejected by validator never pollutes MethodRegistry or planner."""
    planner = HTNPlanner()
    engine = SkillLearningEngine(planner=planner)
    unverified = VerificationResult(valid=False, status=VerificationStatus.DISPROVEN, confidence=0.0, proof_trace=None, counterexample=None, z3_model=None, correction_hint=None)
    p1 = Task(id="p1", name="PRIM1", task_type=TaskType.PRIMITIVE)

    res = engine.learn_from_verified_execution("SOLVE_POLLUTE", [p1], None, unverified, request_id="req-invalid")
    assert res.decision == "NO_LEARNING"
    assert len(planner.method_registry.get_methods_for_task("SOLVE_POLLUTE")) == 0

    root = Task(id="r", name="SOLVE_POLLUTE", task_type=TaskType.COMPOUND)
    with pytest.raises(HTNPlanningError):
        planner.decompose_task(root, context={})


def test_skb1_master_persistence_restart_and_anti_tamper(tmp_path):
    """
    SKB-1 MASTER PERSISTENCE ACCEPTANCE TEST:
    1. Learn verified skill in Engine 1 -> persists to disk.
    2. Destroy Engine 1 runtime.
    3. Initialize Engine 2 -> auto-rehydrates and re-validates skill.
    4. Engine 2 decomposes target task successfully without relearning!
    5. Tamper test: Alter file hash -> rehydration rejects tampered record.
    """
    from hsci.learning.persistent_skill_store import PersistentSkillStore

    store_dir = tmp_path / "knowledge"
    store_file = "test_skills.json"

    # PROCESS A: Learn and persist
    planner1 = HTNPlanner()
    store1 = PersistentSkillStore(storage_dir=store_dir, filename=store_file)
    engine1 = SkillLearningEngine(planner=planner1, auto_rehydrate=False)
    engine1.skill_store = store1

    target_task = "SOLVE_SKB_DOMAIN"
    verified = VerificationResult(valid=True, status=VerificationStatus.PROVEN, confidence=1.0, proof_trace=None, counterexample=None, z3_model=None, correction_hint=None)
    p1 = Task(id="p1", name="IDENTIFY_UNKNOWNS", task_type=TaskType.PRIMITIVE)
    p2 = Task(id="p2", name="SOLVE_EQUATION", task_type=TaskType.PRIMITIVE)
    perception = PerceptionMap(entities={}, unknown_entities=[], relationships=[], intent=AxiomType.REDUCTION, confidence=1.0, entity_graph={})

    res = engine1.learn_from_verified_execution(target_task, [p1, p2], perception, verified, request_id="req-skb-1")
    assert res.decision == "SKILL_ACTIVATED"

    # PROCESS B: Destroy process A runtime and rehydrate process B with same signing key
    planner2 = HTNPlanner()
    store2 = PersistentSkillStore(storage_dir=store_dir, filename=store_file, signing_key=store1.signing_key)
    engine2 = SkillLearningEngine(planner=planner2, auto_rehydrate=False)
    engine2.skill_store = store2

    # Before rehydration: planner2 has no method for SOLVE_SKB_DOMAIN
    assert len(planner2.method_registry.get_methods_for_task(target_task)) == 0

    # Rehydrate
    rehydrated_count = engine2.rehydrate_skills()
    assert rehydrated_count == 1
    assert len(planner2.method_registry.get_methods_for_task(target_task)) == 1

    # Decompose task in Process B successfully!
    root = Task(id="r2", name=target_task, task_type=TaskType.COMPOUND)
    plan = planner2.decompose_task(root, context={})
    assert len(plan) == 2
    assert plan[0].name == "IDENTIFY_UNKNOWNS"
    assert plan[1].name == "SOLVE_EQUATION"

    # TAMPER TEST: Modify content without updating SHA-256 or HMAC
    raw_data = store2.load_records_raw()
    raw_data["skills"][0]["target_task_name"] = "SOLVE_MALICIOUS_TASK"
    with open(store2.storage_path, "w", encoding="utf-8") as f:
        import json
        json.dump(raw_data, f)

    # PROCESS C: Load tampered store
    planner3 = HTNPlanner()
    store3 = PersistentSkillStore(storage_dir=store_dir, filename=store_file, signing_key=store1.signing_key)
    engine3 = SkillLearningEngine(planner=planner3, auto_rehydrate=False)
    engine3.skill_store = store3

    rehydrated_count_tampered = engine3.rehydrate_skills()
    assert rehydrated_count_tampered == 0
    assert len(planner3.method_registry.get_methods_for_task("SOLVE_MALICIOUS_TASK")) == 0


def test_skb1_1_forgery_recomputed_sha256_rejected(tmp_path):
    """SKB-1.1 Test C: Forged record with recomputed SHA-256 but missing/wrong HMAC is REJECTED."""
    from hsci.learning.persistent_skill_store import PersistentSkillStore

    store_dir = tmp_path / "knowledge"
    store_file = "forged_skills.json"
    store = PersistentSkillStore(storage_dir=store_dir, filename=store_file)

    forged_record = {
        "skill_id": "method-learned-forged-999",
        "target_task_name": "SOLVE_FORGED_DOMAIN",
        "source": "learned",
        "preconditions": [],
        "subtasks": [{"id": "p1", "name": "IDENTIFY_UNKNOWNS", "task_type": "PRIMITIVE"}],
        "cost": 1.0,
        "source_request_id": "forged-req",
        "provenance_trace": ["Forged Z3 trace"]
    }
    # Recompute old SHA-256 fingerprint
    forged_record["content_hash"] = store._compute_content_hash(forged_record)
    # But leave hmac_signature invalid or absent!
    forged_record["hmac_signature"] = "0000000000000000000000000000000000000000000000000000000000000000"

    payload = {"schema_version": 1, "skills": [forged_record]}
    with open(store.storage_path, "w", encoding="utf-8") as f:
        import json
        json.dump(payload, f)

    planner = HTNPlanner()
    engine = SkillLearningEngine(planner=planner, auto_rehydrate=False)
    engine.skill_store = store

    rehydrated = engine.rehydrate_skills()
    assert rehydrated == 0
    assert len(planner.method_registry.get_methods_for_task("SOLVE_FORGED_DOMAIN")) == 0


def test_skb1_1_static_method_hijacking_prevented():
    """SKB-1.1 Test F: Low-cost learned method CANNOT hijack canonical static method selection."""
    from hsci.core.data_types import MethodSource

    planner = HTNPlanner()
    target = "SOLVE_REDUCTION"

    # Canonical method for SOLVE_REDUCTION exists with cost=1.0
    canonical_methods = planner.method_registry.get_methods_for_task(target)
    assert len(canonical_methods) == 1
    assert canonical_methods[0].source == MethodSource.CANONICAL
    assert canonical_methods[0].cost == 1.0

    # Register a learned method targeting SOLVE_REDUCTION with lower cost 0.1
    p1 = Task(id="p1", name="IDENTIFY_UNKNOWNS", task_type=TaskType.PRIMITIVE)
    learned_method = Method(
        id="method-learned-hijack-attempt",
        target_task_name=target,
        preconditions=[],
        subtasks=[p1],
        cost=0.1,  # Lower cost!
        source=MethodSource.LEARNED
    )
    planner.method_registry.register_method(learned_method)

    # Verify CANONICAL method remains top choice despite higher cost
    methods_after = planner.method_registry.get_methods_for_task(target)
    assert len(methods_after) == 2
    assert methods_after[0].source == MethodSource.CANONICAL
    assert methods_after[0].id == canonical_methods[0].id
    assert methods_after[1].source == MethodSource.LEARNED


def test_skb1_1_privilege_escalation_rejected(tmp_path):
    """SKB-1.1 Test E: Persisted record claiming 'canonical' source is REJECTED."""
    from hsci.learning.persistent_skill_store import PersistentSkillStore

    store_dir = tmp_path / "knowledge"
    store = PersistentSkillStore(storage_dir=store_dir, filename="priv_escalation.json")

    record = {
        "skill_id": "method-learned-escalate",
        "target_task_name": "SOLVE_DYNAMIC",
        "source": "canonical",  # Privilege escalation attempt!
        "preconditions": [],
        "subtasks": [{"id": "p1", "name": "IDENTIFY_UNKNOWNS", "task_type": "PRIMITIVE"}],
        "cost": 1.0,
        "source_request_id": "req-1"
    }
    record["content_hash"] = store._compute_content_hash(record)
    record["hmac_signature"] = store._compute_hmac_signature(record)

    payload = {"schema_version": 1, "skills": [record]}
    with open(store.storage_path, "w", encoding="utf-8") as f:
        import json
        json.dump(payload, f)

    planner = HTNPlanner()
    engine = SkillLearningEngine(planner=planner, auto_rehydrate=False)
    engine.skill_store = store

    rehydrated = engine.rehydrate_skills()
    assert rehydrated == 0


def test_skb1_1_missing_wrong_key_fails_closed(tmp_path):
    """SKB-1.1 Test I/J: Wrong signing key fails closed and rejects persistent skill."""
    from hsci.learning.persistent_skill_store import PersistentSkillStore

    store_dir = tmp_path / "knowledge"
    key1 = b"0" * 32
    key2 = b"1" * 32

    from hsci.core.data_types import MethodSource
    store1 = PersistentSkillStore(storage_dir=store_dir, filename="key_test.json", signing_key=key1)
    p1 = Task(id="p1", name="IDENTIFY_UNKNOWNS", task_type=TaskType.PRIMITIVE)
    m = Method(id="m1", target_task_name="SOLVE_KEY_TASK", subtasks=[p1], source=MethodSource.LEARNED)
    store1.save_skill(m)

    # Attempt rehydration with wrong key2
    store2 = PersistentSkillStore(storage_dir=store_dir, filename="key_test.json", signing_key=key2)
    planner = HTNPlanner()
    engine = SkillLearningEngine(planner=planner, auto_rehydrate=False)
    engine.skill_store = store2

    rehydrated = engine.rehydrate_skills()
    assert rehydrated == 0
    assert len(planner.method_registry.get_methods_for_task("SOLVE_KEY_TASK")) == 0
