import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Set
from hsci.core.data_types import Concept
from hsci.core.kernel import EventBus, CognitiveContext
from hsci.knowledge.knowledge_manager import IKnowledgeManager

logger = logging.getLogger("HSCI.Knowledge.ConceptActivation")

# ─────────────────────────────────────────────
# ACTIVATION MODELS
# ─────────────────────────────────────────────

class ActivatedConcept:
    """Represents an active concept within the reasoning context."""
    def __init__(self, concept: Concept, score: float, source: str, path: List[str], reason: str, confidence: float = 1.0):
        self.concept: Concept = concept
        self.score: float = score
        self.source: str = source
        self.path: List[str] = path
        self.reason: str = reason
        self.confidence: float = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_id": self.concept.id,
            "name": self.concept.name,
            "score": self.score,
            "source": self.source,
            "path": self.path,
            "reason": self.reason,
            "confidence": self.confidence
        }


class ActivatedConceptSet:
    """Group container for all active concepts within a thinking session."""
    def __init__(self, activated_concepts: List[ActivatedConcept]):
        self.concepts: List[ActivatedConcept] = activated_concepts

    def get(self, concept_id: str) -> Optional[ActivatedConcept]:
        return next((ac for ac in self.concepts if ac.concept.id == concept_id), None)

    def to_list(self) -> List[Dict[str, Any]]:
        return [ac.to_dict() for ac in self.concepts]


# ─────────────────────────────────────────────
# ACTIVATION STRATEGIES
# ─────────────────────────────────────────────

class IActivationStrategy(ABC):
    """Abstract interface defining the spreading activation algorithm strategy."""
    @abstractmethod
    def activate(self, seeds: List[str], manager: IKnowledgeManager, config: Dict[str, Any]) -> List[ActivatedConcept]:
        pass


class GraphSpreadingActivationStrategy(IActivationStrategy):
    """
    Spreads activation tokens across relational semantic structures, including
    generalizes_to targets, alias matches, and hierarchical namespaces.
    """
    def activate(self, seeds: List[str], manager: IKnowledgeManager, config: Dict[str, Any]) -> List[ActivatedConcept]:
        max_hops = config.get("maximum_hops", 2)
        decay_rate = config.get("activation_decay", 0.3)
        threshold = config.get("activation_threshold", 0.1)

        activated_map: Dict[str, ActivatedConcept] = {}
        queue: List[Tuple[str, float, List[str], str]] = []  # (concept_id_or_name, current_score, path_so_far, source_seed)

        # Initialize seeds
        for seed in seeds:
            # Resolve seed by name first, then ID
            concept = manager.get_concept_by_name(seed)
            if not concept:
                concept = manager.get_concept(seed)
            
            if concept:
                activated_map[concept.id] = ActivatedConcept(
                    concept=concept,
                    score=1.0,
                    source=seed,
                    path=[concept.id],
                    reason=f"Seed input match for '{seed}'"
                )
                queue.append((concept.id, 1.0, [concept.id], seed))

        # Perform spreading hops
        for hop in range(max_hops):
            next_queue = []
            for current_id, current_score, path, seed_source in queue:
                concept = manager.get_concept(current_id)
                if not concept:
                    continue

                # Locate neighbors
                neighbors: List[Tuple[Concept, str]] = []

                # Neighbor Type 1: Generalization targets
                for target_id in concept.generalizes_to:
                    target = manager.get_concept(target_id)
                    if target:
                        neighbors.append((target, f"Generalization target of '{concept.name}'"))

                # Neighbor Type 2: Namespace siblings
                ns_concepts = manager.search_by_namespace(concept.namespace)
                for ns_c in ns_concepts:
                    if ns_c.id != concept.id:
                        neighbors.append((ns_c, f"Namespace sibling under '{concept.namespace}'"))

                # Neighbor Type 3: Keyword search match
                search_matches = manager.search(concept.name, limit=5)
                for sm_c in search_matches:
                    if sm_c.id != concept.id:
                        neighbors.append((sm_c, f"Semantic index link to '{concept.name}'"))

                # Distribute activation to neighbors
                for neighbor, reason in neighbors:
                    if neighbor.id in path:
                        continue  # Avoid circular loops
                        
                    spread_score = current_score * (1.0 - decay_rate)
                    if spread_score < threshold:
                        continue

                    new_path = path + [neighbor.id]

                    if neighbor.id in activated_map:
                        # Accumulate score if already visited
                        existing = activated_map[neighbor.id]
                        if spread_score > existing.score:
                            existing.score = spread_score
                            existing.path = new_path
                            existing.reason = f"Alternative path: {reason}"
                    else:
                        ac = ActivatedConcept(
                            concept=neighbor,
                            score=spread_score,
                            source=seed_source,
                            path=new_path,
                            reason=reason
                        )
                        activated_map[neighbor.id] = ac
                        next_queue.append((neighbor.id, spread_score, new_path, seed_source))

            queue = next_queue
            if not queue:
                break

        return list(activated_map.values())


# Future strategy placeholders
class SemanticActivationStrategy(IActivationStrategy):
    def activate(self, seeds: List[str], manager: IKnowledgeManager, config: Dict[str, Any]) -> List[ActivatedConcept]:
        raise NotImplementedError()

class EpisodicActivationStrategy(IActivationStrategy):
    def activate(self, seeds: List[str], manager: IKnowledgeManager, config: Dict[str, Any]) -> List[ActivatedConcept]:
        raise NotImplementedError()

class GoalDirectedActivationStrategy(IActivationStrategy):
    def activate(self, seeds: List[str], manager: IKnowledgeManager, config: Dict[str, Any]) -> List[ActivatedConcept]:
        raise NotImplementedError()

class AnalogicalActivationStrategy(IActivationStrategy):
    def activate(self, seeds: List[str], manager: IKnowledgeManager, config: Dict[str, Any]) -> List[ActivatedConcept]:
        raise NotImplementedError()


# ─────────────────────────────────────────────
# CONCEPT ACTIVATION ENGINE
# ─────────────────────────────────────────────

class IConceptActivationEngine(ABC):
    """Unified interface for concept activation and working memory workspace prep."""
    @abstractmethod
    def activate_concepts(self, seeds: List[str], context: CognitiveContext) -> ActivatedConceptSet:
        pass


class ConceptActivationEngine(IConceptActivationEngine):
    """
    Main orchestration engine executing the 8-stage activation pipeline.
    Uses configurable strategies and emits activation notifications.
    """
    def __init__(self, manager: IKnowledgeManager, event_bus: Optional[EventBus] = None, config: Optional[Dict[str, Any]] = None):
        self.manager: IKnowledgeManager = manager
        self.event_bus: Optional[EventBus] = event_bus
        self.config: Dict[str, Any] = config or {
            "maximum_hops": 2,
            "activation_decay": 0.3,
            "activation_threshold": 0.1,
            "maximum_active_concepts": 10,
            "competition_factor": 0.05
        }
        self.strategy: IActivationStrategy = GraphSpreadingActivationStrategy()
        
        # Local execution cache to prevent redundant calculation on identical requests
        self._cache_lock = threading.RLock()
        self._activation_cache: Dict[Tuple[str, ...], ActivatedConceptSet] = {}

        if self.event_bus:
            self._register_listeners()

    def _register_listeners(self) -> None:
        """Flushes local cache on store updates."""
        def on_store_mutated(context: CognitiveContext) -> None:
            with self._cache_lock:
                self._activation_cache.clear()
                
        for event in ["ConceptUpdated", "ConceptMerged", "ConceptSplit"]:
            self.event_bus.subscribe(event, on_store_mutated)

    def activate_concepts(self, seeds: List[str], context: CognitiveContext) -> ActivatedConceptSet:
        """Executes the 8-stage pipeline to propagate activations and populate working memory."""
        cache_key = tuple(sorted(seeds))
        with self._cache_lock:
            if cache_key in self._activation_cache:
                # Cache Hit
                cached = self._activation_cache[cache_key]
                self._populate_working_memory(cached, context)
                return cached

        # Stage 1-3: Load and perform spreading activation via the selected strategy
        activated_list = self.strategy.activate(seeds, self.manager, self.config)

        # Stage 4: Apply decay (decay already integrated in strategy hop calculations)
        # Stage 5: Apply competitive inhibition
        max_score = max((ac.score for ac in activated_list), default=0.0)
        comp_factor = self.config.get("competition_factor", 0.05)
        
        for ac in activated_list:
            if ac.score < 1.0:  # Do not inhibit seed nodes directly
                ac.score = max(0.0, ac.score - (max_score * comp_factor))

        # Stage 6: Filter out below threshold
        threshold = self.config.get("activation_threshold", 0.1)
        pruned_list = [ac for ac in activated_list if ac.score >= threshold]

        # Stage 7: Rank and limit
        pruned_list.sort(key=lambda ac: ac.score, reverse=True)
        max_active = self.config.get("maximum_active_concepts", 10)
        ranked_list = pruned_list[:max_active]

        result_set = ActivatedConceptSet(ranked_list)

        # Stage 8: Populate WorkingMemory
        self._populate_working_memory(result_set, context)

        # Cache result
        with self._cache_lock:
            self._activation_cache[cache_key] = result_set

        # Emit events
        if self.event_bus:
            for ac in ranked_list:
                self._emit_event("ConceptActivated", ac.concept)
            self._emit_event("ActivationCompleted", None)

        return result_set

    def _populate_working_memory(self, result_set: ActivatedConceptSet, context: CognitiveContext) -> None:
        """Syncs the ActivatedConceptSet values into context.working_memory structures."""
        wm = context.working_memory
        
        # Clear previous activation context values to prevent cross-request contamination
        wm.activation_field.clear()
        wm.attention_buffer.clear()

        # Update ActivationField and AttentionBuffer
        for ac in result_set.concepts:
            wm.activation_field.set_activation(ac.concept.id, ac.score)
            wm.attention_buffer.add_salience(ac.concept.id, ac.score)
            
            # Save concept object mapping reference into active skills list or custom attribute
            if ac.concept.id not in wm.active_skills:
                wm.active_skills.append(ac.concept.id)

    def _emit_event(self, event_name: str, concept: Optional[Concept]) -> None:
        """Helper to publish events onto the EventBus."""
        if self.event_bus:
            try:
                ctx = CognitiveContext(
                    request_id=f"cae-{int(time.time())}",
                    session_id="system",
                    stimulus=f"event:{event_name}"
                )
                if concept:
                    ctx.working_memory.concept = concept
                self.event_bus.emit(event_name, ctx)
            except Exception as e:
                logger.error(f"Failed to publish cae event '{event_name}': {e}")
