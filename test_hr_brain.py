from hnsds.brain.cognitive_core import HyperSymbolicBrain
import sys
import os
sys.path.append(os.getcwd())

def test_hr_capabilities():
    brain = HyperSymbolicBrain()
    
    # 1. Test Payroll (Using synonym 'wages')
    print("--- STIMULUS: 'Write a program to calculate wages' ---")
    res1 = brain.process("Write a program to calculate wages")
    print(res1)
    
    # 2. Test Recruitment (Using concept 'staff')
    print("\n--- STIMULUS: 'Filter staff by age' ---")
    res2 = brain.process("Filter staff by age")
    print(res2)

if __name__ == "__main__":
    test_hr_capabilities()

