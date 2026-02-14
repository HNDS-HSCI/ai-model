import json
import os
import hashlib
from .native_graph import NativeGraph

class NativeEmbedding:
    """
    INVENTION: The Semantic Embedding Layer.
    
    Converts raw text into a fixed-size vector representation.
    Since we can't use pre-trained Word2Vec, we use 'Hashed Fingerprinting'
    initially, which allows the Neural Net to learn associations.
    """
    def __init__(self, vocab_size=200):
        self.vocab_size = vocab_size
        self.graph = NativeGraph()
        
        # Deterministic slots for key concepts to avoid hash collisions in small brains
        self.reserved_slots = {
            "solve": 10, "calculate": 11, "compute": 12, "math": 13, "add": 14, "sum": 15,
            "write": 30, "code": 31, "function": 32, "python": 33, "implement": 34,
            "hello": 50, "hi": 51, "who": 52, "explain": 53, "name": 54,
            "salary": 60, "payroll": 61, "employee": 62, "staff": 63, "hiring": 64
        }

    def embed(self, text):
        """
        Converts text to a Bag-of-Vectors (normalized frequency).
        """
        vector = [0.0] * self.vocab_size
        words = text.lower().split()
        
        stop_words = {"a", "the", "to", "of", "in", "for", "on", "with", "write", "program", "function"}
        
        if not words: return vector
        
        for w in words:
            if w in stop_words: continue
            
            # Concept Normalization
            w = self._normalize(w)
            
            idx = 0
            if w in self.reserved_slots:
                idx = self.reserved_slots[w]
            else:
                # Hash trick for unknown words
                idx = int(hashlib.md5(w.encode()).hexdigest(), 16) % self.vocab_size
                
            vector[idx] += 1.0
            
        # Normalize
        magnitude = sum(x**2 for x in vector) ** 0.5
        if magnitude > 0:
            vector = [x / magnitude for x in vector]
            
        return vector

    def _normalize(self, word):
        """
        Maps synonyms to a canonical concept using the Symbolic Graph.
        """
        # Ask the Knowledge Graph for the canonical form
        canonical = self.graph.find_synonym(word)
        return canonical
