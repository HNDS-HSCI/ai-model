# -*- coding: utf-8 -*-
"""Quick integration test for HSCI brain fixes."""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from hsci.core.rir_loop import RIRLoop

brain = RIRLoop(use_llm=False)

tests = [
    ("hello", "Greeting"),
    ("what is 5 + 3", "Math"),
    ("What is quantum computing", "Knowledge"),
    ("find velocity if distance = 100 and time = 5", "Physics"),
    ("What is the capital of India", "Capital"),
    ("Tell me about gravity", "Science"),
    ("Explain DNA", "Biology"),
    ("calculate 100 * 3", "Arithmetic"),
]

for query, label in tests:
    print(f"\n{'='*60}")
    print(f"TEST [{label}]: {query}")
    print(f"{'='*60}")
    try:
        result = brain.process(query)
        print(result)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

print(f"\n{'='*60}")
print("ALL TESTS COMPLETE")
print(f"{'='*60}")
