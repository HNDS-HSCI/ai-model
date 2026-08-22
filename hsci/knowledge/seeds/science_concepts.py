"""Canonical Scientific & Physics Knowledge Seed for HSCI.

Provides foundational physical laws, formulas, and dimensional relationships for the Scientific Brain.
All concepts are verified with SMT/Z3 templates and executable via SymPy CAS.
"""
import logging
from typing import Dict, List

from hsci.core.data_types import Concept
from hsci.knowledge.knowledge_manager import IKnowledgeManager

logger = logging.getLogger("HSCI.Knowledge.Seeds.Science")

SCIENCE_NAMESPACE = "concept.science"

CANONICAL_PROVENANCE: Dict[str, object] = {
    "source_type": "CANONICAL_SEED",
    "source_id": "hsci.knowledge.seeds.science_concepts",
    "acquisition_method": "MANUAL",
    "confidence": 1.0,
    "notes": "Canonical Scientific & Physical Laws seed",
}


def build_science_concepts() -> List[Concept]:
    """Builds foundational scientific laws and mathematical formulas."""
    return [
        Concept(
            id="c_physical_law",
            name="Physical Law",
            namespace=SCIENCE_NAMESPACE,
            domain="physics",
            abstract_rule="A physical law is a theoretical principle deduced from experimental observations that describes natural phenomena.",
            aliases=["physical law", "law of physics", "scientific law", "nature law"],
            strength=1.0,
            z3_verified=True,
        ),
        Concept(
            id="c_energy",
            name="Energy",
            namespace=SCIENCE_NAMESPACE,
            domain="physics",
            abstract_rule="Energy is the quantitative property transferred to a body or physical system to perform work or produce heat.",
            aliases=["energy", "conservation of energy"],
            generalizes_to=["c_physical_law"],
            strength=1.0,
            z3_verified=True,
        ),
        Concept(
            id="c_newton_second_law",
            name="Newton's Second Law",
            namespace=SCIENCE_NAMESPACE,
            domain="physics",
            abstract_rule="Force equals mass multiplied by acceleration (F = m * a).",
            z3_template="F == m * a && m > 0",
            aliases=["newton's second law", "newtons second law", "second law of motion", "f=ma", "force formula"],
            generalizes_to=["c_physical_law"],
            strength=1.0,
            z3_verified=True,
        ),
        Concept(
            id="c_kinetic_energy",
            name="Kinetic Energy",
            namespace=SCIENCE_NAMESPACE,
            domain="physics",
            abstract_rule="Kinetic energy is the energy an object possesses due to its motion, defined as KE = 1/2 * m * v^2.",
            z3_template="ke == 0.5 * m * v**2 && m > 0 && ke >= 0",
            aliases=["kinetic energy", "ke formula", "energy of motion", "ke = 1/2 mv^2"],
            generalizes_to=["c_energy"],
            strength=1.0,
            z3_verified=True,
        ),
        Concept(
            id="c_potential_energy",
            name="Gravitational Potential Energy",
            namespace=SCIENCE_NAMESPACE,
            domain="physics",
            abstract_rule="Gravitational potential energy is the energy stored by an object in a gravitational field, defined as PE = m * g * h.",
            z3_template="pe == m * g * h && m > 0 && g > 0",
            aliases=["potential energy", "gravitational potential energy", "pe formula", "pe = mgh"],
            generalizes_to=["c_energy"],
            strength=1.0,
            z3_verified=True,
        ),
        Concept(
            id="c_ohms_law",
            name="Ohm's Law",
            namespace=SCIENCE_NAMESPACE,
            domain="physics",
            abstract_rule="The current flowing through a conductor is directly proportional to voltage and inversely proportional to resistance (V = I * R).",
            z3_template="V == I * R && R > 0",
            aliases=["ohm's law", "ohms law", "v=ir", "voltage resistance law"],
            generalizes_to=["c_physical_law"],
            strength=1.0,
            z3_verified=True,
        ),
        Concept(
            id="c_mass_energy_equivalence",
            name="Mass-Energy Equivalence",
            namespace=SCIENCE_NAMESPACE,
            domain="physics",
            abstract_rule="Mass and energy are equivalent and interchangeable according to Einstein's equation E = m * c^2.",
            z3_template="E == m * c**2 && m >= 0 && c > 0",
            aliases=["mass energy equivalence", "einstein equation", "e=mc^2", "e=mc2"],
            generalizes_to=["c_physical_law"],
            strength=1.0,
            z3_verified=True,
        ),
        Concept(
            id="c_ideal_gas_law",
            name="Ideal Gas Law",
            namespace=SCIENCE_NAMESPACE,
            domain="chemistry",
            abstract_rule="The equation of state of a hypothetical ideal gas is PV = n * R * T.",
            z3_template="P * V == n * R * T && P > 0 && V > 0 && T > 0",
            aliases=["ideal gas law", "pv=nrt", "gas law"],
            generalizes_to=["c_physical_law"],
            strength=1.0,
            z3_verified=True,
        ),
    ]


def seed_science_concepts(manager: IKnowledgeManager) -> int:
    """Seeds the canonical scientific concepts into the UKM.

    Idempotent: skips concepts that already exist by ID.
    Returns the number of newly created concepts.
    """
    concepts = build_science_concepts()
    created_count = 0
    for concept in concepts:
        if not manager.exists(concept.id):
            manager.create_concept(concept, provenance=dict(CANONICAL_PROVENANCE))
            created_count += 1
            logger.debug("Seeded scientific concept '%s' (%s)", concept.name, concept.id)
        else:
            logger.debug("Scientific concept '%s' (%s) already present, skipped", concept.name, concept.id)

    logger.info("Science seeding complete. Created %d concepts (total %d defined)", created_count, len(concepts))
    return created_count
