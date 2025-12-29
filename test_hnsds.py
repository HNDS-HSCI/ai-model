import logging
import sys
from hnsds.orchestrator import HNSDSOrchestrator
from hnsds.perception.parser import Parser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.enumerative import EnumerativeSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger


def main():
    # Ensure fresh state
    import os

    if os.path.exists("episodes.jsonl"):
        os.remove("episodes.jsonl")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s - %(message)s", stream=sys.stdout
    )

    # Initialize components
    p = Parser()
    f = SpecBuilder()
    pl = HTNPlanner()
    v = Z3Verifier()
    l = EpisodeLogger()
    sy = EnumerativeSynthesizer(learner=l)

    # Initialize orchestrator
    orchestrator = HNSDSOrchestrator(p, f, pl, sy, v, l)

    # Complex Task Decomposition
    print("\n--- SYSTEM SOLVER TEST ---")
    # Increase budget for real enumerative search
    result = orchestrator.run("Solve x + y = -10, x - y = 2", budget=100000)

    if result:
        print(f"\nFinal Solution for System: {result}")
        print("\n--- DELIBERATION REPORT (MENTAL MODEL) ---")
        print(orchestrator.write_solution())
    else:
        print("\nFailed to find solution for system.")


if __name__ == "__main__":
    main()
