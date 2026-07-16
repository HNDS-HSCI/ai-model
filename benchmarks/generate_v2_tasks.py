import os
import json
import random

def gen_constraint_verification(task_idx):
    random.seed(hash(f"cv_{task_idx}"))
    prompt = "GLOBAL RESOURCE ALLOCATION MATRIX:\n"
    for i in range(25):
        prompt += f"Resource R{i} has base capacity {random.randint(100, 1000)}.\n"
    for i in range(50):
        prompt += f"Node N{random.randint(0, 30)} draws from R{random.randint(0, 24)}.\n"
    prompt += "\nCONSTRAINTS:\n"
    for i in range(10):
        prompt += f"Constraint {i}: Total draw on R{random.randint(0, 24)} cannot exceed 80% of capacity.\n"
        
    prompt += "\nRule: A node cannot draw from more than 3 resources simultaneously.\n"
    prompt += "Rule: Nodes in cluster A (N0-N15) have priority overrides over cluster B (N16-N30).\n"
    
    expected = random.choice(["VALID", "INVALID", "CONTRADICTION"])
    if expected == "INVALID":
        prompt += "\nPROPOSED STATE: N5 draws 5000 from R0.\n"
    elif expected == "CONTRADICTION":
        prompt += "\nPROPOSED STATE: Rule 3 dictates N0 must draw 100% of R0, contradicting the 80% capacity constraint.\n"
    else:
        prompt += "\nPROPOSED STATE: N5 draws 10 from R0.\n"
    prompt += "Answer ONLY with: VALID, INVALID, or CONTRADICTION."
    return prompt, expected

def gen_requirements_analysis(task_idx):
    random.seed(hash(f"req_{task_idx}"))
    prompt = "ENTERPRISE REQUIREMENTS DOC:\n"
    for i in range(25):
        prompt += f"Req {i}: System {random.randint(0, 10)} must support feature F{i}.\n"
    for i in range(50):
        prompt += f"Rule {i}: Feature F{random.randint(0, 24)} conflicts with F{random.randint(0, 24)} if active.\n"
    expected = random.choice(["CONSISTENT", "INCONSISTENT", "MISSING_REQUIREMENT"])
    if expected == "INCONSISTENT":
        prompt += "\nFinal Rule: F0 and F1 MUST be active simultaneously, overriding previous exclusions.\n"
    elif expected == "MISSING_REQUIREMENT":
        prompt += "\nFinal Rule: System 0 requires encryption, but encryption module is completely undefined.\n"
    else:
        prompt += "\nFinal Rule: Features operate normally.\n"
    prompt += "Answer ONLY with: CONSISTENT, INCONSISTENT, or MISSING_REQUIREMENT."
    return prompt, expected

def gen_architecture_planning(task_idx):
    random.seed(hash(f"arch_{task_idx}"))
    nodes = 50
    regions = ["us-east", "us-west", "eu-central", "ap-south"]
    prompt = "ENTERPRISE DEPLOYMENT TOPOLOGY:\n"
    services = {}
    for i in range(nodes):
        reg = random.choice(regions)
        services[f"S{i}"] = reg
        prompt += f"Service S{i} must deploy in region {reg}.\n"
        
    prompt += "\nDEPENDENCY RULES:\n"
    for i in range(1, nodes):
        dep = random.randint(0, i-1)
        prompt += f"S{i} requires S{dep} to be healthy before booting.\n"
        if random.random() > 0.5:
            prompt += f"S{i} requires S{random.randint(0, i-1)} as a secondary dependency.\n"
            
    prompt += "\nCOMPLIANCE RULES:\n"
    prompt += "Rule 1: Services in eu-central CANNOT depend on services in us-east due to GDPR isolation.\n"
    prompt += "Rule 2: Services in ap-south MUST start after at least one service in us-west.\n"
    
    expected = "VALID_ORDER"
    violation_type = random.choice(["NONE", "CYCLE", "COMPLIANCE"])
    if violation_type == "CYCLE":
        prompt += f"\nCRITICAL UPDATE: S2 now requires S45 to function.\n"
        expected = "CYCLIC_DEPENDENCY"
    elif violation_type == "COMPLIANCE":
        prompt += "\nCRITICAL UPDATE: Service S49 (in eu-central) strongly requires S0 (in us-east).\n"
        expected = "INVALID_ORDER"
            
    prompt += "\nEvaluate topology. Answer ONLY with: VALID_ORDER, CYCLIC_DEPENDENCY, or INVALID_ORDER."
    return prompt, expected

def gen_dependency_resolution(task_idx):
    random.seed(hash(f"dep_{task_idx}"))
    prompt = "PACKAGE MANAGER RESOLUTION GRAPH:\n"
    for i in range(50):
        prompt += f"Package lib-{i} v{random.randint(1,3)}.0.0 is available.\n"
    
    for i in range(1, 50):
        prompt += f"lib-{i} strictly requires lib-{random.randint(0, i-1)}.\n"
        if random.random() > 0.3:
            prompt += f"lib-{i} also requires lib-{random.randint(0, i-1)}.\n"
            
    expected = "VALID_ORDER"
    violation_type = random.choice(["NONE", "CYCLE", "VERSION"])
    if violation_type == "CYCLE":
        prompt += "\nFATAL: lib-5 requires lib-45.\n"
        expected = "CYCLIC_DEPENDENCY"
    elif violation_type == "VERSION":
        prompt += "\nFATAL: lib-49 requires lib-0 v9.9.9, which does not exist.\n"
        expected = "INVALID_ORDER"
        
    prompt += "\nEvaluate the dependency graph. Answer ONLY with: VALID_ORDER, CYCLIC_DEPENDENCY, or INVALID_ORDER."
    return prompt, expected

def gen_state_machine_verification(task_idx):
    random.seed(hash(f"sm_{task_idx}"))
    prompt = "ENTERPRISE WORKFLOW STATE MACHINE:\n"
    states = [f"STATE_{i}" for i in range(25)]
    prompt += "Valid states registered: " + ", ".join(states) + "\n\n"
    
    prompt += "TRANSITIONS:\n"
    for i in range(50):
        prompt += f"T{i}: {states[random.randint(0, 23)]} -> {states[random.randint(1, 24)]}\n"
        
    prompt += "\nCONDITIONS & FORBIDDEN PATHS:\n"
    prompt += "Rule 1: STATE_24 is a TERMINAL state. No transitions out are allowed.\n"
    prompt += "Rule 2: Cannot enter STATE_10 without passing through STATE_2 (Recovery State).\n"
    prompt += "Rule 3: STATE_5 to STATE_15 is time-bound and requires override token.\n"
    prompt += "Rule 4: STATE_0 -> STATE_24 directly is FORBIDDEN.\n"
    
    expected = "VALID" if task_idx % 2 == 0 else "INVALID"
    if expected == "INVALID":
        prompt += "\nEXECUTION TRACE: STATE_0 -> STATE_24.\n"
    else:
        prompt += "\nEXECUTION TRACE: STATE_0 -> STATE_1 -> STATE_2.\n"
        
    prompt += "Is the execution trace valid according to the DFA? Answer ONLY with: VALID or INVALID."
    return prompt, expected

def main():
    base_dir = os.path.dirname(__file__)
    categories = {
        "constraint_verification": gen_constraint_verification,
        "requirements_analysis": gen_requirements_analysis,
        "architecture_planning": gen_architecture_planning,
        "state_machine_verification": gen_state_machine_verification,
        "dependency_resolution": gen_dependency_resolution
    }
    
    total = 0
    for cat, gen_func in categories.items():
        tasks = []
        for i in range(1, 21):
            prompt, expected = gen_func(i)
            tasks.append({
                "id": f"{cat}_v2_{i}",
                "category": cat,
                "prompt": prompt,
                "expected": expected
            })
            
        cat_dir = os.path.join(base_dir, cat)
        os.makedirs(cat_dir, exist_ok=True)
        with open(os.path.join(cat_dir, "tasks.json"), "w") as f:
            json.dump(tasks, f, indent=2)
        total += len(tasks)
        print(f"Generated {len(tasks)} V2 tasks for {cat}.")
        
    print(f"\nTotal V2 tasks generated: {total}")

if __name__ == "__main__":
    main()
