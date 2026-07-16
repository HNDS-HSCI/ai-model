# HSCI Real Benchmark Generation

## Context

The current benchmark suite is too simplistic.

Examples of bad benchmarks:

- Arithmetic drills
- Number extraction
- Echoing values from prompts
- Simple memory recall
- Trivial planning tasks

These benchmarks do not measure HSCI's strengths.

HSCI strengths are:

- Formal Verification
- Z3 Constraint Solving
- HTN Planning
- Contradiction Detection
- Requirements Analysis
- Dependency Resolution
- State Validation
- Symbolic Reasoning

Your task is to generate realistic benchmarks that specifically test these capabilities.

---

# Goal

Generate a benchmark suite that can objectively compare:

- HSCI
- GPT
- Claude
- Gemini

and expose where HSCI genuinely outperforms LLMs.

---

# Benchmark Categories

Generate exactly 20 tasks for each category.

## Category 1: Constraint Verification

Examples:

- Banking rules
- Trading rules
- Access control
- Resource allocation
- Scheduling constraints

Expected outputs:

VALID
INVALID
CONTRADICTION

---

## Category 2: Requirements Analysis

Examples:

- User stories
- Functional requirements
- Business rules

Tasks should require:

- detecting missing requirements
- detecting conflicting requirements
- validating requirement consistency

Expected outputs:

CONSISTENT
INCONSISTENT
MISSING_REQUIREMENT

---

## Category 3: Architecture Planning

Examples:

- Microservices
- Deployment dependencies
- Event-driven systems

Tasks should require:

- dependency ordering
- valid deployment sequences
- planning verification

Expected outputs should be objectively scoreable.

---

## Category 4: State Machine Verification

Examples:

- Order lifecycle
- User lifecycle
- Workflow transitions

Tasks should require:

- checking valid transitions
- detecting illegal transitions

Expected outputs:

VALID
INVALID

---

## Category 5: Dependency Resolution

Examples:

- Package dependencies
- Service dependencies
- Build dependencies

Tasks should require:

- topological ordering
- cycle detection
- dependency validation

Expected outputs:

VALID_ORDER
CYCLIC_DEPENDENCY
INVALID_ORDER

---

# Requirements

Every task must:

1. Be objectively scoreable.
2. Have deterministic expected output.
3. Be suitable for automatic evaluation.
4. Reflect real enterprise problems.
5. Not depend on subjective judgment.

---

# Output Format

Generate JSON files.

Example:

[
  {
    "id": "cv_1",
    "prompt": "Account balance is 1000. Withdrawal is 1500. Balance cannot be negative. Is transaction valid?",
    "expected": "INVALID"
  }
]

Create:

benchmarks/
├── constraint_verification/tasks.json
├── requirements_analysis/tasks.json
├── architecture_planning/tasks.json
├── state_machine_verification/tasks.json
└── dependency_resolution/tasks.json

Generate 20 tasks per category.

Total = 100 tasks.

Also generate:

1. Python scoring logic
2. Evaluation criteria
3. Suggested leaderboard metrics
4. Benchmark documentation

Do not generate trivial arithmetic or memorization tasks.