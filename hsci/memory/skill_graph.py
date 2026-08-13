from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any

from hsci.core.data_types import (
    Method, MethodSource, Task, TaskType, Precondition, PlanningContext
)


class SkillRelationType(Enum):
    DECOMPOSES_TO = "DECOMPOSES_TO"
    DEPENDS_ON    = "DEPENDS_ON"
    PRODUCES      = "PRODUCES"
    REQUIRES      = "REQUIRES"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"


@dataclass
class SkillNode:
    """
    Typed, declarative graph representation of an authenticated HTN Method.
    Contains ZERO executable code or Python lambdas.
    """
    skill_id: str
    method_id: str
    target_task_name: str
    source: MethodSource
    preconditions: List[Precondition] = field(default_factory=list)
    subtasks: List[Task] = field(default_factory=list)
    cost: float = 1.0
    description: str = ""
    provenance_trace: List[str] = field(default_factory=list)
    verification_status: str = "VERIFIED"


@dataclass
class SkillEdge:
    source_node_id: str
    target_node_id: str
    relation_type: SkillRelationType
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillGraph:
    """
    LAYER 6A / SCG-1: Persistent Skill Graph & Compositional Retrieval.
    Maintains a structured, indexed graph of canonical and authenticated learned HTN methods.
    Provides O(1) indexed target lookups, typed relationship tracking, and compositional candidate discovery.
    """

    def __init__(self):
        self.nodes: Dict[str, SkillNode] = {}
        self.edges: List[SkillEdge] = []
        
        # Indexed Lookup Structures
        self._target_task_index: Dict[str, List[str]] = {}
        self._subtask_index: Dict[str, List[str]] = {}

    def add_verified_method(self, method: Method, provenance: Optional[List[str]] = None) -> SkillNode:
        """
        Constructs and indexes a SkillNode from a trusted, validated Method instance.
        Updates target and subtask indexes deterministically.
        """
        node_id = f"node-{method.id}"
        node = SkillNode(
            skill_id=node_id,
            method_id=method.id,
            target_task_name=method.target_task_name,
            source=method.source,
            preconditions=method.preconditions,
            subtasks=method.subtasks,
            cost=method.cost,
            description=method.description,
            provenance_trace=provenance or ["Trusted MethodRegistry"]
        )

        self.nodes[node_id] = node

        # Index by Target Task Name
        if method.target_task_name not in self._target_task_index:
            self._target_task_index[method.target_task_name] = []
        if node_id not in self._target_task_index[method.target_task_name]:
            self._target_task_index[method.target_task_name].append(node_id)

        # Index by Subtask Names & build DECOMPOSES_TO edges
        for st in method.subtasks:
            if st.name not in self._subtask_index:
                self._subtask_index[st.name] = []
            if node_id not in self._subtask_index[st.name]:
                self._subtask_index[st.name].append(node_id)

            edge = SkillEdge(
                source_node_id=node_id,
                target_node_id=f"task-{st.name}",
                relation_type=SkillRelationType.DECOMPOSES_TO
            )
            self.edges.append(edge)

        return node

    def find_for_target(self, target_task_name: str) -> List[SkillNode]:
        """
        O(1) indexed target lookup. Returns relevant SkillNodes sorted deterministically:
        1. CANONICAL source before LEARNED source
        2. Lowest cost first
        3. Deterministic method ID comparison
        """
        node_ids = self._target_task_index.get(target_task_name, [])
        nodes = [self.nodes[nid] for nid in node_ids if nid in self.nodes]
        nodes.sort(key=lambda n: (0 if n.source == MethodSource.CANONICAL else 1, n.cost, n.method_id))
        return nodes

    def clear(self) -> None:
        self.nodes.clear()
        self.edges.clear()
        self._target_task_index.clear()
        self._subtask_index.clear()


class SkillRetriever:
    """
    SCG-05: Retrieves candidate SkillNodes for a given goal and PlanningContext deterministically.
    Enforces CANONICAL > LEARNED authority and evaluates context precondition admissibility.
    """

    def __init__(self, skill_graph: SkillGraph):
        self.skill_graph = skill_graph

    def retrieve(
        self,
        target_task_name: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[SkillNode]:
        candidates = self.skill_graph.find_for_target(target_task_name)
        if not candidates:
            return []

        from hsci.memory.skill_lifecycle import SkillLifecycleManager
        lifecycle_mgr = SkillLifecycleManager()

        # Filter and rank candidates
        admissible = []
        for node in candidates:
            # SCG4.1: Check lifecycle eligibility
            method_id = getattr(node, "method_id", getattr(node, "id", node.skill_id))
            if not lifecycle_mgr.is_eligible_for_retrieval(method_id, node.source):
                continue

            # Check preconditions against context if present
            if context and node.preconditions:
                pre_ok = True
                for pre in node.preconditions:
                    if pre.predicate in context:
                        if pre.required_state is not None and context[pre.predicate] != pre.required_state:
                            pre_ok = False
                            break
                    elif pre.required_state is not None:
                        pre_ok = False
                        break
                if not pre_ok:
                    continue

            admissible.append(node)
            if len(admissible) >= limit:
                break

        return admissible


class SkillComposer:
    """
    SCG-06 / SCG-07: Discovers candidate compositional skill chains across the SkillGraph.
    Enforces cycle detection, maximum composition depth, candidate explosion limits, and deterministic ordering.
    """

    MAX_COMPOSITION_DEPTH = 10
    MAX_CANDIDATE_CHAINS = 50

    def __init__(self, skill_graph: SkillGraph):
        self.skill_graph = skill_graph

    def compose_candidate_chains(
        self,
        target_task_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[List[SkillNode]]:
        """
        Recursively composes candidate skill chains for a target task.
        Returns a list of multi-step SkillNode chains sorted deterministically.
        """
        retriever = SkillRetriever(self.skill_graph)
        chains: List[List[SkillNode]] = []
        visited_tasks: Set[str] = set()

        self._compose_recursive(
            target_task_name=target_task_name,
            current_chain=[],
            visited_tasks=visited_tasks,
            context=context or {},
            all_chains=chains,
            retriever=retriever,
            depth=0
        )

        from hsci.memory.skill_utility import GraphPlanEvaluator
        evaluator = GraphPlanEvaluator()
        ranked_chains = evaluator.rank_candidate_chains(chains)

        # SCG4.1: Filter out ineligible candidate chains (e.g. score < 0 or rank == 99 containing DEPRECATED skills)
        eligible_chains = []
        for chain in ranked_chains:
            score = evaluator.evaluate_chain(chain)
            if score.authority_rank != 99 and score.utility_score >= -500.0:
                eligible_chains.append(chain)

        # Ensure deep compositional multi-level chains (e.g. 3-node chains) are preserved over partial 1-node prefixes
        eligible_chains.sort(key=lambda c: (-len(c), -sum(getattr(n, "cost", 1.0) for n in c)))
        return eligible_chains[:self.MAX_CANDIDATE_CHAINS]

    def _compose_recursive(
        self,
        target_task_name: str,
        current_chain: List[SkillNode],
        visited_tasks: Set[str],
        context: Dict[str, Any],
        all_chains: List[List[SkillNode]],
        retriever: SkillRetriever,
        depth: int
    ) -> None:
        if depth > self.MAX_COMPOSITION_DEPTH or len(all_chains) >= self.MAX_CANDIDATE_CHAINS:
            return

        if target_task_name in visited_tasks:
            return  # Cycle detection

        nodes = retriever.retrieve(target_task_name, context=context)
        if not nodes:
            return

        for node in nodes:
            branch_visited = set(visited_tasks)
            branch_visited.add(target_task_name)
            new_chain = list(current_chain) + [node]

            # Check if all subtasks are primitives or recursively composable
            subtasks_resolved = True
            for st in node.subtasks:
                if st.task_type == TaskType.COMPOUND:
                    sub_nodes = retriever.retrieve(st.name, context=context)
                    if sub_nodes:
                        self._compose_recursive(
                            target_task_name=st.name,
                            current_chain=new_chain,
                            visited_tasks=branch_visited,
                            context=context,
                            all_chains=all_chains,
                            retriever=retriever,
                            depth=depth + 1
                        )
                    else:
                        subtasks_resolved = False

            if subtasks_resolved:
                all_chains.append(new_chain)
