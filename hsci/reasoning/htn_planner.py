from typing import List, Dict, Optional, Set, Any, Union, Tuple
from hsci.core.data_types import (
    PerceptionMap, SubGoal, AxiomType, Task, TaskType, Method, MethodSource, Operator, Precondition, Postcondition, PlanningFailure, PlanningContext, PlanningTrace
)


class HTNPlanningError(Exception):
    """
    Structured Exception representing a controlled HTN planning/decomposition failure.
    Carries a detailed PlanningFailure payload for Phase 4B Reflection.
    """
    def __init__(self, failure: PlanningFailure):
        super().__init__(f"HTN Planning Failure on task '{failure.failed_task_name}' ({failure.failed_task_id}): {failure.reason}")
        self.failure = failure



class MethodRegistry:
    """
    Deterministic registry for HTN Methods.
    Manages registration, lookup, and deterministic priority ordering of methods.
    """
    def __init__(self):
        self._methods_by_target: Dict[str, List[Method]] = {}
        self._registered_ids: Set[str] = set()

    def register_method(self, method: Method) -> bool:
        """
        Registers a new decomposition method. Returns True if registered, False if duplicate.
        """
        if method.id in self._registered_ids:
            return False
        
        self._registered_ids.add(method.id)
        if method.target_task_name not in self._methods_by_target:
            self._methods_by_target[method.target_task_name] = []
        
        # Insert maintaining deterministic priority ordering:
        # 1. CANONICAL methods before LEARNED methods
        # 2. Lowest cost first
        # 3. Deterministic method ID string comparison
        methods = self._methods_by_target[method.target_task_name]
        methods.append(method)
        methods.sort(key=lambda m: (0 if m.source == MethodSource.CANONICAL else 1, m.cost, m.id))
        return True

    def get_methods_for_task(self, target_task_name: str) -> List[Method]:
        """
        Retrieves all registered methods for a given target compound task in deterministic order
        (CANONICAL first, sorted by cost and ID).
        """
        return list(self._methods_by_target.get(target_task_name, []))

    def get_method(self, method_id: str) -> Optional[Method]:
        """
        Retrieves a method by its unique method_id. Returns None if not registered.
        """
        for methods in self._methods_by_target.values():
            for m in methods:
                if m.id == method_id:
                    return m
        return None

    def has_methods(self, target_task_name: str) -> bool:
        return bool(self._methods_by_target.get(target_task_name))

    def clear(self) -> None:
        self._methods_by_target.clear()
        self._registered_ids.clear()


class OperatorRegistry:
    """
    Deterministic registry for Primitive HTN Operators.
    Maps primitive task names to executable operator definitions.
    """
    def __init__(self):
        self._operators_by_task: Dict[str, Operator] = {}

    def register_operator(self, operator: Operator) -> bool:
        """
        Registers a primitive operator. Rejects duplicates for the same primitive task name.
        """
        if operator.primitive_task_name in self._operators_by_task:
            return False
        self._operators_by_task[operator.primitive_task_name] = operator
        return True

    def get_operator(self, primitive_task_name: str) -> Optional[Operator]:
        """
        Retrieves the operator definition for a primitive task name.
        """
        return self._operators_by_task.get(primitive_task_name)

    def has_operator(self, primitive_task_name: str) -> bool:
        return primitive_task_name in self._operators_by_task

    def clear(self) -> None:
        self._operators_by_task.clear()


class HTNPlanner:
    """
    Hierarchical Task Network planner.
    Decomposes complex goals into solvable sub-goals.
    Provides backward-compatible static decomposition while housing Method and Operator registries.
    """

    DECOMPOSITION_RULES = {
        AxiomType.REDUCTION: [
            ("IDENTIFY_UNKNOWNS", "Identify variables to solve for."),
            ("BUILD_EQUATION", "Construct a mathematical equation."),
            ("SOLVE_EQUATION", "Solve the mathematical equation.")
        ],
        AxiomType.COMPOSITION: [
            ("EXTRACT_ENTITIES", "Extract all relevant entities."),
            ("IDENTIFY_RELATIONSHIPS", "Determine relationships between entities."),
            ("BUILD_CONSTRAINT_NETWORK", "Construct a network of constraints."),
            ("SOLVE_NETWORK", "Solve the network of constraints.")
        ],
        AxiomType.SYNTHESIS: [
            ("DEFINE_INPUTS_OUTPUTS", "Define inputs and expected outputs."),
            ("IDENTIFY_ALGORITHM_PATTERN", "Identify suitable algorithmic patterns."),
            ("BUILD_PROCEDURE", "Construct the procedural logic."),
            ("VERIFY_INVARIANTS", "Verify algorithmic invariants.")
        ],
        AxiomType.TRANSFORMATION: [
            ("PARSE_SOURCE_STRUCTURE", "Parse the source information structure."),
            ("IDENTIFY_TARGET_STRUCTURE", "Identify the target information structure."),
            ("MAP_TRANSFORMATION_RULES", "Map rules for transformation."),
            ("APPLY_TRANSFORMATION", "Apply transformation rules.")
        ],
    }

    MAX_DEPTH = 10

    def __init__(
        self,
        method_registry: Optional[MethodRegistry] = None,
        operator_registry: Optional[OperatorRegistry] = None,
        max_depth: int = 10,
        verifier: Optional[Any] = None,
        skill_graph: Optional[Any] = None,
        lifecycle_manager: Optional[Any] = None
    ):
        self.method_registry = method_registry or MethodRegistry()
        self.operator_registry = operator_registry or OperatorRegistry()
        self.max_depth = max_depth
        self.verifier = verifier
        from hsci.memory.skill_graph import SkillGraph
        self.skill_graph = skill_graph if skill_graph is not None else SkillGraph()
        from hsci.memory.skill_lifecycle import SkillLifecycleManager
        self.lifecycle_manager = lifecycle_manager or SkillLifecycleManager()
        self._bootstrap_default_domain()
        if method_registry is not None or skill_graph is not None:
            self.sync_skill_graph()

    def _is_method_lifecycle_eligible(self, method: Method) -> bool:
        """
        SCG4.1: Enforces system-wide lifecycle eligibility invariant for direct MethodRegistry methods.
        CANONICAL methods are permanently immune (always True).
        LEARNED methods are checked against SkillLifecycleManager (DEPRECATED -> False).
        """
        source = getattr(method, "source", MethodSource.CANONICAL)
        if source == MethodSource.CANONICAL or getattr(source, "value", source) == "canonical":
            return True
        if self.lifecycle_manager is not None:
            # Check using method.id
            return self.lifecycle_manager.is_eligible_for_retrieval(method.id, source)
        return True

    def sync_skill_graph(self) -> None:
        """
        Populates the SkillGraph from trusted, active methods in MethodRegistry.
        """
        self.skill_graph.clear()
        for methods in self.method_registry._methods_by_target.values():
            for method in methods:
                if self._is_method_lifecycle_eligible(method):
                    self.skill_graph.add_verified_method(method)

    def _bootstrap_default_domain(self) -> None:
        """
        Populates MethodRegistry and OperatorRegistry with default domain rules derived from DECOMPOSITION_RULES.
        """
        for axiom_type, steps in self.DECOMPOSITION_RULES.items():
            compound_task_name = f"SOLVE_{axiom_type.value}"
            subtasks = []
            for step_name, desc in steps:
                subtask = Task(
                    id=f"task-{step_name.lower()}",
                    name=step_name,
                    task_type=TaskType.PRIMITIVE,
                    axiom_type=axiom_type
                )
                subtasks.append(subtask)
                
                # Register default primitive operator
                self.operator_registry.register_operator(
                    Operator(
                        id=f"op-{step_name.lower()}",
                        primitive_task_name=step_name,
                        description=desc,
                        execution_handler=f"handle_{step_name.lower()}"
                    )
                )
                
            method = Method(
                id=f"method-{axiom_type.value.lower()}-default",
                target_task_name=compound_task_name,
                subtasks=subtasks,
                cost=1.0,
                description=f"Default decomposition method for {axiom_type.value}"
            )
            self.method_registry.register_method(method)
        
        self.sync_skill_graph()

    def decompose_task(self, task: Task, context: Optional[Union[PlanningContext, Dict[str, Any], Any]] = None) -> List[Task]:
        """
        Public API for recursive HTN task decomposition with verified preconditions and alternative method search.
        Accepts request-scoped PlanningContext, WorkingMemory, or dictionary facts.
        Reduces a task (whether PRIMITIVE or COMPOUND) into a flattened sequence of PRIMITIVE tasks.
        Raises HTNPlanningError if depth is exceeded, cycle is detected, preconditions fail, or all methods fail.
        """
        primitives, _ = self.decompose_task_with_trace(task, context)
        return primitives

    def decompose_task_with_trace(
        self,
        task: Task,
        context: Optional[Union[PlanningContext, Dict[str, Any], Any]] = None
    ) -> Tuple[List[Task], PlanningTrace]:
        """
        SCG3-01 / SCG3-02: Public API returning primitive tasks along with a request-local PlanningTrace.
        Enforces exact candidate outcome attribution without global telemetry leakage.
        """
        if context is None:
            ctx_dict: Dict[str, Any] = {}
        elif isinstance(context, PlanningContext):
            ctx_dict = context.to_dict()
        elif hasattr(context, "build_planning_context"):
            ctx_dict = context.build_planning_context().to_dict()
        elif isinstance(context, dict):
            ctx_dict = context
        else:
            ctx_dict = {}

        trace = PlanningTrace()
        primitives = self._decompose_task_recursive(task, current_depth=0, visited_tasks=set(), context=ctx_dict, trace=trace)
        return primitives, trace


    def _verify_preconditions(
        self,
        method: Method,
        task: Task,
        context: Dict[str, Any],
        current_depth: int
    ) -> Optional[PlanningFailure]:
        """
        Verification Boundary: Evaluates a Method's preconditions against current request-local planning context.
        Returns None if all preconditions pass (or if no preconditions exist).
        Returns a PlanningFailure payload if any precondition is rejected.
        """
        if not method.preconditions:
            return None

        # 1. Verification Engine (Z3) integration path if callable/configured
        if self.verifier is not None:
            # If verifier has explicit verify_preconditions capability
            if hasattr(self.verifier, "verify_preconditions"):
                res = self.verifier.verify_preconditions(method.preconditions, context)
                if not res.get("valid", False):
                    return PlanningFailure(
                        failed_task_id=task.id,
                        failed_task_name=task.name,
                        attempted_methods=[method.id],
                        failed_precondition=res.get("failed_precondition"),
                        z3_counterexample=res.get("counterexample"),
                        depth_reached=current_depth,
                        reason=res.get("reason", "UNSATISFIABLE_PRECONDITION")
                    )
                return None
            
            # Direct Z3VerificationEngine verify() fallback for Expression / Z3 objects in preconditions
            if hasattr(self.verifier, "verify"):
                for pre in method.preconditions:
                    if isinstance(pre.required_state, bool) and pre.required_state is False:
                        return PlanningFailure(
                            failed_task_id=task.id,
                            failed_task_name=task.name,
                            attempted_methods=[method.id],
                            failed_precondition=pre,
                            depth_reached=current_depth,
                            reason=f"Precondition '{pre.predicate}' failed required boolean state"
                        )

        # 2. Native Typed Precondition Evaluation against request-local context facts
        for pre in method.preconditions:
            key = pre.predicate
            # If context has explicit state for this predicate key
            if key in context:
                actual_val = context[key]
                if pre.required_state is not None and actual_val != pre.required_state:
                    return PlanningFailure(
                        failed_task_id=task.id,
                        failed_task_name=task.name,
                        attempted_methods=[method.id],
                        failed_precondition=pre,
                        z3_counterexample={"predicate": key, "expected": pre.required_state, "actual": actual_val},
                        depth_reached=current_depth,
                        reason=f"Precondition '{key}' unsat: expected {pre.required_state}, got {actual_val}"
                    )
            elif pre.required_state is not None:
                # Required state was specified but key is absent from facts context
                return PlanningFailure(
                    failed_task_id=task.id,
                    failed_task_name=task.name,
                    attempted_methods=[method.id],
                    failed_precondition=pre,
                    depth_reached=current_depth,
                    reason=f"Precondition predicate '{key}' missing from planning context"
                )

        return None

    def _decompose_task_recursive(
        self,
        task: Task,
        current_depth: int,
        visited_tasks: Set[str],
        context: Dict[str, Any],
        trace: Optional[PlanningTrace] = None
    ) -> List[Task]:
        """
        Internal recursive decomposition engine with verified preconditions & alternative method search.
        - PRIMITIVE tasks terminate recursion and return [task].
        - COMPOUND tasks query MethodRegistry, verify candidate method preconditions, iterate candidates by cost,
          and recursively reduce subtasks.
        - If a candidate method fails preconditions or structural decomposition, its branch plan is rolled back
          and the next candidate method is attempted.
        - If all candidate methods fail, a structured HTNPlanningError with attempted_methods is raised.
        """
        if current_depth > self.max_depth:
            failure = PlanningFailure(
                failed_task_id=task.id,
                failed_task_name=task.name,
                depth_reached=current_depth,
                reason=f"Max decomposition depth ({self.max_depth}) exceeded"
            )
            raise HTNPlanningError(failure)

        if task.task_type == TaskType.PRIMITIVE:
            return [task]

        if task.task_type == TaskType.COMPOUND:
            methods = self.method_registry.get_methods_for_task(task.name)

            # Active-branch cycle protection
            if task.id in visited_tasks:
                failure = PlanningFailure(
                    failed_task_id=task.id,
                    failed_task_name=task.name,
                    depth_reached=current_depth,
                    reason=f"Cycle detected in task decomposition for task ID '{task.id}' ({task.name})"
                )
                raise HTNPlanningError(failure)

            # Branch-local visited set
            branch_visited = set(visited_tasks)
            branch_visited.add(task.id)

            attempted_methods: List[str] = []
            last_method_failure_reason = "No direct methods registered"

            # Alternative Method Search & Backtracking Loop
            for method in methods:
                # Step 0: Direct Lifecycle Gate Check (SCG4.1 invariant: DEPRECATED learned skills blocked)
                if not self._is_method_lifecycle_eligible(method):
                    last_method_failure_reason = f"Learned method '{method.id}' is DEPRECATED (Excluded by lifecycle policy)"
                    continue

                attempted_methods.append(method.id)

                # Step 1: Precondition Verification Boundary Check
                pre_failure = self._verify_preconditions(method, task, context, current_depth)
                if pre_failure is not None:
                    # Precondition invalid / UNSAT -> skip subtask expansion and attempt next Method
                    last_method_failure_reason = pre_failure.reason
                    continue

                # Step 2: Structural Subtask Decomposition
                candidate_plan: List[Task] = []
                method_success = True
                local_trace = PlanningTrace()

                for subtask in method.subtasks:
                    try:
                        sub_primitives = self._decompose_task_recursive(
                            subtask,
                            current_depth=current_depth + 1,
                            visited_tasks=branch_visited,
                            context=context,
                            trace=local_trace
                        )
                        candidate_plan.extend(sub_primitives)
                    except HTNPlanningError as err:
                        # Transactional Backtracking: discard candidate_plan for this method
                        method_success = False
                        last_method_failure_reason = err.failure.reason
                        break

                if method_success:
                    # Method succeeded! Commit local_trace to request trace.
                    if trace is not None:
                        if method.id not in trace.executed_method_ids:
                            trace.executed_method_ids.append(method.id)
                        for mid in local_trace.executed_method_ids:
                            if mid not in trace.executed_method_ids:
                                trace.executed_method_ids.append(mid)
                        for nid in local_trace.executed_graph_node_ids:
                            if nid not in trace.executed_graph_node_ids:
                                trace.executed_graph_node_ids.append(nid)
                    return candidate_plan

            # ─────────────────────────────────────────────────────────────
            # SCG-2 GRAPH FALLBACK SEARCH INTEGRATION
            # If all direct registered methods fail (or none exist), attempt graph-assisted composition
            # ─────────────────────────────────────────────────────────────
            graph_plan = self._attempt_graph_fallback(
                task=task,
                current_depth=current_depth,
                visited_tasks=visited_tasks,
                context=context,
                trace=trace
            )
            if graph_plan is not None:
                return graph_plan

            # All candidate methods and graph composition failed: raise structured HTNPlanningError
            if not attempted_methods and not methods:
                failure_reason = f"No decomposition method registered for compound task '{task.name}'"
            elif not attempted_methods and methods:
                failure_reason = f"All direct candidate methods excluded by lifecycle policy for task '{task.name}'. Last failure: {last_method_failure_reason}"
            else:
                failure_reason = f"All candidate methods failed for task '{task.name}'. Last failure: {last_method_failure_reason}"
            
            failure = PlanningFailure(
                failed_task_id=task.id,
                failed_task_name=task.name,
                attempted_methods=attempted_methods,
                depth_reached=current_depth,
                reason=failure_reason
            )
            raise HTNPlanningError(failure)

    def _attempt_graph_fallback(
        self,
        task: Task,
        current_depth: int,
        visited_tasks: Set[str],
        context: Dict[str, Any],
        trace: Optional[PlanningTrace] = None
    ) -> Optional[List[Task]]:
        """
        SCG2-01 - SCG2-07: Fallback Graph Search Integration.
        Invokes SkillComposer to discover multi-skill candidate chains across SkillGraph.
        Evaluates chains transactionally and recursively decomposes subtasks.
        """
        if not hasattr(self, "skill_graph") or self.skill_graph is None:
            return None

        # Loop Prevention: Prevent planner <-> graph infinite recursion loop
        graph_visited_key = f"graph-{task.name}"
        if graph_visited_key in visited_tasks:
            return None

        from hsci.memory.skill_graph import SkillComposer
        composer = SkillComposer(self.skill_graph)

        try:
            candidate_chains = composer.compose_candidate_chains(task.name, context=context)
        except Exception:
            return None

        if not candidate_chains:
            return None

        branch_visited = set(visited_tasks)
        branch_visited.add(graph_visited_key)
        branch_visited.add(task.id)

        # Iterate composed candidate chains
        from hsci.memory.skill_utility import SkillUtilityStore
        utility_store = getattr(self, "utility_store", SkillUtilityStore())

        for idx, chain in enumerate(candidate_chains):
            chain_plan: List[Task] = []
            chain_success = True
            local_trace = PlanningTrace(graph_fallback_used=True, selected_candidate_id=f"cand-{idx}")

            for node in chain:
                # Validate preconditions for each SkillNode in chain against context
                for pre in node.preconditions:
                    if pre.predicate in context:
                        if pre.required_state is not None and context[pre.predicate] != pre.required_state:
                            chain_success = False
                            break
                    elif pre.required_state is not None:
                        chain_success = False
                        break
                if not chain_success:
                    break

                node_id = getattr(node, "method_id", getattr(node, "id", node.skill_id if hasattr(node, "skill_id") else str(node)))
                if node_id not in local_trace.executed_graph_node_ids:
                    local_trace.executed_graph_node_ids.append(node_id)

                # Decompose subtasks of this SkillNode recursively
                for subtask in node.subtasks:
                    try:
                        sub_primitives = self._decompose_task_recursive(
                            subtask,
                            current_depth=current_depth + 1,
                            visited_tasks=branch_visited,
                            context=context,
                            trace=local_trace
                        )
                        chain_plan.extend(sub_primitives)
                    except HTNPlanningError:
                        chain_success = False
                        break
                if not chain_success:
                    break

            if chain_success and chain_plan:
                # Commit local_trace to request trace
                if trace is not None:
                    trace.graph_fallback_used = True
                    trace.selected_candidate_id = local_trace.selected_candidate_id
                    for nid in local_trace.executed_graph_node_ids:
                        if nid not in trace.executed_graph_node_ids:
                            trace.executed_graph_node_ids.append(nid)
                    for mid in local_trace.executed_method_ids:
                        if mid not in trace.executed_method_ids:
                            trace.executed_method_ids.append(mid)
                return chain_plan
            else:
                # Record planning failure telemetry ONLY for this failed candidate chain's nodes
                for node in chain:
                    method_id = getattr(node, "method_id", getattr(node, "id", node.skill_id if hasattr(node, "skill_id") else str(node)))
                    utility_store.record_outcome(method_id, "PLANNING_FAILURE")

        return None


    def decompose(self, perception: PerceptionMap) -> List[SubGoal]:
        """
        Backward-compatible public API.
        Decomposes the intent in perception into a sequence of sub-goals.
        """
        steps = self.DECOMPOSITION_RULES.get(perception.intent, [("UNKNOWN_INTENT_HANDLING", "Handle unknown or unclassifiable intent.")])
        sub_goals = []
        for name, description in steps:
            sub_goal = SubGoal(
                name=name,
                description=description,
                required_entities=list(perception.entities.keys()),
                target_entity=perception.unknown_entities[0] if perception.unknown_entities else "result",
                axiom_type=perception.intent
            )
            sub_goals.append(sub_goal)
        return sub_goals


