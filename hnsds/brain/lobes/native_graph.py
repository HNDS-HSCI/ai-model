import json
import os

class NativeGraph:
    """
    INVENTION: The Symbolic Knowledge Graph.
    
    Stores explicit relationships between concepts.
    Replaces 'Hidden Weights' with 'Visible Edges'.
    
    Structure:
    - Nodes: Concepts (e.g., "Sort", "QuickSort", "Algorithm")
    - Edges: Relationships (e.g., "IS_A", "RELATED_TO", "IMPLEMENTS")
    """
    def __init__(self, path="hnsds/brain/knowledge/concept_graph.json"):
        self.path = path
        self.nodes = {} # {concept: {relation: [concepts]}}
        self._load()

    def add_relation(self, subject, relation, object_):
        subj = subject.lower()
        obj = object_.lower()
        rel = relation.upper()
        
        if subj not in self.nodes: self.nodes[subj] = {}
        if rel not in self.nodes[subj]: self.nodes[subj][rel] = []
        
        if obj not in self.nodes[subj][rel]:
            self.nodes[subj][rel].append(obj)
            self._save()

    def get_related(self, concept, relation=None):
        """
        Symbolic Traversal: Finds related concepts.
        """
        c = concept.lower()
        if c not in self.nodes: return []
        
        if relation:
            return self.nodes[c].get(relation.upper(), [])
        
        # Return all related
        all_related = []
        for rel in self.nodes[c]:
            all_related.extend(self.nodes[c][rel])
        return all_related

    def find_synonym(self, word):
        """
        Traverses 'SYNONYM_OF' edges to normalize concepts.
        """
        related = self.get_related(word, "SYNONYM_OF")
        if related:
            return related[0] # Return canonical form
        return word

    def _save(self):
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(self.nodes, f, indent=2)

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.nodes = json.load(f)
            except: pass
        else:
            # Seed with primordial knowledge
            self._seed_knowledge()

    def _seed_knowledge(self):
        # Base Ontology
        self.add_relation("total", "SYNONYM_OF", "sum")
        self.add_relation("plus", "SYNONYM_OF", "sum")
        self.add_relation("combine", "SYNONYM_OF", "sum")
        self.add_relation("minus", "SYNONYM_OF", "subtract")
        self.add_relation("difference", "SYNONYM_OF", "subtract")
        self.add_relation("arrange", "SYNONYM_OF", "sort")
        self.add_relation("order", "SYNONYM_OF", "sort")
        self.add_relation("fib", "SYNONYM_OF", "fibonacci")
        
        # Coding Ontology
        self.add_relation("write", "SYNONYM_OF", "software_engineering")
        self.add_relation("function", "SYNONYM_OF", "algorithm")
        self.add_relation("script", "SYNONYM_OF", "software_engineering")
        self.add_relation("implement", "SYNONYM_OF", "software_engineering")
        
        # Logic Ontology
        self.add_relation("houses", "SYNONYM_OF", "logic_puzzle")
        self.add_relation("lives", "SYNONYM_OF", "logic_puzzle")
        self.add_relation("neighbor", "SYNONYM_OF", "logic_puzzle")
        self.add_relation("next to", "SYNONYM_OF", "logic_puzzle")
        
        # HR Ontology (Human Resources)
        self.add_relation("wages", "SYNONYM_OF", "salary")
        self.add_relation("pay", "SYNONYM_OF", "salary")
        self.add_relation("compensation", "SYNONYM_OF", "salary")
        self.add_relation("hiring", "SYNONYM_OF", "recruitment")
        self.add_relation("staff", "SYNONYM_OF", "employee")
        self.add_relation("workforce", "SYNONYM_OF", "employee")
        
        # Hierarchical Knowledge (The "Ontology")
        self.add_relation("sum", "IS_A", "math_operation")
        self.add_relation("sort", "IS_A", "algorithm")
        self.add_relation("salary", "IS_A", "financial_record")
