import re
from typing import Dict, List, Any, Optional
from uuid import uuid4
from datetime import datetime
from hsci.core.data_types import PerceptionMap, Expression, ProofTrace, Concept, AxiomType, EntityValue

class ConceptExtractor:
    """
    Extracts abstract concepts from proven interactions.
    Uses structural induction — finds the minimal rule explaining the proof.
    """

    def extract(
        self,
        perception: PerceptionMap,
        solution: Expression,
        proof_trace: ProofTrace,
        knowledge_base: Any
    ) -> Concept:

        # Abstract away specific values using entity names
        abstract_rule = self._abstract_values(
            perception.entities, str(solution.value)
        )

        # Build Z3 template
        z3_template = abstract_rule.replace("=", "==")

        # Domain and Intent
        domain = perception.domain
        intent = perception.intent

        # Generate name
        name = self._generate_name(abstract_rule, domain)

        return Concept(
            id=str(uuid4()),
            name=name,
            axiom_type=intent,
            abstract_rule=abstract_rule,
            z3_template=z3_template,
            domain=domain,
            learned_from_domains=[domain],
            strength=0.5,
            proof_count=1,
            created_at=datetime.now(),
            last_used=datetime.now(),
            required_entities=self._extract_required_entities(abstract_rule),
            z3_verified=True
        )

    def _abstract_values(self, entities: Dict[str, EntityValue], solution_str: str) -> str:
        """Replaces literal values in the solution with entity names."""
        abstracted = solution_str
        # Sort entities by value string length descending to avoid partial matches
        sorted_items = sorted(
            [(k, str(v.value)) for k, v in entities.items() if v.known and v.value is not None],
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for name, val_str in sorted_items:
            abstracted = abstracted.replace(val_str, name)
        
        return abstracted

    def _generate_name(self, rule: str, domain: str) -> str:
        domain_upper = domain.upper()
        if "+" in rule: return f"{domain_upper}_ADDITION"
        if "-" in rule and "*" in rule: return f"{domain_upper}_DEDUCTION"
        if "*" in rule: return f"{domain_upper}_PRODUCT"
        if "/" in rule: return f"{domain_upper}_RATIO"
        return f"{domain_upper}_RULE_{uuid4().hex[:4].upper()}"

    def _extract_required_entities(self, rule: str) -> List[str]:
        """Extracts alphabetic variable names from the rule."""
        return re.findall(r'[a-zA-Z_]\w*', rule)
