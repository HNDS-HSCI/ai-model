# Building the HSCI (Hyper-Symbolic Cognitive Invention)

You are building a **Self-Verifying Cognitive Architecture** that does not rely on "black box" LLMs. Instead of predicting tokens, it **deliberates** using a native Neuro-Symbolic loop.

## Core Components to Build

To make this a "real" working AI model, you need to implement the **RIR-RI Loop** (Reinforced Iterative Repair with Retrieval & Induction). Here is the roadmap:

### 1. The Native Neural Lobe (`hnsds/brain/lobes/native_neural_lobe.py`)
This is the "Intuition" layer. It needs to:
- **Transduce** raw text into a strict JSON specification ($\Sigma$) using a `classify_and_formalize` method.
- **Learn** by updating a local weight matrix (`synaptic_core.json`) when a solution is proven correct (Hebbian Learning).
- **Avoid LLMs**: It currently uses simple Bag-of-Words and Regex heuristics. You can upgrade this to use a local embedding model (like `Word2Vec` or a small Transformer like `BERT`) for better intent classification without external APIs.

### 2. The Symbolic Engine (`hnsds/brain/lobes/native_engine.py`)
This is the "Truth" layer. It currently does basic arithmetic reduction. You need to:
- **Expand Axioms**: Add support for more complex logic (Algebra, Boolean Logic).
- **Integrate Z3**: Use the `z3-solver` library to mathematically prove that a candidate solution satisfies the specification $\Sigma$.

### 3. The Synthesizer (`hnsds/synthesizer/`)
This is the "Reasoning" layer. It generates candidate solutions.
- **Implement Enumerative Search**: Systematically explore the space of possible small programs.
- **Implement Template Filling**: Use the "synaptic weights" to select code templates (e.g., "Recursion Template" vs "Loop Template") based on the input.

## How to "Build" and Run
The project is set up as a Python package.

1.  **Install Dependencies**:
    ```bash
    pip install fastapi uvicorn sympy scikit-learn numpy
    # Optional but recommended for "Real" proof capabilities:
    pip install z3-solver
    ```

2.  **Run the Brain**:
    ```bash
    python run_app.py
    ```
    This launches the backend API and the Dashboard.

3.  **Interact**:
    - Open `http://localhost:8000`.
    - Type "Solve x + 10 = 50" -> The brain should parse this as MATH, extract the equation, search for `x`, and verify it.
    - Type "Write a function to add two numbers" -> The brain should parse as CODING and synthesize `def solve(a,b): return a+b`.

## Next Steps for "Real AI" Behavior
- **Refine the Heuristics**: The `native_neural_lobe.py` is currently very simple. You can make it "smarter" by training it on a small dataset of `(text, spec)` pairs to update `synaptic_core.json`.
- **Add "Continuous Learning"**: Ensure `grow()` is called after every success. The more you use it, the better the weights in `synaptic_core.json` become.
