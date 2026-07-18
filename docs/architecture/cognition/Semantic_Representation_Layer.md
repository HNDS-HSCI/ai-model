# HSCI V4 — Semantic Representation Layer (Semantic_Representation_Layer.md)

This document specifies the internal Language of Thought (LoT) schema that serves as the universal semantic representation for all ingestion sources (text, PDF, speech, images, APIs, and source code).

---

## 1. The Language of Thought (LoT) Schema

HSCI does not reason in English. It translates all inputs into a structured predicate-logic graph notation composed of:
1.  **Semantic Term (Node)**: An ontological concept coordinate (e.g. `concept.oop.inheritance`).
2.  **Predicate (Edge)**: A typed logical relation constraint (e.g. `specializes_to`).
3.  **Logical Quantifier**: SMT boundary definitions (e.g. \(\forall x, P(x) \rightarrow Q(x)\)).

---

## 2. Ingestion Format Normalization

Different modalities map to identical LoT formats:

*   **PDF / Books**: Text parsing extracts hierarchical concepts (chapter \(\rightarrow\) sections) and assertion relations.
*   **Source Code**: AST tokenization extracts structural dependency graphs (class definitions, function calls, usage scopes).
*   **Live APIs**: JSON responses map variables directly to entity attributes and property updates.
*   **Images**: Visual object detection maps objects and positions into spatial topology maps (e.g. `c_obj_1` `left_of` `c_obj_2`).

---

## 3. Core Dimensions Representation

### 3.1 Time and Space
*   **Temporal Dimension**: Represented using relative interval logic (Allen's Interval Algebra: `BEFORE`, `MEETS`, `OVERLAPS`, `DURING`) and anchored to Unix millisecond timestamps.
*   **Spatial Dimension**: Modeled topologically (`INSIDE`, `OUTSIDE`, `ADJACENT_TO`) or coordinate-mapped using coordinate boundaries.

### 3.2 Uncertainty and Confidence
Every LoT assertion carries a confidence evaluation (\(P_{conf} \in [0.0, 1.0]\)). Logic engines treat values above \(0.85\) as deterministic facts and values below as candidate hypotheses undergoing further SMT validation checks.

### 3.3 Goals and Procedures
*   **Goal Representation**: Formulated as target-state predicates (e.g. `Goal: state(room_temp) == 22`).
*   **Procedural Representation**: Sequenced Action blocks mapped as Hierarchical Task Network (HTN) task schemas.
