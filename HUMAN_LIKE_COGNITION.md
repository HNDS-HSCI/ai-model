# How HSCI Works "Like a Human"

You asked: *"How will it work like a human?"*

This is the core question. Standard AI (LLMs) does NOT work like a human; it works like a statistical parrot. It guesses the next word.

**HSCI (Hyper-Symbolic Cognitive Invention)** is designed to mimic the *structure* of human cognition. Here is the breakdown of how we implemented this "Human-Like" behavior in the code:

## 1. The Two Systems of Thought (Kahneman's Theory)

Human cognition is divided into **System 1 (Fast, Intuitive)** and **System 2 (Slow, Deliberative)**. We have explicitly coded this separation:

### System 1: The Intuition (`NativeNeuralLobe`)
- **Human Behavior**: When you see "2+2", you don't calculate it; you just *know* it's 4. This is fast, pattern-matched intuition.
- **HSCI Implementation**: The `NativeNeuralLobe` (in `hnsds/brain/lobes/native_neural_lobe.py`) uses a "Synaptic Weight Matrix" (`synaptic_core.json`) to instantly classify inputs based on past experience. It doesn't "think"; it "reacts."

### System 2: The Reasoner (`NativeSymbolicEngine`)
- **Human Behavior**: When you see "234 * 12", you can't just "know" it. You have to *stop*, apply a rule (algorithm), and verify the result step-by-step.
- **HSCI Implementation**: The `NativeSymbolicEngine` (in `hnsds/brain/lobes/native_engine.py`) takes the output of System 1 and *rigorously verifies it*. It performs the actual logic reduction. If the Intuition was wrong, this system catches it.

## 2. Learning from Experience (Neuroplasticity)

Humans get smarter the more they solve problems.
- **Human Behavior**: If you solve a math problem correctly, your brain strengthens the synaptic connection for that method. Next time, it's easier.
- **HSCI Implementation**: We implemented **Hebbian Learning** in the `grow()` function.
    - When `HyperSymbolicBrain.process()` finds a **Proven Solution**, it calls `self.neural_lobe.grow()`.
    - This updates the weights in `synaptic_core.json`.
    - **Result**: The AI effectively "rewires" itself based on *verified successes*, not just training data.

## 3. The Mental Model (Self-Awareness)

Humans are aware of their own thinking process ("I am currently trying to recall a memory...").
- **HSCI Implementation**: The `MentalModel` class (in `hnsds/mental_model.py`) maintains a live trace of the cognitive state (`self.state`, `self.memory_trace`).
- It explicitly switches modes: `IDLE` -> `RECALLING` -> `ANALYTICAL` -> `VERIFYING`.
- This "Stream of Consciousness" is visible in the Dashboard, making the AI's mind transparent.

## Summary of the "Human" Loop

1.  **Stimulus**: "Calculate total velocity."
2.  **System 1 (Intuition)**: "This feels like a MATH problem." (Classified by `NativeNeuralLobe`)
3.  **System 2 (Reasoning)**: "I will apply the formula. $v = d/t$." (Synthesized)
4.  **Verification**: "Is this mathematically consistent?" (Proven by `NativeSymbolicEngine`)
5.  **Growth**: "That worked. Strengthen the connection between 'velocity' and 'division'." (Updated `synaptic_core.json`)

This is not a chatbot. It is a **Cognitive Engine**.
