import json
import os

def create_math_tasks():
    tasks = []
    for i in range(1, 21):
        x = i * 2
        y = i * 3
        tasks.append({
            "id": f"math_{i}",
            "prompt": f"Solve: {x}x + {y} = {x * 10 + y}",
            "expected": str(10)
        })
    return tasks

def create_logic_tasks():
    tasks = []
    for i in range(1, 21):
        tasks.append({
            "id": f"logic_{i}",
            "prompt": f"If A is {i} times B, and B is {i*2}, what is A?",
            "expected": str(i * i * 2)
        })
    return tasks

def create_planning_tasks():
    tasks = []
    for i in range(1, 21):
        tasks.append({
            "id": f"plan_{i}",
            "prompt": f"Plan exactly {i} steps to boil water. Only output the final step number.",
            "expected": str(i)
        })
    return tasks

def create_memory_tasks():
    tasks = []
    for i in range(1, 21):
        tasks.append({
            "id": f"memory_{i}",
            "prompt": f"The secret code is {i * 999}. What is the secret code?",
            "expected": str(i * 999)
        })
    return tasks

def create_sw_eng_tasks():
    tasks = []
    for i in range(1, 21):
        tasks.append({
            "id": f"se_{i}",
            "prompt": f"Write a Python function that returns the number {i*50}. Just output the number returned.",
            "expected": str(i * 50)
        })
    return tasks

def main():
    base_dir = os.path.dirname(__file__)
    categories = {
        "math": create_math_tasks(),
        "logic": create_logic_tasks(),
        "planning": create_planning_tasks(),
        "memory": create_memory_tasks(),
        "software_engineering": create_sw_eng_tasks()
    }
    
    total = 0
    for cat, tasks in categories.items():
        cat_dir = os.path.join(base_dir, cat)
        os.makedirs(cat_dir, exist_ok=True)
        with open(os.path.join(cat_dir, "tasks.json"), "w") as f:
            json.dump(tasks, f, indent=2)
        total += len(tasks)
        print(f"Generated {len(tasks)} tasks for {cat}.")
        
    print(f"\nTotal tasks generated: {total}")

if __name__ == "__main__":
    main()
