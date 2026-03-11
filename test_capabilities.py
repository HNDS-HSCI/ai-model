import sys
import os
import logging
from hnsds.brain.cognitive_core import HyperSymbolicBrain

def run_iq_test():
    """
    Automated Continuous Intelligence Benchmark.
    Fails the build if the system loses its axiomatic reasoning capabilities.
    """
    # Clear old mental intelligence cache to ensure a fresh test environment
    if os.path.exists("mental_intelligence.json"):
        os.remove("mental_intelligence.json")

    # Mute standard logs for clean test output
    logging.getLogger("CognitiveCore").setLevel(logging.CRITICAL)
    logging.getLogger("CognitiveAwareness").setLevel(logging.CRITICAL)

    brain = HyperSymbolicBrain()
    failed_tests = 0

    print("==================================================")
    print("   HSCI CONTINUOUS INTELLIGENCE VERIFICATION      ")
    print("==================================================\n")

    # TEST 1: INSTRUCTIONAL PRIMING
    print("[TEST 1] Priming the Brain (Instructional Learning)")
    lesson = "teach: find the total if base is x and bonus is y | SALARY_SUMMATION | REDUCTION"
    try:
        res = brain.process(lesson)
        assert "Learned concept" in res
        print("  ✅ Pass: Brain successfully ingested new concept.\n")
    except AssertionError:
        print(f"  ❌ Fail: Could not learn concept. Output: {res}\n")
        failed_tests += 1

    # TEST 2: ZERO-SHOT GENERALIZATION & MATH PROOF
    print("[TEST 2] Analogical Generalization & Z3 Verification")
    stimulus = "Calculate the total result if the base is 1000 and the bonus is 500."
    try:
        # Re-instantiate brain to ensure memory persistence (simulating new request)
        brain_two = HyperSymbolicBrain()
        # Force clear previous context so it reads the new numbers
        brain_two.awareness_lobe.mental_library = brain.awareness_lobe.mental_library
        res = brain_two.process(stimulus)
        
        # DEBUG: Print output
        print(f"DEBUG SIGMA/RES: {res}")

        # The solver must find the base values and NOT return a cognitive failure
        assert "COGNITIVE_FAILURE" not in res
        assert "1000" in res
        assert "500" in res
        assert "1500" in res
        print("  ✅ Pass: Brain successfully generalized understanding and proved math.\n")
    except AssertionError:
        print(f"  ❌ Fail: Could not solve unseen problem using learned logic. Output:\n{res}\n")
        failed_tests += 1

    # TEST 3: RECURSIVE DECOMPOSITION
    print("[TEST 3] High-Complexity Feature Decomposition")
    # Simulate a high-complexity coding task
    lesson_code = "teach: build a feature | COMPLEX_FEATURE | SYNTHESIS"
    brain.process(lesson_code)
    
    stimulus_code = "Build a feature for user authentication."
    try:
        # We manually inject 'high' complexity to trigger HTNPlanner for the test
        brain.awareness_lobe.mental_library["COMPLEX_FEATURE"][0]["target_type"] = "coding"
        brain.awareness_lobe.mental_library["COMPLEX_FEATURE"][0]["target_goal"] = "synthesize"
        brain.awareness_lobe._save_library()

        res = brain.process(stimulus_code)
        
        # It should decompose into DATA_STRUCTURE, BUSINESS_LOGIC, and INTEGRATION
        assert "DATA_STRUCTURE" in res
        assert "BUSINESS_LOGIC" in res
        assert "INTEGRATION" in res
        print("  ✅ Pass: HTN Planner successfully decomposed complex intent.\n")
    except AssertionError:
        print(f"  ❌ Fail: Brain failed to decompose complex task. Output:\n{res}\n")
        failed_tests += 1

    print("==================================================")
    if failed_tests == 0:
        print("🎉 IQ VERIFIED: No cognitive regressions detected.")
        sys.exit(0)
    else:
        print(f"🚨 PIPELINE HALTED: {failed_tests} cognitive tests failed. The AI has degraded.")
        sys.exit(1)

if __name__ == "__main__":
    run_iq_test()
