
import os
import sys
import json
import logging

# Add project root to path
sys.path.append(os.getcwd())

from hnsds.brain.cognitive_core import HyperSymbolicBrain

def harvest_and_prime():
    """
    INVENTION: Knowledge Harvester.
    Automatically primes the brain with a library of foundational lessons.
    This is the foundation for Continuous Learning.
    """
    logging.basicConfig(level=logging.INFO)
    brain = HyperSymbolicBrain()
    
    # Foundational Lesson Bank (Math, Code, Logic)
    lessons = [
        # --- MATH & REDUCTION ---
        {
            "name": "ALGEBRAIC_BALANCE",
            "stimulus": "If x + a = b, then x = b - a",
            "axiom": "REDUCTION"
        },
        {
            "name": "SUMMATION_PRINCIPLE",
            "stimulus": "The total of multiple entities is the sum of their individual values",
            "axiom": "REDUCTION"
        },
        # --- CODING & SYNTHESIS ---
        {
            "name": "FUNCTIONAL_STRUCTURE",
            "stimulus": "Write a function to perform an operation on input parameters",
            "axiom": "SYNTHESIS"
        },
        {
            "name": "DATA_MODELING",
            "stimulus": "Create a data structure to represent a real-world entity",
            "axiom": "SYNTHESIS"
        },
        # --- LOGIC & COMPOSITION ---
        {
            "name": "TRANSITIVE_RELATION",
            "stimulus": "If A is B and B is C, then A is C",
            "axiom": "COMPOSITION"
        },
        {
            "name": "SPATIAL_CONSTRAINT",
            "stimulus": "Entity X is next to Entity Y in a sequence",
            "axiom": "COMPOSITION"
        }
    ]

    print("==================================================")
    print("   HSCI KNOWLEDGE HARVESTER: Continuous Priming   ")
    print("==================================================\n")

    for lesson in lessons:
        print(f"Ingesting Lesson: {lesson['name']}...")
        brain.teach(lesson['stimulus'], lesson['name'], lesson['axiom'])
    
    print("\n✅ Knowledge Harvest Complete. The brain's IQ has been expanded.")

if __name__ == "__main__":
    harvest_and_prime()
