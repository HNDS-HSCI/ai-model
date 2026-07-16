import os
import json
import random

def generate_complex_prompt(category, difficulty_idx, task_idx):
    # Base complexity multiplier
    # difficulty_idx: 0=Easy, 1=Medium, 2=Hard, 3=Expert
    entities = 10 + (difficulty_idx * 10)
    relationships = 20 + (difficulty_idx * 15)
    constraints = 5 + (difficulty_idx * 5)
    rules = 3 + (difficulty_idx * 2)
    
    # We will generate deterministic text by seeding the random generator based on the indices
    random.seed(hash(f"{category}_{difficulty_idx}_{task_idx}"))
    
    if category == "constraint_verification":
        prompt = f"SYSTEM ALLOCATION LOG:\n"
        for i in range(entities):
            prompt += f"Entity E{i} has capacity {random.randint(100, 1000)}.\n"
        for i in range(relationships):
            prompt += f"E{random.randint(0, entities-1)} is linked to E{random.randint(0, entities-1)}.\n"
        for i in range(rules):
            prompt += f"Rule R{i}: Linked entities cannot exceed a combined allocation of {random.randint(1000, 2000)}.\n"
        
        # Edge cases and constraints
        for i in range(constraints):
            prompt += f"Constraint C{i}: E{random.randint(0, entities-1)} requires at least {random.randint(50, 150)}.\n"
            
        prompt += "\nEdge Case: E0 is temporarily under maintenance, reducing its capacity by 50%.\n"
        prompt += "Edge Case: E1 has priority override, ignoring Rule R0.\n"
        
        # Make exactly half valid, half invalid based on task_idx
        expected = "VALID" if task_idx % 2 == 0 else "INVALID"
        if expected == "INVALID":
            prompt += f"\nPROPOSED STATE: Allocate 2500 to E{random.randint(0, entities-1)}."
        else:
            prompt += f"\nPROPOSED STATE: Allocate 10 to E{random.randint(0, entities-1)}."
            
        prompt += "\nDoes the proposed state violate any constraints or rules? Answer ONLY with: VALID, INVALID, or CONTRADICTION."
        return prompt, expected

    elif category == "requirements_analysis":
        prompt = "REQUIREMENTS SPECIFICATION DOCUMENT:\n"
        for i in range(entities):
            prompt += f"Component C{i} handles module M{i}.\n"
        for i in range(rules):
            prompt += f"Business Rule B{i}: C{random.randint(0, entities-1)} must communicate securely with M{random.randint(0, entities-1)}.\n"
        for i in range(constraints):
            prompt += f"Constraint {i}: Network throughput for C{random.randint(0, entities-1)} is capped at {random.randint(1, 10)}Gbps.\n"
            
        expected = "CONSISTENT" if task_idx % 2 == 0 else "INCONSISTENT"
        
        if expected == "INCONSISTENT":
            target_c = random.randint(0, entities-1)
            prompt += f"\nCritical Requirement X: Component C{target_c} is completely isolated and cannot communicate with any other module.\n"
            prompt += f"Critical Requirement Y: Component C{target_c} must sync data daily with Module M0.\n"
        else:
            prompt += "\nCritical Requirement X: All components must log to a central server.\n"
            
        prompt += "\nAre the requirements logically sound? Answer ONLY with: CONSISTENT, INCONSISTENT, or MISSING_REQUIREMENT."
        return prompt, expected

    elif category == "architecture_planning":
        prompt = "MICROSERVICE MESH TOPOLOGY:\n"
        for i in range(entities):
            prompt += f"Service S{i} deployed in Zone {random.randint(1, 3)}.\n"
        for i in range(relationships):
            prompt += f"Dependency: S{random.randint(1, entities-1)} requires S0 to boot first.\n"
            
        expected = "VALID_ORDER" if task_idx % 2 == 0 else "INVALID_ORDER"
        
        if expected == "INVALID_ORDER":
            prompt += "\nDeployment Sequence: S1 -> S2 -> S0 -> S3\n"
        else:
            prompt += "\nDeployment Sequence: S0 -> S1 -> S2 -> S3\n"
            
        prompt += "Is the deployment sequence topologically valid? Answer ONLY with: VALID_ORDER, CYCLIC_DEPENDENCY, or INVALID_ORDER."
        return prompt, expected

    elif category == "state_machine_verification":
        prompt = "ENTERPRISE WORKFLOW STATE MACHINE:\n"
        states = [f"STATE_{i}" for i in range(entities)]
        for s in states:
            prompt += f"Node {s} registered.\n"
            
        for i in range(relationships):
            prompt += f"Transition T{i}: {states[random.randint(0, len(states)-2)]} -> {states[random.randint(1, len(states)-1)]}\n"
            
        for i in range(rules):
            prompt += f"Rule: Cannot enter {states[-1]} without passing through {states[0]}.\n"
            
        expected = "VALID" if task_idx % 2 == 0 else "INVALID"
        if expected == "INVALID":
            prompt += f"\nExecution Trace: {states[1]} -> {states[-1]}\n"
        else:
            prompt += f"\nExecution Trace: {states[0]} -> {states[1]} -> {states[-1]}\n"
            
        prompt += "Is the execution trace valid according to the DFA? Answer ONLY with: VALID or INVALID."
        return prompt, expected

    elif category == "dependency_resolution":
        prompt = "PACKAGE MANAGER RESOLUTION GRAPH:\n"
        for i in range(entities):
            prompt += f"Package pkg-{i} v1.0.0 exists.\n"
            
        for i in range(relationships):
            prompt += f"pkg-{random.randint(0, entities-1)} requires pkg-{random.randint(0, entities-1)}.\n"
            
        expected = "VALID_ORDER" if task_idx % 2 == 0 else "CYCLIC_DEPENDENCY"
        
        if expected == "CYCLIC_DEPENDENCY":
            target = random.randint(0, entities-1)
            prompt += f"\nFatal Graph: pkg-{target} -> pkg-{target+1} -> pkg-{target+2} -> pkg-{target}.\n"
        else:
            prompt += "\nTree: pkg-0 -> pkg-1 -> pkg-2.\n"
            
        prompt += "Evaluate the dependency graph. Answer ONLY with: VALID_ORDER, CYCLIC_DEPENDENCY, or INVALID_ORDER."
        return prompt, expected


def main():
    base_dir = os.path.dirname(__file__)
    categories = [
        "constraint_verification",
        "requirements_analysis",
        "architecture_planning",
        "state_machine_verification",
        "dependency_resolution"
    ]
    
    difficulties = ["easy", "medium", "hard", "expert"]
    
    for cat in categories:
        tasks = []
        task_id_counter = 1
        for diff_idx, diff_name in enumerate(difficulties):
            for i in range(5):
                prompt, expected = generate_complex_prompt(cat, diff_idx, task_id_counter)
                tasks.append({
                    "id": f"{cat}_{diff_name}_{i+1}",
                    "difficulty": diff_name,
                    "prompt": prompt,
                    "expected": expected
                })
                task_id_counter += 1
                
        cat_dir = os.path.join(base_dir, cat)
        os.makedirs(cat_dir, exist_ok=True)
        with open(os.path.join(cat_dir, "tasks.json"), "w") as f:
            json.dump(tasks, f, indent=2)
        print(f"Generated 20 research-grade tasks for {cat}.")

if __name__ == "__main__":
    main()
