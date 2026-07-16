import os
import json

def generate_constraint_verification():
    tasks = []
    for i in range(1, 11):
        tasks.append({
            "id": f"cv_valid_{i}",
            "prompt": f"Account balance is {1000 * i}. Withdrawal is {500 * i}. Balance cannot be negative. Is transaction valid? Answer ONLY with: VALID, INVALID, or CONTRADICTION.",
            "expected": "VALID"
        })
    for i in range(11, 21):
        tasks.append({
            "id": f"cv_invalid_{i}",
            "prompt": f"Account balance is {1000 * i}. Withdrawal is {1500 * i}. Balance cannot be negative. Is transaction valid? Answer ONLY with: VALID, INVALID, or CONTRADICTION.",
            "expected": "INVALID"
        })
    return tasks

def generate_requirements_analysis():
    tasks = []
    for i in range(1, 11):
        tasks.append({
            "id": f"req_cons_{i}",
            "prompt": f"Req1: System must support {i} concurrent users. Req2: System supports up to {i*2} concurrent users. Are requirements consistent? Answer ONLY with: CONSISTENT, INCONSISTENT, or MISSING_REQUIREMENT.",
            "expected": "CONSISTENT"
        })
    for i in range(11, 21):
        tasks.append({
            "id": f"req_incons_{i}",
            "prompt": f"Req1: Admin must have full access. Req2: No user can have full access. Are requirements consistent? Answer ONLY with: CONSISTENT, INCONSISTENT, or MISSING_REQUIREMENT.",
            "expected": "INCONSISTENT"
        })
    return tasks

def generate_architecture_planning():
    tasks = []
    for i in range(1, 11):
        tasks.append({
            "id": f"arch_valid_{i}",
            "prompt": "Services: DB, API, UI. DB depends on nothing. API depends on DB. UI depends on API. Given order: DB -> API -> UI. Is order valid? Answer ONLY with: VALID_ORDER, CYCLIC_DEPENDENCY, or INVALID_ORDER.",
            "expected": "VALID_ORDER"
        })
    for i in range(11, 21):
        tasks.append({
            "id": f"arch_invalid_{i}",
            "prompt": "Services: DB, API, UI. DB depends on nothing. API depends on DB. UI depends on API. Given order: UI -> API -> DB. Is order valid? Answer ONLY with: VALID_ORDER, CYCLIC_DEPENDENCY, or INVALID_ORDER.",
            "expected": "INVALID_ORDER"
        })
    return tasks

def generate_state_machine_verification():
    tasks = []
    for i in range(1, 11):
        tasks.append({
            "id": f"sm_valid_{i}",
            "prompt": "Order states: NEW -> PROCESSING -> SHIPPED. Can order transition from PROCESSING to SHIPPED? Answer ONLY with: VALID or INVALID.",
            "expected": "VALID"
        })
    for i in range(11, 21):
        tasks.append({
            "id": f"sm_invalid_{i}",
            "prompt": "Order states: NEW -> PROCESSING -> SHIPPED. Can order transition from NEW to SHIPPED directly? Answer ONLY with: VALID or INVALID.",
            "expected": "INVALID"
        })
    return tasks

def generate_dependency_resolution():
    tasks = []
    for i in range(1, 11):
        tasks.append({
            "id": f"dep_cyclic_{i}",
            "prompt": "Pkg A depends on Pkg B. Pkg B depends on Pkg C. Pkg C depends on Pkg A. Check dependencies. Answer ONLY with: VALID_ORDER, CYCLIC_DEPENDENCY, or INVALID_ORDER.",
            "expected": "CYCLIC_DEPENDENCY"
        })
    for i in range(11, 21):
        tasks.append({
            "id": f"dep_valid_{i}",
            "prompt": "Pkg A depends on Pkg B. Pkg B depends on Pkg C. Pkg C depends on nothing. Check dependencies. Answer ONLY with: VALID_ORDER, CYCLIC_DEPENDENCY, or INVALID_ORDER.",
            "expected": "VALID_ORDER"
        })
    return tasks

def main():
    base_dir = os.path.dirname(__file__)
    categories = {
        "constraint_verification": generate_constraint_verification(),
        "requirements_analysis": generate_requirements_analysis(),
        "architecture_planning": generate_architecture_planning(),
        "state_machine_verification": generate_state_machine_verification(),
        "dependency_resolution": generate_dependency_resolution()
    }
    
    total = 0
    for cat, tasks in categories.items():
        cat_dir = os.path.join(base_dir, cat)
        os.makedirs(cat_dir, exist_ok=True)
        with open(os.path.join(cat_dir, "tasks.json"), "w") as f:
            json.dump(tasks, f, indent=2)
        total += len(tasks)
        print(f"Generated {len(tasks)} tasks for {cat}.")
        
    print(f"\nTotal real tasks generated: {total}")

if __name__ == "__main__":
    main()
