import sys
import os
import time

# Add project root to path
sys.path.append(os.getcwd())

from hnsds.brain.cognitive_core import HyperSymbolicBrain

def type_writer(text, speed=0.01):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    print()

def run_mind():
    brain = HyperSymbolicBrain()
    
    print("\n=================================================")
    print("   HSCI: Hyper-Symbolic Cognitive Intelligence   ")
    print("           (Native Tensor Brain v1.0)            ")
    print("=================================================")
    print("Type 'exit' to quit. Type 'debug' to toggle trace.")
    
    debug_mode = True
    
    while True:
        try:
            print("\n┌──[USER]")
            user_input = input("└─> ")
            
            if user_input.lower() in ['exit', 'quit']:
                print("\nShutting down cognitive core...")
                break
            
            if user_input.lower() == 'debug':
                debug_mode = not debug_mode
                print(f"Debug Trace: {'ON' if debug_mode else 'OFF'}")
                continue
            
            # --- COGNITIVE PROCESS ---
            start_time = time.time()
            
            # 1. PERCEIVE & DELIBERATE
            response = brain.process(user_input)
            
            duration = time.time() - start_time
            
            # --- DISPLAY MENTAL STATE (The Glass Box) ---
            if debug_mode:
                trace = brain.get_mind_state()
                print("\n  ┌──[MIND STATE]")
                for line in trace.split('\n'):
                    if line: print(f"  │ {line}")
                print(f"  └─> Thought Time: {duration:.4f}s")
            
            # --- OUTPUT ---
            print("\n┌──[HSCI]")
            type_writer(f"└─> {response}")
            
            # --- REAL-TIME LEARNING LOOP ---
            # Only ask occasionally or if it looks uncertain? 
            # For this demo, we allow explicit correction command or auto-prompt on failure.
            
            if "COGNITIVE_FAILURE" in response:
                print("\n[!] The Brain failed. Teach it? (y/n)")
                should_teach = input("    > ").lower() == 'y'
            else:
                # Implicit feedback hook
                pass
                
            # Allow user to force-correct by typing '/wrong' next turn?
            # Or just ask simple feedback for this demo phase:
            print("\n    [Was this correct? (Enter=Yes, 'no'=Teach)]")
            feedback = input("    > ").lower()
            
            if feedback == 'no' or feedback == 'n':
                print("    What was the correct intent? (MATH / CODING / CONVERSATIONAL)")
                correct_intent = input("    > ").upper()
                if correct_intent in ["MATH", "CODING", "CONVERSATIONAL"]:
                    # Force Learning: Backpropagate the Error
                    brain.neural_lobe.grow(user_input, None, correct_intent)
                    print(f"    [+] Synaptic Weights Rewired. I associated '{user_input}' with {correct_intent}.")
                else:
                    print("    [-] Invalid intent. Learning cancelled.")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n[ERROR] Cognitive Crash: {e}")

if __name__ == "__main__":
    run_mind()
