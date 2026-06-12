"""
HSCI CLI v3.0 — Terminal Interface
Run HSCI directly from the command line with real-time proof feedback.
Usage: python hsci_cli.py
"""
import os
import sys
import time

# Force UTF-8 on Windows terminals (fixes emoji/unicode rendering)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hsci.core.rir_loop import RIRLoop


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║        HSCI  v3.0  —  Hyper-Symbolic Cognitive Invention     ║
║        Neurosymbolic AI  ·  No LLMs  ·  Proof-Verified       ║
╚══════════════════════════════════════════════════════════════╝
 Domains: Math · Physics · Finance · Geometry · Code · Logic
 Commands: 'stats' · 'save' · 'clear' · 'exit'
"""

EXAMPLES = [
    "calculate 10 + 5",
    "what is velocity if distance = 100 and time = 5",
    "find tax amount if salary = 50000 and rate = 0.3",
    "compute force given mass = 10 and acceleration = 9.8",
    "write code to add two numbers",
    "what is the area if length = 5 and width = 3",
]


def print_examples():
    print("\n  💡 Example queries:")
    for ex in EXAMPLES:
        print(f"     • {ex}")
    print()


def main():
    print(BANNER)
    print_examples()

    print("  Initializing HSCI cognitive core...")
    brain = RIRLoop(use_llm=False)
    print("  ✅ Ready.\n")

    history = []

    while True:
        try:
            user_input = input("  [YOU] › ").strip()

            if not user_input:
                continue

            # ─── Built-in Commands ────────────────────────────────────────
            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n  Saving weights before exit...")
                brain.save_weights()
                print("  Goodbye.\n")
                break

            if user_input.lower() == "stats":
                stats = brain.get_neural_stats()
                print(f"\n  📊 Neural Stats:")
                print(f"     Weight version  : {stats['weight_version']}")
                print(f"     Proofs processed: {stats['classifier']['proof_count']}")
                print(f"     Avg loss        : {stats['classifier']['avg_loss']:.4f}")
                print(f"     Concepts loaded : {len(brain.knowledge_base.concept_library.concepts)}")
                print()
                continue

            if user_input.lower() == "save":
                brain.save_weights()
                print("  ✅ Weights saved.\n")
                continue

            if user_input.lower() == "clear":
                history.clear()
                print("  🗑️  History cleared.\n")
                continue

            if user_input.lower() in ["help", "examples"]:
                print_examples()
                continue

            # ─── Process Through Full RIR Loop ────────────────────────────
            print(f"\n  [HSCI] ⚙  Deliberating", end="", flush=True)
            start = time.time()

            final_out, structured = brain.process_internal(user_input)
            response = brain.response_bridge.generate(final_out, user_input, structured.domain)

            elapsed = time.time() - start

            # Status badge
            if final_out.is_verified:
                badge = "✅ VERIFIED"
                badge_color = "\033[92m"  # green
            else:
                badge = "⚠  UNVERIFIED"
                badge_color = "\033[93m"  # yellow

            reset = "\033[0m"

            print(f"\r  [HSCI] {badge_color}{badge}{reset}")
            print(f"\n  {response}\n")

            # Compact trace
            if final_out.concepts_used:
                print(f"  📐 Concepts : {', '.join(final_out.concepts_used)}")
            print(f"  🧠 Confidence: {final_out.confidence:.0%}  |  ⏱ {elapsed:.3f}s  |  Attempt: {final_out.attempts}")
            print()

            history.append({
                "input": user_input,
                "answer": final_out.answer,
                "verified": final_out.is_verified
            })

        except KeyboardInterrupt:
            print("\n\n  Saving weights...")
            brain.save_weights()
            print("  Goodbye.\n")
            break
        except Exception as e:
            print(f"\n  [ERROR] {e}\n")


if __name__ == "__main__":
    main()
