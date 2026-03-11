import re
import json
import os
import logging
from hnsds.brain.lobes.native_graph import NativeGraph

class CognitiveAwareness:
    """
    INVENTION: The Environmental Awareness Lobe.
    
    NEW ARCHITECTURE: Cognitive State-Space Environment.
    Treats the whole input as a "Logical Environment" with its own rules and state.
    Instead of 'Intents', it identifies 'Conceptual Gaps' and applies 'Mental Axioms'.
    """
    def __init__(self, memory_path="mental_intelligence.json"):
        self.logger = logging.getLogger("CognitiveAwareness")
        self.ontology = NativeGraph()
        self.memory_path = memory_path
        # Learned Conceptual Logic (Mastery of Principles)
        self.mental_library = self._load_library()
        
        # Universal Mental Axioms (The System's Core Reasoning Capabilities)
        self.axioms = {
            "REDUCTION": "Simplifying a complex expression to a primitive value.",
            "COMPOSITION": "Linking disparate entities through logical constraints.",
            "SYNTHESIS": "Constructing a new procedural logic to bridge a gap.",
            "TRANSFORMATION": "Converting one state of information to another."
        }

    def _load_library(self):
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, 'r') as f:
                    return json.load(f)
            except: pass
        return {}

    def _save_library(self):
        with open(self.memory_path, 'w') as f:
            json.dump(self.mental_library, f, indent=2)

    def perceive_environment(self, whole_block):
        """
        Absorbs the whole context and builds a Mental Map of the Environment.
        """
        self.logger.info("COMPREHENDING_ENVIRONMENT...")

        env = {
            "entities": self._extract_entities(whole_block),
            "existing_logic": self._map_logic_rules(whole_block),
            "active_concepts": self._project_to_ontology(whole_block),
            "raw": whole_block
        }

        self.logger.info(f"ENVIRONMENT_MAP: {len(env['entities'])} entities, {len(env['active_concepts'])} concepts.")

        return env

    def deliberate(self, environment):
        """
        Identifies the GAP in the environment and selects the AXIOM to bridge it.
        Uses pure learned intelligence (from the mental_library) to perform analogical reasoning.
        """
        concepts = set(environment["active_concepts"])

        # 1. Identify the 'State Delta' (What is missing or requested?)
        # We look for Conceptual Mastery in our library
        selected_axiom = "TRANSFORMATION" # Default fallback
        best_score = 0.0

        # Analogical Reasoning against Taught Masteries
        for concept_name, mastered_instances in self.mental_library.items():
            for mastery in mastered_instances:
                mastery_concepts = set(mastery["concepts"])

                # Jaccard similarity of conceptual environments
                union = concepts.union(mastery_concepts)
                if union:
                    score = len(concepts.intersection(mastery_concepts)) / len(union)
                    
                    # Context Type Match Bonus (if structure exists)
                    if environment.get("existing_logic") and mastery.get("structure"):
                         score += 0.1

                    if score > best_score:
                        best_score = score
                        selected_axiom = mastery["axiom"]

        # If confidence is too low, stay conversational
        if best_score < 0.2:
            selected_axiom = "TRANSFORMATION"

        self.logger.info(f"DELIBERATION_COMPLETE: Applying Axiom '{selected_axiom}' (Confidence: {best_score:.2f})")

        return {
            "axiom": selected_axiom,
            "environment": environment,
            "goal": self._derive_goal(environment, selected_axiom)
        }

    def _extract_entities(self, text):
        # Finds variables, function names, object names
        entities = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text))
        # Filter out keywords
        keywords = {"def", "class", "import", "return", "if", "else", "for", "while", "in", "is", "the", "a"}
        return list(entities - keywords)

    def _map_logic_rules(self, text):
        # Identifies existing function signatures or equations
        rules = []
        # Function detection
        funcs = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)', text)
        for f in funcs:
            rules.append({"type": "PROCEDURE", "name": f[0], "args": f[1]})
        # Equation detection
        eqs = re.findall(r'([a-z0-9\s\+\-\*\/\^]+=[a-z0-9\s\+\-\*\/\^]+)', text.lower())
        for e in eqs:
            rules.append({"type": "EQUATION", "raw": e})
        return rules

    def _project_to_ontology(self, text):
        concepts = set()
        text_lower = text.lower()
        for node in self.ontology.nodes.keys():
            if node in text_lower:
                # Basic boundary check to avoid partial word matches for short concepts
                if len(node) < 4 and not re.search(r'\b' + re.escape(node) + r'\b', text_lower):
                    continue
                
                canon = self.ontology.find_synonym(node)
                concepts.add(canon)
                for parent in self.ontology.get_related(canon, "IS_A"):
                    concepts.add(parent)
        return sorted(list(concepts))

    def _derive_goal(self, env, axiom):
        # Bridges the gap based on the axiom type
        if axiom == "SYNTHESIS":
            return {"type": "coding", "desc": env["raw"], "goal": "synthesize"}
        if axiom == "REDUCTION":
            # Extract math spec
            eqs = self._extract_equations(env["raw"])
            return {
                "type": "math" if len(eqs) <= 1 else "system",
                "equations": eqs,
                "variables": self._extract_variables(eqs),
                "goal": "solve"
            }
        if axiom == "COMPOSITION":
            return {"type": "logic", "raw": env["raw"], "goal": "solve"}
        
        return {"type": "conversational", "response": "Environmental awareness established. Processing state transformation."}

    def teach_concept(self, concept_name, example_stimulus, axiom):
        """
        Teaching Phase: Updates the mental intelligence library with conceptual logic.
        """
        env = self.perceive_environment(example_stimulus)
        if concept_name not in self.mental_library:
            self.mental_library[concept_name] = []
        
        self.mental_library[concept_name].append({
            "axiom": axiom,
            "concepts": env["active_concepts"],
            "structure": env["existing_logic"]
        })
        self._save_library()
        self.logger.info(f"CONCEPT_MASTERED: '{concept_name}' mapped to Axiom {axiom}")

    # Helpers
    def _extract_equations(self, text):
        clean_text = text.lower().replace("solve", "").strip()
        clean_text = re.sub(r"\s*={1,2}\s*", " == ", clean_text)
        matches = re.findall(r"([a-z0-9\s\+\-\*\/\(\)\.]+\s*==\s*[\-a-z0-9\s\+\-\*\/\(\)\.]+)", clean_text)
        return [m.strip() for m in matches if "==" in m]

    def _extract_variables(self, equations):
        vars_set = set()
        for eq in equations:
            vars_set.update(re.findall(r"\b[a-z]\b", eq))
        return sorted(list(vars_set))
    
    def propose_solution(self, sigma): return "x=0"
    def grow(self, stimulus, spec, intent): 
        # Map to axiom and teach
        mapping = {"MATH": "REDUCTION", "CODING": "SYNTHESIS", "LOGIC": "COMPOSITION"}
        self.teach_concept(intent, stimulus, mapping.get(intent, "TRANSFORMATION"))
