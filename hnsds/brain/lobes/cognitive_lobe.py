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

        # INVENTION: Metaphysical Blueprints (First Principles of the Universe)
        self.blueprints = self._load_blueprints()

        # Universal Mental Axioms
        self.axioms = {
            "REDUCTION": "Simplifying a complex expression to a primitive value.",
            "COMPOSITION": "Linking disparate entities through logical constraints.",
            "SYNTHESIS": "Constructing a new procedural logic to bridge a gap.",
            "TRANSFORMATION": "Converting one state of information to another."
        }

    def _load_blueprints(self):
        path = "hnsds/learner/metaphysical_blueprint.json"
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {}

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
        INVENTION: Multi-Modal Environmental Awareness.
        Detects text, JSON, or CSV and builds a Structural Map.
        """
        self.logger.info("COMPREHENDING_ENVIRONMENT...")
        
        raw = whole_block.strip()
        structured_entities = []
        
        # 1. Detect JSON Multi-Modal Input
        if (raw.startswith('{') and raw.endswith('}')) or (raw.startswith('[') and raw.endswith(']')):
            try:
                data = json.loads(raw)
                self.logger.info("MODALITY_DETECTED: JSON")
                structured_entities = self._flatten_structured_data(data)
            except: pass

        # 2. Detect CSV Multi-Modal Input
        elif "," in raw and "\n" in raw and any(line.count(",") > 1 for line in raw.split("\n")[:2]):
            self.logger.info("MODALITY_DETECTED: CSV")
            structured_entities = self._parse_csv_modality(raw)

        # 3. Standard Text Perception
        concepts = self._project_to_ontology(whole_block)
        entities = self._extract_entities(whole_block) + structured_entities
        intent = self._infer_intent(whole_block, concepts)

        env = {
            "entities": list(set(entities)), # Deduplicate
            "existing_logic": self._map_logic_rules(whole_block),
            "active_concepts": concepts,
            "intent": intent,
            "raw": whole_block
        }

        self.logger.info(f"ENVIRONMENT_MAP: {len(env['entities'])} entities, {len(env['active_concepts'])} concepts, Intent: {intent['master_concept']}")

        return env

    def _flatten_structured_data(self, data, prefix=""):
        # Converts JSON keys/values into addressable entities
        entities = []
        if isinstance(data, dict):
            for k, v in data.items():
                entities.append(f"{k}")
                entities.extend(self._flatten_structured_data(v, prefix=f"{k}_"))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                entities.extend(self._flatten_structured_data(item, prefix=f"item{i}_"))
        else:
            entities.append(str(data))
        return entities

    def _parse_csv_modality(self, raw):
        # Converts CSV rows into logical entities
        entities = []
        lines = raw.split("\n")
        if len(lines) > 1:
            headers = [h.strip() for h in lines[0].split(",")]
            entities.extend(headers)
            for line in lines[1:]:
                values = [v.strip() for v in line.split(",")]
                entities.extend(values)
        return entities

    def deliberate(self, environment):
        """
        Deliberation Phase: 
        1. Comprehend the 'State Delta' (The GAP between Initial and Goal states).
        2. Apply Mental Axioms to bridge the gap.
        3. Explain the reasoning trace.
        """
        intent = environment["intent"]
        concepts = set(environment["active_concepts"])
        master_concept = intent["master_concept"]

        # 1. ANALOGICAL COMPREHENSION: Map to Mastery
        best_mastery = None
        best_score = 0.0

        for concept_name, mastered_instances in self.mental_library.items():
            for mastery in mastered_instances:
                mastery_concepts = set(mastery.get("concepts", []))
                
                # Semantic Similarity of the Environment
                score = self._compute_semantic_similarity(concepts, mastery_concepts, master_concept, mastery.get("intent"))
                
                if score > best_score:
                    best_score = score
                    best_mastery = mastery

        # 2. BRIDGE THE GAP: Transform Intent into a Sigma (╬ú) Contract
        if best_mastery and best_score > 0.2:
            selected_axiom = best_mastery["axiom"]
            self.logger.info(f"INTENT_MAPPED: '{master_concept}' to Axiom '{selected_axiom}' (Score: {best_score:.2f})")
            sigma = self._bridge_gap_intelligently(environment, best_mastery)
            rationale = f"I understand this is a '{master_concept}' request requiring '{selected_axiom}' logic based on my mastery of '{best_mastery.get('name', 'Unknown')}'. I have identified {len(environment['entities'])} entities to process."
        
        # INVENTION: Zero-Shot Axiomatic Application (Understanding without explicit lesson)
        elif master_concept != "UNKNOWN" and intent.get("axiom") != "TRANSFORMATION":
            selected_axiom = intent["axiom"]
            self.logger.info(f"ZERO_SHOT_INTENT: '{master_concept}' mapped to Axiom '{selected_axiom}'")
            
            # Use a generic mastery template for the axiom
            generic_mastery = {"axiom": selected_axiom, "target_type": "math" if selected_axiom == "REDUCTION" else "logic"}
            sigma = self._bridge_gap_intelligently(environment, generic_mastery)
            rationale = f"I have inferred your intent as '{master_concept}' and am applying my core '{selected_axiom}' axiom to bridge the state gap."
        
        else:
            self.logger.warning("LOW_COMPREHENSION: Falling back to TRANSFORMATION (Conversational).")

            selected_axiom = "TRANSFORMATION"
            
            # DYNAMIC CONVERSATIONAL RESPONSE GENERATION (No Hardcoding)
            entities_str = ", ".join(environment['entities']) if environment['entities'] else "no specific entities"
            concepts_str = ", ".join(concepts) if concepts else "general concepts"
            
            if master_concept == "UNKNOWN" and not environment['entities']:
                dynamic_response = "I am receiving your input, but it does not contain structural entities or a recognizable intent for me to process."
            elif master_concept == "UNKNOWN":
                dynamic_response = f"I perceive you are discussing [{entities_str}] related to [{concepts_str}], but I cannot infer a clear actionable intent. You can use the 'teach:' command to prime my understanding."
            else:
                dynamic_response = f"I understand you want to '{master_concept}' involving [{entities_str}]. However, I have not yet been taught the conceptual mastery required to bridge this specific state gap. Please teach me the underlying logic first."

            sigma = {"type": "conversational", "response": dynamic_response}
            rationale = f"Mapped to TRANSFORMATION. Identified entities: {entities_str}. Missing axiomatic mastery for intent: {master_concept}."

        return {
            "axiom": selected_axiom,
            "environment": environment,
            "goal": sigma,
            "confidence": best_score,
            "rationale": rationale
        }

    def _infer_intent(self, text, concepts):
        """
        Intelligent Intent Inference:
        Traverses the Symbolic Knowledge Graph to determine intent and required axioms.
        No hardcoded dictionaries are used.
        """
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        master_concept = "UNKNOWN"
        target_axiom = "TRANSFORMATION"

        # 1. Graph Traversal for Direct Intent
        for word in words:
            # Check if this word directly maps to an axiom in the ontology
            mapped_axioms = self.ontology.get_related(word, "MAPS_TO_AXIOM")
            if mapped_axioms:
                master_concept = word.upper()
                target_axiom = mapped_axioms[0].upper()
                break
        
        # 2. Graph Traversal via Concepts (Implicit Intent)
        if master_concept == "UNKNOWN":
            for concept in concepts:
                mapped_axioms = self.ontology.get_related(concept, "MAPS_TO_AXIOM")
                if mapped_axioms:
                    master_concept = concept.upper()
                    target_axiom = mapped_axioms[0].upper()
                    break

        return {
            "master_concept": master_concept,
            "axiom": target_axiom,
            "entities": self._extract_entities(text)
        }

    def _compute_semantic_similarity(self, c1, c2, i1, i2):
        # Weighted Similarity: Concept Overlap (40%) + Intent Match (60%)
        concept_overlap = len(c1.intersection(c2)) / len(c1.union(c2)) if c1.union(c2) else 0
        intent_match = 1.0 if i1 == i2 else 0.0
        return (concept_overlap * 0.4) + (intent_match * 0.6)

    def _bridge_gap_intelligently(self, env, mastery):
        """
        The Intelligent Bridge: 
        Uses the 'Internal Knowledge' of the brain to extract the necessary logic for the Σ contract.
        Instead of regex, it looks for relationships between entities.
        """
        axiom = mastery["axiom"]
        raw = env["raw"]

        # 1. Base Sigma Contract (The 'Mental Target')
        # Ensure REDUCTION defaults to math so it hits the Z3 solver
        target_type = "math" if axiom == "REDUCTION" else mastery.get("target_type", "logic")
        sigma = {
            "type": target_type,
            "goal": mastery.get("target_goal", "solve"),
            "explanation_needed": True
        }

        # 2. Intelligent Logic Extraction (Mapping the 'World')
        if axiom == "REDUCTION":
            # Understand equations by identifying operators and equals relations
            sigma.update(self._comprehend_mathematical_environment(raw))
        elif axiom == "SYNTHESIS":
            sigma.update({"desc": raw, "goal": "synthesize", "complexity": "high" if "feature" in raw.lower() else "low"})
        elif axiom == "COMPOSITION":
            sigma.update({"problem": raw, "entities": env["entities"]})

        return sigma

    def _comprehend_mathematical_environment(self, text):
        """
        Intelligence: Extracts equations by identifying 'Mathematical Statements' 
        and 'Entity-Value Bindings'.
        """
        clean = text.lower().replace("find the total", "").replace("calculate", "").replace("result", "").strip()
        
        # 1. Direct Symbolic Identification
        clean = re.sub(r"\s*={1,2}\s*", " == ", clean)
        
        eqs = []
        # Split environment into separate logical clauses
        clauses = re.split(r'\band\b|,|;', clean)
        
        for clause in clauses:
            # Look for structured math (at least one var/num, operator, ==, var/num)
            # More constrained regex to avoid picking up whole sentences
            match = re.search(r"([a-z0-9\+\-\*\/\(\)\. ]+==[a-z0-9\+\-\*\/\(\)\. ]+)", clause)
            if match:
                # Clean up residual conversational words from the edges
                eq = match.group(1).strip()
                words_to_strip = ["solve", "can", "you", "find", "prove", "if", "then", "the"]
                for w in words_to_strip:
                    eq = re.sub(r"\b" + w + r"\b", "", eq).strip()
                if "==" in eq:
                    eqs.append(eq)

        # 2. Conversational Binding ('base is 1000' -> 'base == 1000')
        bindings = re.findall(r"\b([a-z_]+)\s+(?:is|are|equals|to|was)\s+([0-9\.]+|[a-z_]+)\b", clean)
        for entity, value in bindings:
            eqs.append(f"{entity} == {value}")

        # 3. Aggregation Discovery ('total', 'sum', 'combined')
        vars_found = self._extract_variables(eqs)
        if "total" in text.lower() or "result" in text.lower() or "sum" in text.lower():
            goal_var = "total" if "total" in text.lower() else "result"
            if goal_var not in vars_found:
                assigned_vars = [v for v in vars_found if any(f"{v} ==" in e or f"{v}=" in e for e in eqs)]
                if assigned_vars:
                    sum_expr = " + ".join(assigned_vars)
                    eqs.append(f"{goal_var} == {sum_expr}")

        return {
            "equations": list(set([e.strip() for e in eqs if e.strip()])),
            "variables": self._extract_variables(eqs)
        }

    def _extract_entities(self, text):
        entities = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text))
        # Extended stop-word list to make dynamic conversational fallback smarter
        keywords = {
            "def", "class", "import", "return", "if", "else", "for", "while", "in", "is", "the", "a",
            "an", "and", "or", "but", "to", "of", "my", "i", "you", "we", "they", "he", "she", "it", 
            "about", "want", "need", "like", "hello", "hi", "hey", "name", "this", "that", "these", 
            "those", "am", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", 
            "does", "did", "will", "would", "could", "should", "can", "may", "might", "must", "with",
            "at", "by", "from", "up", "down", "on", "off", "over", "under", "again", "then", "once"
        }
        filtered = [e for e in entities if e.lower() not in keywords]
        return sorted(list(filtered))

    def _map_logic_rules(self, text):
        rules = []
        funcs = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)', text)
        for f in funcs:
            rules.append({"type": "PROCEDURE", "name": f[0], "args": f[1]})
        return rules

    def _project_to_ontology(self, text):
        concepts = set()
        text_lower = text.lower()
        for node in self.ontology.nodes.keys():
            if node in text_lower:
                if len(node) < 4 and not re.search(r'\b' + re.escape(node) + r'\b', text_lower):
                    continue
                canon = self.ontology.find_synonym(node)
                concepts.add(canon)
                for parent in self.ontology.get_related(canon, "IS_A"):
                    concepts.add(parent)
        return sorted(list(concepts))

    def _extract_variables(self, equations):
        vars_set = set()
        keywords = {"is", "are", "equals", "to", "was", "total", "result", "sum", "find", "solve", "calculate"}
        for eq in equations:
            # Find identifiers that aren't just numbers
            found = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", eq)
            for f in found:
                if f.lower() not in keywords:
                    vars_set.add(f)
        return sorted(list(vars_set))

    def teach_concept(self, concept_name, example_stimulus, axiom):
        """
        Teaching Phase: Updates the mental intelligence library with conceptual logic.
        """
        env = self.perceive_environment(example_stimulus)
        if concept_name not in self.mental_library:
            self.mental_library[concept_name] = []
        
        self.mental_library[concept_name].append({
            "name": concept_name,
            "axiom": axiom,
            "concepts": env["active_concepts"],
            "intent": env["intent"]["master_concept"]
        })
        self._save_library()
        self.logger.info(f"CONCEPT_MASTERED: '{concept_name}' mapped to Axiom {axiom}")
