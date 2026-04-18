import z3
from typing import List, Dict, Any, Optional
from hsci.core.data_types import SubGoal, Concept, Expression, EntityValue
from hsci.symbolic.z3_templates import Z3_TEMPLATES

class SolutionBuilder:
    """
    Builds a candidate solution (Expression) based on decomposed sub-goals,
    assigned concepts, and extracted entities.
    v3.1: Improved semantic mapping to avoid generic operand collisions.
    """

    def build(self,
              sub_goals: List[SubGoal],
              concept_assignments: Dict[str, Concept],
              entities: Dict[str, EntityValue],
              ctx: Optional[z3.Context] = None) -> Expression:
        if not sub_goals or not concept_assignments:
             return Expression(value=False, concepts_used=[])

        # Identify target concept
        assigned_concept = None
        for goal_id in [sg.id for sg in sub_goals]:
             if goal_id in concept_assignments:
                  assigned_concept = concept_assignments[goal_id]
                  break

        if assigned_concept and assigned_concept.name in Z3_TEMPLATES:
            z3_func = Z3_TEMPLATES[assigned_concept.name]
            
            try:
                # 1. Identify result key (unknown)
                result_key = next((k for k, v in entities.items() if not v.known), "result")
                
                # 2. Filter operands (knowns)
                # Prioritize keys that are NOT 'op_n' if they exist
                all_knowns = [k for k, v in entities.items() if v.known and k != result_key]
                semantic_knowns = [k for k in all_knowns if not k.startswith("op_")]
                generic_knowns = [k for k in all_knowns if k.startswith("op_")]
                
                operand_keys = semantic_knowns + generic_knowns
                z3_vars = {k: z3.Real(k, ctx=ctx) for k in entities.keys()}

                if assigned_concept.name in ["ADDITION", "SUBTRACTION", "MULTIPLICATION", "DIVISION"]:
                    if len(operand_keys) >= 2:
                        mapped_args = {
                            "a": z3_vars[operand_keys[0]],
                            "b": z3_vars[operand_keys[1]],
                            "result": z3_vars[result_key]
                        }
                        z3_expr = z3_func(**mapped_args)
                        return Expression(value=z3_expr, concepts_used=[assigned_concept.name])

                elif assigned_concept.name == "PERCENTAGE":
                    if len(operand_keys) >= 2:
                        # Find rate: looks like 'tax', 'rate', or is between 0 and 1
                        rate_key = next((k for k in operand_keys if any(x in k.lower() for x in ['tax', 'rate', 'discount', 'percent'])), None)
                        if not rate_key:
                             rate_key = next((k for k in operand_keys if entities[k].value is not None and 0 < entities[k].value < 1), operand_keys[1])
                        
                        base_key = next((k for k in operand_keys if k != rate_key), operand_keys[0])
                        
                        ev_rate = entities[rate_key]
                        # Use decimal template if parser normalized it (e.g. 15% -> 0.15)
                        if ev_rate.unit == 'percentage' or (ev_rate.value is not None and ev_rate.value < 1.0):
                             z3_expr = Z3_TEMPLATES["PERCENTAGE_DECIMAL"](base=z3_vars[base_key], rate=z3_vars[rate_key], result=z3_vars[result_key])
                        else:
                             z3_expr = z3_func(base=z3_vars[base_key], rate=z3_vars[rate_key], result=z3_vars[result_key])
                        
                        return Expression(value=z3_expr, concepts_used=[assigned_concept.name])

                elif assigned_concept.name == "DISTANCE_RATE_TIME":
                    d_key = result_key
                    r_key = next((k for k in operand_keys if any(x in k.lower() for x in ['velocity', 'rate', 'speed'])), operand_keys[0])
                    t_key = next((k for k in operand_keys if k != r_key), operand_keys[1] if len(operand_keys)>1 else operand_keys[0])
                    return Expression(value=z3_func(d=z3_vars[d_key], r=z3_vars[r_key], t=z3_vars[t_key]), concepts_used=[assigned_concept.name])

                # Generic 2-operand fallback
                if len(operand_keys) >= 2:
                     import inspect
                     sig = inspect.signature(z3_func)
                     arg_names = [p for p in sig.parameters.keys()]
                     if 'result' in arg_names and len(arg_names) == 3:
                          mapped_args = {
                              arg_names[0]: z3_vars[operand_keys[0]],
                              arg_names[1]: z3_vars[operand_keys[1]],
                              "result": z3_vars[result_key]
                          }
                          return Expression(value=z3_func(**mapped_args), concepts_used=[assigned_concept.name])

            except Exception:
                pass

        return Expression(value=False, concepts_used=[])
