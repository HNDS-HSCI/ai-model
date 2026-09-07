"""
Synthetic bootstrap corpus for the trainable semantic tagger.

No external dataset and no human labeling: every example is generated from
templates and labeled exactly, because we built the string ourselves. This
is the in-house replacement for hand-labeled training data -- the templates
encode the same domain knowledge that used to live only in regex/keyword
rules (hsci/language/semantic_compiler.py), but now as supervision for a
real trained model instead of the final decision-maker itself.

Label schema:
  Token roles (BIO):  O, B-KNOWN, I-KNOWN, B-UNKNOWN, I-UNKNOWN
  Sentence intent:    REDUCTION, COMPOSITION, SYNTHESIS, TRANSFORMATION
  Sentence relation:  NONE, ADD, SUBTRACT, MULTIPLY, DIVIDE, EQUALS,
                      POSSESSION, ACQUIRE, GREATER_THAN, LESS_THAN
"""
import random
from dataclasses import dataclass, field
from typing import List, Tuple

TOKEN_ROLES = ["O", "B-KNOWN", "I-KNOWN", "B-UNKNOWN", "I-UNKNOWN"]
INTENTS = ["REDUCTION", "COMPOSITION", "SYNTHESIS", "TRANSFORMATION"]
RELATIONS = [
    "NONE", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "EQUALS",
    "POSSESSION", "ACQUIRE", "GREATER_THAN", "LESS_THAN",
]

_NAMES = ["Sam", "Alex", "Maria", "the store", "the class", "John", "Priya"]
_NOUNS = ["apples", "marbles", "dollars", "books", "points", "candies"]


@dataclass
class LabeledExample:
    text: str
    entity_spans: List[Tuple[int, int, str]]  # (start_char, end_char, role) role in {KNOWN, UNKNOWN}
    intent: str
    relation: str


def _span_for(text: str, needle: str, occurrence: int = 0) -> Tuple[int, int]:
    start = -1
    idx = -1
    for _ in range(occurrence + 1):
        idx = text.find(needle, idx + 1)
        if idx == -1:
            raise ValueError(f"'{needle}' not found in '{text}'")
        start = idx
    return start, start + len(needle)


def _reduction_examples(rng: random.Random, n: int) -> List[LabeledExample]:
    templates = [
        ("What is {a} + {b}?", "ADD"),
        ("Solve {a} + {b}", "ADD"),
        ("Calculate the sum of {a} and {b}", "ADD"),
        ("Compute {a} plus {b}", "ADD"),
        ("Find the total of {a} and {b}", "ADD"),
        ("Add {a} and {b}", "ADD"),
        ("What is {a} - {b}?", "SUBTRACT"),
        ("Solve {a} - {b}", "SUBTRACT"),
        ("Subtract {b} from {a}", "SUBTRACT"),
        ("What is the difference between {a} and {b}?", "SUBTRACT"),
        ("What is {a} * {b}?", "MULTIPLY"),
        ("Multiply {a} by {b}", "MULTIPLY"),
        ("What is the product of {a} and {b}?", "MULTIPLY"),
        ("What is {a} / {b}?", "DIVIDE"),
        ("Divide {a} by {b}", "DIVIDE"),
    ]
    out = []
    for _ in range(n):
        tmpl, rel = rng.choice(templates)
        a, b = rng.randint(1, 99), rng.randint(1, 99)
        text = tmpl.format(a=a, b=b)
        spans = [
            (*_span_for(text, str(a)), "KNOWN"),
            (*_span_for(text, str(b)), "KNOWN"),
        ]
        out.append(LabeledExample(text=text, entity_spans=spans, intent="REDUCTION", relation=rel))
    return out


def _composition_examples(rng: random.Random, n: int) -> List[LabeledExample]:
    templates_acquire = [
        "If {name} has {a} {noun} and gets {b} more, how many {noun} does {name} have now?",
        "{name} starts with {a} {noun} and receives {b} more {noun}.",
        "{name} has {a} {noun}. {name} buys {b} more.",
    ]
    templates_compare = [
        "{a} is greater than {b}",
        "{a} exceeds {b}",
        "{a} is less than {b}",
        "{a} is smaller than {b}",
    ]
    out = []
    for _ in range(n):
        if rng.random() < 0.6:
            tmpl = rng.choice(templates_acquire)
            name, noun = rng.choice(_NAMES), rng.choice(_NOUNS)
            a, b = rng.randint(1, 50), rng.randint(1, 50)
            text = tmpl.format(name=name, noun=noun, a=a, b=b)
            spans = [
                (*_span_for(text, str(a)), "KNOWN"),
                (*_span_for(text, str(b)), "KNOWN"),
            ]
            out.append(LabeledExample(text=text, entity_spans=spans, intent="COMPOSITION", relation="ACQUIRE"))
        else:
            tmpl = rng.choice(templates_compare)
            a, b = rng.randint(1, 99), rng.randint(1, 99)
            text = tmpl.format(a=a, b=b)
            rel = "GREATER_THAN" if ("greater" in tmpl or "exceeds" in tmpl) else "LESS_THAN"
            spans = [
                (*_span_for(text, str(a)), "KNOWN"),
                (*_span_for(text, str(b)), "KNOWN"),
            ]
            out.append(LabeledExample(text=text, entity_spans=spans, intent="COMPOSITION", relation=rel))
    return out


def _synthesis_examples(rng: random.Random, n: int) -> List[LabeledExample]:
    templates = [
        "write a function to add two numbers",
        "implement a program that calculates the sum of two numbers",
        "write code to check if a number is prime",
        "create a script that reverses a string",
        "build a function for computing a factorial",
        "implement an algorithm to sort a list",
    ]
    out = []
    for _ in range(n):
        text = rng.choice(templates)
        out.append(LabeledExample(text=text, entity_spans=[], intent="SYNTHESIS", relation="NONE"))
    return out


def _transformation_examples(rng: random.Random, n: int) -> List[LabeledExample]:
    templates = [
        "hi", "hello", "hey there", "who are you", "help", "greetings",
        "explain what addition means", "what can you do", "summarize this",
    ]
    out = []
    for _ in range(n):
        text = rng.choice(templates)
        out.append(LabeledExample(text=text, entity_spans=[], intent="TRANSFORMATION", relation="NONE"))
    return out


def generate_corpus(size: int = 2000, seed: int = 42) -> List[LabeledExample]:
    """Generates a balanced, exactly-labeled synthetic corpus across all 4 intents."""
    rng = random.Random(seed)
    per_bucket = size // 4
    examples = (
        _reduction_examples(rng, per_bucket)
        + _composition_examples(rng, per_bucket)
        + _synthesis_examples(rng, per_bucket)
        + _transformation_examples(rng, size - 3 * per_bucket)
    )
    rng.shuffle(examples)
    return examples
