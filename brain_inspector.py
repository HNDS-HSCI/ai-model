import json
import os

def inspect_brain():
    core_path = "synaptic_core.json"
    episodes_path = "episodes.jsonl"
    
    print("="*60)
    print("HSCI BRAIN INSPECTOR: MODEL STATE ANALYSIS")
    print("="*60)
    
    if os.path.exists(core_path):
        with open(core_path, "r") as f:
            core = json.load(f)
            features = core.get("features", {})
            print(f"\n[SYNAPTIC INTELLIGENCE]")
            print(f"Total Concepts Learned: {len(features)}")
            
            # Show top 5 strongest synapses
            sorted_features = sorted(features.items(), key=lambda x: max(x[1].values() if x[1] else [0]), reverse=True)
            print("\nStrongest Synaptic Links:")
            for concept, weights in sorted_features[:10]:
                dominant_mode = max(weights, key=weights.get) if weights else "None"
                strength = weights[dominant_mode] if weights else 0
                print(f"  - '{concept}' -> {dominant_mode} (Strength: {strength:.2f})")
    
    if os.path.exists(episodes_path):
        with open(episodes_path, "r") as f:
            episodes = f.readlines()
            print(f"\n[EPISODIC MEMORY]")
            print(f"Total Experiences Logged: {len(episodes)}")
            
            successes = 0
            for ep in episodes:
                try:
                    if json.loads(ep).get("success"): successes += 1
                except: pass
            print(f"Proven Logic Paths: {successes}")

    print("\n" + "="*60)
    print("ANALYSIS COMPLETE: The model is growing through native interaction.")
    print("="*60)

if __name__ == "__main__":
    inspect_brain()
