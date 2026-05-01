import z3
from hsci.core.rir_loop import RIRLoop

loop = RIRLoop()
text = "If base is 1000 and tax is 15%, find the tax_amount"

print(f"INPUT: {text}")

# Layer 0: Language Bridge
structured = loop.language_bridge.parse(text)
print(f"\nLAYER 0 (Structured): {structured}")

# Layer 1: Neural Perceiver
perception = loop.perceiver.perceive(structured)
print(f"\nLAYER 1 (Perception): {perception}")

# Layer 2: Knowledge
knowledge = loop.knowledge_base.query(perception)
print(f"\nLAYER 2 (Knowledge): Found {len(knowledge.direct_matches)} concepts")

# Layer 3: Reasoning
ctx = z3.Context()
plan = loop.reasoning_engine.reason(perception, knowledge, ctx=ctx)
print(f"\nLAYER 3 (Plan): {plan.concepts_used}")
print(f"CANDIDATE: {plan.candidate_solution}")

# Layer 4: Verification
verification = loop.verifier.verify(plan.candidate_solution, perception, plan.primary_concept, ctx=ctx)
print(f"\nLAYER 4 (Verification): Valid={verification.valid}, Status={verification.status}")
if verification.counterexample:
    print(f"COUNTEREXAMPLE: {verification.counterexample}")
