import logging
import sys
from hnsds.orchestrator import HNSDSOrchestrator
from hnsds.perception.parser import Parser
from hnsds.formalizer.spec_builder import SpecBuilder
from hnsds.planner.htn_planner import HTNPlanner
from hnsds.synthesizer.generative import GenerativeSynthesizer
from hnsds.verifier.z3_interface import Z3Verifier
from hnsds.learner.episode_logger import EpisodeLogger

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

def main():
    # Initialize the "Generic" System
    p = Parser()
    f = SpecBuilder()
    pl = HTNPlanner()
    v = Z3Verifier()
    l = EpisodeLogger()
    sy = GenerativeSynthesizer(model_name="gemini-ultra") 

    orchestrator = HNSDSOrchestrator(p, f, pl, sy, v, l)

    # The User's Raw Log Input
    raw_logs = """
2025-12-28 11:20:00 | WARNING  | CREATING OTP: recipient=flimhub12@gmail.com, purpose=reset_pin, code=895795
2025-12-28 11:20:00 | INFO     | REQUEST_END | ID: 5e787ec8 | POST /api/v1/auth/otp/request | Status: 200
2025-12-28 11:20:29 | INFO     | OTP verified successfully for flimhub12@gmail.
    """

    print("--- User provided raw server logs for analysis ---")
    print(f"Input Data: {raw_logs.strip()[:100]}...\n")
    
    # We wrap the logs in a command so the parser treats it as a 'task'
    # In a real system, the parser would auto-detect "Data Blob" vs "Command"
    task_input = f"Analyze these logs: {raw_logs}"
    
    print("--- Cognitive Process (Log Analysis) ---")
    result = orchestrator.run(task_input)
    
    if result:
        print(f"\n>>> System Output:\n{result}")
    else:
        print(">>> Failed.")

if __name__ == "__main__":
    main()
