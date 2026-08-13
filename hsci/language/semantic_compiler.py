import re
import z3
import logging
from typing import Dict, Any, List, Optional, Tuple, Union

from hsci.core.data_types import (
    SemanticIR, RelationTriple, ASTNode, VariableNode, ConstantNode, BinaryOpNode,
    BinaryOperator, SemanticCompilationFailure, Task, TaskType, AxiomType, PlanningContext
)

logger = logging.getLogger("HSCI.Language.SemanticCompiler")

# ─────────────────────────────────────────────
# NSG-2 DECLARED SEMANTIC LEXICON & NORMALIZERS
# ─────────────────────────────────────────────


SEMANTIC_LEXICON = {
    # Possession concept
    "has": "POSSESSION",
    "owns": "POSSESSION",
    "possesses": "POSSESSION",
    "holds": "POSSESSION",
    "starts with": "POSSESSION",

    # Acquisition concept
    "gets": "ACQUIRE",
    "receives": "ACQUIRE",
    "obtains": "ACQUIRE",
    "acquires": "ACQUIRE",
    "buys": "ACQUIRE",

    # Relational Comparison concept
    "greater than": "GREATER_THAN",
    "larger than": "GREATER_THAN",
    "above": "GREATER_THAN",
    "exceeds": "GREATER_THAN",
    "less than": "LESS_THAN",
    "below": "LESS_THAN",
    "smaller than": "LESS_THAN",
}

NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20
}

class NumberNormalizer:
    @staticmethod
    def parse_number(token: str) -> Optional[Union[int, float]]:
        token_clean = token.lower().strip()
        if token_clean in NUMBER_WORDS:
            return NUMBER_WORDS[token_clean]
        try:
            if "." in token_clean:
                return float(token_clean)
            return int(token_clean)
        except ValueError:
            return None


class Z3ASTCompiler:
    """
    Safely compiles a declarative ASTNode graph into a Z3 SMT expression.
    Contains ZERO eval() or exec() calls.
    """

    def compile_node(self, node: ASTNode, z3_vars: Dict[str, Any], ctx: Optional[z3.Context] = None) -> Any:
        if isinstance(node, VariableNode):
            if node.name not in z3_vars:
                z3_vars[node.name] = z3.Real(node.name, ctx=ctx)
            return z3_vars[node.name]

        if isinstance(node, ConstantNode):
            return node.value

        if isinstance(node, BinaryOpNode):
            left_z3 = self.compile_node(node.left, z3_vars, ctx=ctx)
            right_z3 = self.compile_node(node.right, z3_vars, ctx=ctx)

            if node.op == BinaryOperator.ADD:
                return left_z3 + right_z3
            elif node.op == BinaryOperator.SUB:
                return left_z3 - right_z3
            elif node.op == BinaryOperator.MUL:
                return left_z3 * right_z3
            elif node.op == BinaryOperator.DIV:
                return left_z3 / right_z3
            elif node.op == BinaryOperator.EQ:
                return left_z3 == right_z3
            elif node.op == BinaryOperator.GT:
                return left_z3 > right_z3
            elif node.op == BinaryOperator.LT:
                return left_z3 < right_z3
            elif node.op == BinaryOperator.GTE:
                return left_z3 >= right_z3
            elif node.op == BinaryOperator.LTE:
                return left_z3 <= right_z3
            elif node.op == BinaryOperator.AND:
                return z3.And(left_z3, right_z3)
            elif node.op == BinaryOperator.OR:
                return z3.Or(left_z3, right_z3)

        raise ValueError(f"Unknown AST node type: {type(node)}")


class SemanticCompiler:
    """
    LAYER 0: Neurosymbolic Semantic Grounding & Intent Compiler (NSG-2)
    Parses unstructured text statements into typed SemanticIR, ASTNodes, and Z3 expressions.
    Uses reusable lexical, grammatical, and role-binding mechanisms.
    NO internal arithmetic solver leakage (e.g. 7 + 4 = 11 is strictly forbidden inside the parser).
    """

    def __init__(self):
        self.z3_ast_compiler = Z3ASTCompiler()
        self.num_normalizer = NumberNormalizer()

    def compile(self, text: str) -> Union[SemanticIR, SemanticCompilationFailure]:
        """
        Parses text into a deterministic SemanticIR representation.
        """
        if not text or not text.strip():
            return SemanticCompilationFailure(
                failed_input=text,
                reason="Empty input string",
                category="UNSUPPORTED_STRUCTURE"
            )

        clean_text = text.strip()
        text_lower = clean_text.lower()

        # Negation Guard (Explicit Polarity Rejection / NOT Node Construction)
        if " not " in f" {text_lower} " or "n't " in text_lower:
            neg_match = re.search(r'(\b[a-z]\b|\b\w+\b)\s+is\s+not\s+(greater\s+than|exceeds)\s+(\d+|\w+)', clean_text, re.IGNORECASE)
            if neg_match:
                var_name = neg_match.group(1)
                num_val = self.num_normalizer.parse_number(neg_match.group(3))
                if num_val is not None:
                    var_node = VariableNode(var_name)
                    gt_node = BinaryOpNode(BinaryOperator.GT, var_node, ConstantNode(num_val))
                    # Negated AST
                    ast_constraints = [BinaryOpNode(BinaryOperator.EQ, gt_node, ConstantNode(False))]
                    return SemanticIR(
                        raw_text=clean_text,
                        entities={var_name: f"NOT >{num_val}"},
                        relations=[RelationTriple(subject=var_name, relation="NOT_GREATER_THAN", object=num_val)],
                        ast_constraints=ast_constraints,
                        target_goal="SOLVE_COMPOSITION",
                        domain="logic",
                        intent="COMPOSITION",
                        confidence=0.95
                    )
            return SemanticCompilationFailure(
                failed_input=clean_text,
                reason="Negation clause cannot be safely grounded into positive relation",
                category="UNSUPPORTED_STRUCTURE"
            )

        entities: Dict[str, Any] = {}
        relations: List[RelationTriple] = []
        ast_constraints: List[ASTNode] = []
        provenance: Dict[str, str] = {}

        # 1. Active / Passive Ownership & Lexical Possession ("John has 5 apples.", "5 apples belong to John.")
        poss_verbs = r'has|owns|possesses|holds'
        own_match = re.search(r'^(\b[A-Z][a-z]+\b)\s+(' + poss_verbs + r')\s+(\d+|\w+)\s+(\w+)\.?$', clean_text, re.IGNORECASE)
        passive_match = re.search(r'^(\d+|\w+)\s+(\w+)\s+belong\s+to\s+(\b[A-Z][a-z]+\b)\.?$', clean_text, re.IGNORECASE)

        if own_match or passive_match:
            if own_match:
                subj = own_match.group(1).capitalize()
                qty_raw = own_match.group(3)
                obj = own_match.group(4).lower()
                verb_found = own_match.group(2).lower()
            else:
                qty_raw = passive_match.group(1)
                obj = passive_match.group(2).lower()
                subj = passive_match.group(3).capitalize()
                verb_found = "belong to"

            qty = self.num_normalizer.parse_number(qty_raw)
            if qty is not None:
                entities["subject"] = subj
                entities["item"] = obj
                entities[obj] = qty
                entities["op_1"] = qty
                entities["a"] = qty
                entities["result"] = None

                norm_concept = SEMANTIC_LEXICON.get(verb_found, "POSSESSION")
                relations.append(RelationTriple(subject=subj, relation=norm_concept, object=qty))
                ast_constraints.append(BinaryOpNode(BinaryOperator.EQ, VariableNode(obj), ConstantNode(qty)))

                return SemanticIR(
                    raw_text=clean_text,
                    entities=entities,
                    relations=relations,
                    ast_constraints=ast_constraints,
                    target_goal="SOLVE_REDUCTION",
                    domain="arithmetic",
                    intent="REDUCTION",
                    confidence=0.95
                )

        # 2. Relational Comparison & Exceeds Grammar ("x is greater than 5 and less than 10.", "x exceeds 5.")
        comp_match = re.search(r'(\b[a-z]\b|\b\w+\b)\s+(?:is\s+greater\s+than|exceeds|is\s+above)\s+(\d+|\w+)(?:\s+and\s+(?:is\s+)?less\s+than\s+(\d+|\w+))?', clean_text, re.IGNORECASE)
        if comp_match:
            var_name = comp_match.group(1)
            gt_val = self.num_normalizer.parse_number(comp_match.group(2))
            lt_val = self.num_normalizer.parse_number(comp_match.group(3)) if comp_match.group(3) else None

            if gt_val is not None:
                var_node = VariableNode(var_name)
                ast_constraints.append(BinaryOpNode(BinaryOperator.GT, var_node, ConstantNode(gt_val)))
                relations.append(RelationTriple(subject=var_name, relation="GREATER_THAN", object=gt_val))

                if lt_val is not None:
                    ast_constraints.append(BinaryOpNode(BinaryOperator.LT, var_node, ConstantNode(lt_val)))
                    relations.append(RelationTriple(subject=var_name, relation="LESS_THAN", object=lt_val))

                entities[var_name] = f">{gt_val}"

                return SemanticIR(
                    raw_text=clean_text,
                    entities=entities,
                    relations=relations,
                    ast_constraints=ast_constraints,
                    target_goal="SOLVE_COMPOSITION",
                    domain="logic",
                    intent="COMPOSITION",
                    confidence=0.95
                )

        # 3. Multi-Step Lexical Composition with Bounded Coreference ("Ravi possesses 7 notebooks and receives 4 additional notebooks.")
        acq_verbs = r'receives|gets|acquires|obtains|buys'
        arith_match = re.search(r'(\b[A-Z][a-z]+\b)\s+(' + poss_verbs + r')\s+(\d+|\w+)\s+(\w+)(?:\.|\s+(?:and|,)?)\s*(?:He|She|They|\1)?\s*(' + acq_verbs + r')\s+(\d+|\w+)\s+(?:additional|more)?\s*\4?\.?', clean_text, re.IGNORECASE)
        if arith_match:
            subject = arith_match.group(1).capitalize()
            initial_qty = self.num_normalizer.parse_number(arith_match.group(3))
            item_name = arith_match.group(4).lower()
            verb_acq = arith_match.group(5).lower() if arith_match.group(5) else None
            additional_qty = self.num_normalizer.parse_number(arith_match.group(6)) if arith_match.group(6) else 0

            if initial_qty is not None and additional_qty is not None:
                # STRICT ARCHITECTURAL RULE: NO ARITHMETIC SOLVING (7+4=11) INSIDE SEMANTIC COMPILER!
                entities["subject"] = subject
                entities["item"] = item_name
                entities["initial_quantity"] = initial_qty
                entities["change_quantity"] = additional_qty
                entities["op_1"] = initial_qty
                entities["op_2"] = additional_qty
                entities["a"] = initial_qty
                entities["b"] = additional_qty
                entities["result"] = None

                norm_poss = SEMANTIC_LEXICON.get(arith_match.group(2).lower(), "POSSESSION")
                relations.append(RelationTriple(subject=subject, relation=norm_poss, object=initial_qty))
                if additional_qty > 0:
                    acq_concept = SEMANTIC_LEXICON.get(verb_acq, "ACQUIRE")
                    relations.append(RelationTriple(subject=subject, relation=acq_concept, object=additional_qty))

                var_init = VariableNode("initial_quantity")
                var_change = VariableNode("change_quantity")
                var_total = VariableNode("total_quantity")

                ast_constraints.append(BinaryOpNode(BinaryOperator.EQ, var_init, ConstantNode(initial_qty)))
                if additional_qty > 0:
                    ast_constraints.append(BinaryOpNode(BinaryOperator.EQ, var_change, ConstantNode(additional_qty)))
                    ast_constraints.append(BinaryOpNode(BinaryOperator.EQ, var_total, BinaryOpNode(BinaryOperator.ADD, var_init, var_change)))

                return SemanticIR(
                    raw_text=clean_text,
                    entities=entities,
                    relations=relations,
                    ast_constraints=ast_constraints,
                    target_goal="SOLVE_REDUCTION",
                    domain="arithmetic",
                    intent="REDUCTION",
                    confidence=0.95,
                    provenance_spans=provenance
                )






        # Unsupported structure fallback
        return SemanticCompilationFailure(
            failed_input=clean_text,
            reason="No deterministic semantic pattern matched for input text",
            category="UNSUPPORTED_STRUCTURE"
        )

    def compile_to_htn_root_task(self, ir: SemanticIR) -> Task:
        """
        Compiles a SemanticIR into a root HTN Task for HTNPlanner.
        """
        goal_name = ir.target_goal or f"SOLVE_{ir.intent or 'REDUCTION'}"
        return Task(
            id=f"root-{goal_name.lower()}",
            name=goal_name,
            task_type=TaskType.COMPOUND,
            axiom_type=AxiomType(ir.intent) if ir.intent in [a.value for a in AxiomType] else AxiomType.REDUCTION
        )

    def compile_to_planning_context(self, ir: SemanticIR, request_id: str = "") -> PlanningContext:
        """
        Compiles a SemanticIR into a request-isolated PlanningContext for WorkingMemory.
        """
        facts = dict(ir.entities)
        for r in ir.relations:
            facts[f"RELATION_{r.subject}_{r.relation}"] = r.object

        return PlanningContext(
            facts=facts,
            entities=ir.entities,
            active_concepts=[r.relation for r in ir.relations],
            intent=ir.intent,
            request_id=request_id
        )
