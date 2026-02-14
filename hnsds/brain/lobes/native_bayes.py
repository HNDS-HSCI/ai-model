import json
import math
import re
from collections import defaultdict, Counter

class NativeBayesClassifier:
    """
    INVENTION: Native Bayesian Cortex.
    
    A pure Python implementation of a Naive Bayes classifier.
    It provides the 'Intuition' for the brain by calculating
    the probabilistic likelihood of an intent given a stimulus.
    
    P(Intent | Words) \propto P(Intent) * \Prod P(Word | Intent)
    """
    def __init__(self, memory_path="episodes.jsonl"):
        self.memory_path = memory_path
        self.classes = set()
        self.word_counts = defaultdict(Counter) # {class: {word: count}}
        self.class_counts = Counter() # {class: total_docs}
        self.vocab = set()
        self.total_docs = 0
        
        # Load initial memory
        self._seed_axioms() # Always seed base knowledge
        self.train_from_episodic_memory()

    def train(self, text, label):
        """Online training with a single example."""
        self.classes.add(label)
        self.class_counts[label] += 1
        self.total_docs += 1
        
        words = self._tokenize(text)
        for w in words:
            self.vocab.add(w)
            self.word_counts[label][w] += 1

    def train_from_episodic_memory(self):
        """Bootstraps intelligence from past episodes."""
        try:
            with open(self.memory_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        text = data.get("goal_str", "")
                        
                        # Determine label from goal_obj
                        goal_obj = data.get("goal_obj", {})
                        if isinstance(goal_obj, dict):
                            label = goal_obj.get("type", "conversational").upper()
                        else:
                            label = "CONVERSATIONAL"
                            
                        if text and label:
                            self.train(text, label)
                    except:
                        continue
        except FileNotFoundError:
            # Seed with basic axioms if memory is empty
            self._seed_axioms()

    def _seed_axioms(self):
        """Hardcoded axioms to start the brain if no memory exists."""
        seeds = [
            ("solve x + y", "MATH"),
            ("calculate sum", "MATH"),
            ("what is 5 * 5", "MATH"),
            ("write a python function", "CODING"),
            ("code fibonacci", "CODING"),
            ("implement a sort", "CODING"),
            ("hello how are you", "CONVERSATIONAL"),
            ("explain this", "CONVERSATIONAL")
        ]
        for t, l in seeds:
            self.train(t, l)

    def predict(self, text):
        """
        Returns the most probable intent and its log-probability score.
        """
        words = self._tokenize(text)
        best_label = None
        best_score = -float('inf')
        
        scores = {}
        
        for label in self.classes:
            # Log-probability to avoid underflow
            # P(Label)
            score = math.log(self.class_counts[label] / self.total_docs)
            
            # Sum log P(Word | Label)
            total_words_in_class = sum(self.word_counts[label].values())
            vocab_size = len(self.vocab)
            
            for w in words:
                # Laplace Smoothing (+1)
                count = self.word_counts[label].get(w, 0) + 1
                prob = count / (total_words_in_class + vocab_size)
                score += math.log(prob)
            
            scores[label] = score
            
            if score > best_score:
                best_score = score
                best_label = label
                
        return best_label, scores

    def _tokenize(self, text):
        return [w.lower() for w in re.findall(r'\w+', text)]

    def save_state(self, path="bayes_weights.json"):
        # Serialization logic could go here
        pass
