from concurrent.futures import ThreadPoolExecutor

from hsci.core.rir_loop import RIRLoop


def test_parallel_requests_do_not_corrupt_optimizer_state():
    brain = RIRLoop(use_llm=False)
    queries = [
        "calculate 25 + 75",
        "find velocity if distance = 100 and time = 5",
        "find tax amount if salary = 50000 and rate = 0.3",
        "hello",
    ] * 2

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(brain.process_internal, queries))

        assert len(results) == len(queries)
        assert brain.get_neural_stats()["classifier"]["proof_count"] > 0
    finally:
        brain.self_play.stop()


def test_code_generation_returns_useful_and_honest_output():
    brain = RIRLoop(use_llm=False)
    try:
        response = brain.process("write code for a salary calculator")

        assert "def calculate_salary" in response
        assert "net_salary" in response
        assert "has not been formally verified" in response
        assert "Verified by structural induction" not in response
    finally:
        brain.self_play.stop()
