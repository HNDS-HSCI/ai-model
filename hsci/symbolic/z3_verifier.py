import z3
from typing import Dict, Any, List, Optional
from hsci.core.data_types import (
    PerceptionMap, Expression, VerificationResult, ProofTrace, Concept, 
    VerificationStatus, ProofStep, EntityValue
)
from hsci.symbolic.z3_templates import Z3_TEMPLATES

from hsci.core.config import SystemConfig

class Z3VerificationEngine:
    """
    LAYER 4: Z3 Verification Engine
    The Truth Gatekeeper.
    Every candidate solution must pass here.
    """

    def __init__(self):
        self.config = SystemConfig()

    def verify(
        self,
        candidate: Expression,
        perception: PerceptionMap,
        concept: Optional[Concept],
        ctx: Optional[z3.Context] = None
    ) -> VerificationResult:
        
        # Ensure we have a context
        if ctx is None:
            ctx = z3.Context()
            
        solver = z3.Solver(ctx=ctx)
        solver.set("timeout", self.config.z3_timeout_ms)

        if not hasattr(candidate, 'value') or candidate.value is False:
             return VerificationResult(
                valid=False,
                status=VerificationStatus.DISPROVEN,
                counterexample={"error": "Invalid candidate expression"},
                correction_hint="Check SolutionBuilder mapping.",
                confidence=0.0,
                proof_trace=None,
                z3_model=None
            )

        try:
            # Step 1: Build Z3 constraints from perception (using .value)
            known_constraints = self._build_constraints(
                perception.entities, ctx
            )

            # Step 2: Add all constraints
            for constraint in known_constraints:
                solver.add(constraint)
            
            # Add solution constraint
            solver.add(candidate.value)

            # Step 4: Check satisfiability
            result = solver.check()

            if result == z3.sat:
                model = solver.model()
                trace = self._extract_proof_trace(model, perception.entities, concept, candidate)
                return VerificationResult(
                    valid=True,
                    status=VerificationStatus.PROVEN,
                    proof_trace=trace,
                    z3_model=model,
                    confidence=1.0,
                    counterexample=None,
                    correction_hint=None
                )

            elif result == z3.unsat:
                return VerificationResult(
                    valid=False,
                    status=VerificationStatus.DISPROVEN,
                    counterexample={"status": "unsat"},
                    correction_hint="The proposed solution contradicts known constraints.",
                    confidence=0.0,
                    proof_trace=None,
                    z3_model=None
                )

            else:  # unknown (timeout)
                return VerificationResult(
                    valid=False,
                    status=VerificationStatus.TIMEOUT,
                    counterexample=None,
                    correction_hint="Z3 timeout — problem may be undecidable",
                    confidence=0.0,
                    proof_trace=None,
                    z3_model=None
                )
        except Exception as e:
            return VerificationResult(
                valid=False,
                status=VerificationStatus.UNKNOWN,
                counterexample={"error": str(e)},
                correction_hint="System-level error during verification. Check logs.",
                confidence=0.0,
                proof_trace=None,
                z3_model=None
            )

    def _build_constraints(self, entities: Dict[str, EntityValue], ctx: z3.Context) -> List[z3.BoolRef]:
        constraints = []
        for name, ev in entities.items():
            if ev.known and ev.value is not None:
                z3_var = z3.Real(name, ctx=ctx)
                constraints.append(z3_var == float(ev.value))
        return constraints

    def _extract_proof_trace(self, model: z3.ModelRef, entities: Dict[str, EntityValue], concept: Optional[Concept], candidate: Expression) -> ProofTrace:
        assignments = {d.name(): str(model[d]) for d in model.decls()}
        
        # Simple step extraction for demonstration
        steps = [ProofStep(
            step_number=1,
            operation=concept.name if concept else "GENERIC_SOLVE",
            input_values={k: v.value for k, v in entities.items() if v.known},
            output_value=assignments,
            concept_applied=concept.name if concept else "UNKNOWN"
        )]

        return ProofTrace(
            steps=steps,
            variable_assignments=assignments,
            concepts_applied=[concept.name] if concept else [],
            structural_pattern=concept.abstract_rule if concept else "verified_pattern"
        )
