"""Canonical Object-Oriented Programming (OOP) knowledge seed.

Sprint VS-1 requires the Understanding Engine to resolve a non-empty seed concept
for the demonstrator question *"Explain what a Java interface is."*. Concept
resolution (`UnderstandingEngine`) only matches concepts already present in the UKM
`ConceptStore`, so a small canonical set of OOP concepts must be seeded first.

This module inserts that set through the existing `KnowledgeManager` public API.
It does NOT access SQLite directly and it does NOT define a new schema — it only
uses relationship types (``generalizes_to``, ``namespace``, ``aliases``) already
supported by the `Concept` dataclass and UKM tables.

Provenance is recorded as ``CANONICAL_SEED`` so these concepts are distinguishable
from learned concepts, honouring the canonical/learned distinction.

The seed is idempotent: running it twice never creates duplicate concepts, because
each concept carries a deterministic ID and is skipped if already present.
"""
import logging
from typing import Dict, List

from hsci.core.data_types import Concept
from hsci.knowledge.knowledge_manager import IKnowledgeManager

logger = logging.getLogger("HSCI.Knowledge.Seeds.OOP")

# Shared namespace so the concepts cohabit (drives namespace-based reasoning and
# spreading activation between siblings).
OOP_NAMESPACE = "concept.oop"

# Provenance marking these concepts as canonical (not learned).
CANONICAL_PROVENANCE: Dict[str, object] = {
    "source_type": "CANONICAL_SEED",
    "source_id": "hsci.knowledge.seeds.oop_concepts",
    "acquisition_method": "MANUAL",
    "confidence": 1.0,
    "notes": "VS-1 canonical OOP knowledge seed",
}


def build_oop_concepts() -> List[Concept]:
    """Builds the canonical OOP concept objects with their relationships.

    Deterministic IDs guarantee idempotency across repeated runs. Relationships
    use only ``generalizes_to`` (concept-hierarchy links) already supported by the
    UKM schema:

        Java Interface -> Interface
        Interface      -> Abstraction
        Class          -> Abstraction
        Method         -> Class
    """
    return [
        Concept(
            id="c_abstraction",
            name="Abstraction",
            namespace=OOP_NAMESPACE,
            domain="programming",
            abstract_rule="Abstraction hides implementation detail behind a simpler contract.",
        ),
        Concept(
            id="c_class",
            name="Class",
            namespace=OOP_NAMESPACE,
            domain="programming",
            generalizes_to=["c_abstraction"],
            abstract_rule="A class is a blueprint bundling state and behaviour for objects.",
        ),
        Concept(
            id="c_method",
            name="Method",
            namespace=OOP_NAMESPACE,
            domain="programming",
            generalizes_to=["c_class"],
            abstract_rule="A method is a named behaviour defined on a class.",
        ),
        Concept(
            id="c_interface",
            name="Interface",
            namespace=OOP_NAMESPACE,
            domain="programming",
            aliases=["interface"],
            generalizes_to=["c_abstraction"],
            abstract_rule="An interface is a contract of method signatures without implementation.",
        ),
        Concept(
            id="c_java_interface",
            name="Java Interface",
            namespace=OOP_NAMESPACE,
            domain="programming",
            aliases=["java interface"],
            generalizes_to=["c_interface"],
            abstract_rule=(
                "A Java interface is a reference type declaring abstract methods (and "
                "constants) that implementing classes must fulfil."
            ),
        ),
    ]


def seed_oop_concepts(manager: IKnowledgeManager) -> Dict[str, List[str]]:
    """Idempotently seeds the canonical OOP concepts into the UKM.

    Returns a summary dict ``{"created": [...], "skipped": [...]}`` naming the
    concept IDs created on this run versus those already present.

    Idempotency: a concept is skipped when its deterministic ID already exists,
    so a second invocation creates nothing and never duplicates.
    """
    created: List[str] = []
    skipped: List[str] = []

    for concept in build_oop_concepts():
        if manager.exists(concept.id):
            skipped.append(concept.id)
            continue
        # Defensive: also skip if the canonical name is already active under a
        # different ID, so the seed never conflicts with pre-existing knowledge.
        existing_by_name = manager.get_concept_by_name(concept.name)
        if existing_by_name is not None:
            skipped.append(concept.id)
            continue

        manager.create_concept(concept, provenance=dict(CANONICAL_PROVENANCE))
        created.append(concept.id)

    logger.info(
        "OOP canonical seed complete. Created=%s Skipped=%s", created, skipped
    )
    return {"created": created, "skipped": skipped}
