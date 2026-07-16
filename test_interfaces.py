import sys
import os

# Force UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hsci.core.rir_loop import RIRLoop

brain = RIRLoop(use_llm=False)

tests = [
    "calculate 25 + 75",
    "what is velocity if distance = 100 and time = 5",
    "find tax amount if salary = 50000 and rate = 0.3",
    "hello",
]

print("\n=== HSCI Interface Test ===\n")
for query in tests:
    out, s = brain.process_internal(query)
    response = brain.response_bridge.generate(out, query, s.domain)
    status = "VERIFIED" if out.is_verified else "UNVERIFIED"
    print(f"Query   : {query}")
    print(f"Status  : {status}")
    print(f"Response: {response[:120]}")
    print()

stats = brain.get_neural_stats()
clf = stats['classifier']
print("=== Neural Stats ===")
print(f"Proof count   : {clf['proof_count']}")
print(f"Weight version: {stats['weight_version']}")
print(f"Avg loss      : {clf['avg_loss']:.4f}")
print()
print("=== All 3 User Interfaces Available ===")
print("1. CLI      -> python hsci_cli.py")
print("2. Web UI   -> python brain_api.py  then open  http://localhost:8000")
print("3. REST API -> POST /process | GET /health | GET /neural-stats")
