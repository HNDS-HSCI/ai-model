"""Closed-class English grammar and morphology.

Only *function words* live here (determiners, copulas, pronouns, quantifiers,
prepositions, wh-words). These are a small, finite part of any language and carry
no world knowledge. Open-class words -- nouns, adjectives, verbs, names -- are never
listed: they become symbols the moment the user uses them.

Normalisation is applied identically to statements and questions, so even an
imperfect lemma ("analyses" -> "analysis") is consistent end to end.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

_DATA = os.path.join(os.path.dirname(__file__), "data", "morphology.json")

ARTICLES = {"a", "an"}
DEFINITE = {"the"}
UNIVERSAL = {"all", "every", "each", "any"}
EXISTENTIAL = {"some"}
NEGATIVE_QUANT = {"no"}
POSSESSIVE_DET = {"my", "your", "his", "her", "its", "our", "their"}
DETERMINERS = ARTICLES | DEFINITE | UNIVERSAL | EXISTENTIAL | NEGATIVE_QUANT | POSSESSIVE_DET
COPULA_SG = {"is", "was"}
COPULA_PL = {"are", "were", "am"}
COPULAS = COPULA_SG | COPULA_PL
DO_AUX = {"do", "does", "did"}
MODALS = {"can", "could", "will", "would", "should", "must", "may", "might"}
NEGATORS = {"not", "never", "n't"}
VARIABLE_WORDS = {"someone", "something", "somebody", "anyone", "anything", "anybody",
                  "everyone", "everything", "everybody", "one", "person"}
PRONOUNS = {"it", "they", "them", "he", "she", "him", "her", "this", "that", "these", "those"}
RELATIVE = {"who", "that", "which"}
WH = {"who", "what", "which", "whom", "whose", "where", "when", "why", "how"}
PREPOSITIONS = {"in", "on", "at", "under", "over", "above", "below", "near", "inside", "outside",
                "with", "from", "to", "into", "of", "behind", "beside", "between", "by", "for",
                "within", "without", "after", "before", "next"}
CONJ = {"and", "or", "but"}

FUNCTION_WORDS = (DETERMINERS | COPULAS | DO_AUX | MODALS | NEGATORS | PRONOUNS | RELATIVE | WH
                  | CONJ | {"than", "if", "then", "there", "as", "so", "also", "too", "very"})


@lru_cache(maxsize=1)
def _morph() -> dict:
    with open(_DATA, encoding="utf-8") as fh:
        return json.load(fh)


def singularize(word: str) -> str:
    w = word.lower()
    m = _morph()
    if w in m["irregular_plurals"]:
        return m["irregular_plurals"][w]
    if w in m["uncountable_s_endings"] or len(w) <= 3:
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    for suf in ("sses", "ches", "shes", "xes", "zzes", "oes"):
        if w.endswith(suf):
            return w[:-2]
    if w.endswith("ss") or w.endswith("us") or w.endswith("is"):
        return w
    if w.endswith("s"):
        return w[:-1]
    return w


def looks_plural(word: str) -> bool:
    return singularize(word) != word.lower()


def verb_lemma(word: str) -> str:
    w = word.lower()
    m = _morph()
    if w in m["irregular_verbs"]:
        return m["irregular_verbs"][w]
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    for suf in ("sses", "ches", "shes", "xes", "zzes", "oes"):
        if w.endswith(suf):
            return w[:-2]
    if w.endswith("ss") or w.endswith("us"):
        return w
    if w.endswith("s") and len(w) > 2:
        return w[:-1]
    return w


def third_person(verb: str) -> str:
    """Inverse of verb_lemma, used only for generating English."""
    if verb == "be":
        return "is"
    if verb == "have":
        return "has"
    if verb.endswith("y") and len(verb) > 2 and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
    if verb.endswith(("s", "sh", "ch", "x", "z", "o")):
        return verb + "es"
    return verb + "s"


def superlative_to_comparative(word: str) -> str | None:
    """'youngest' -> 'younger', 'best' -> 'better'. None if not a superlative form."""
    w = word.lower()
    irregular = {"best": "better", "worst": "worse", "most": "more", "least": "less",
                 "eldest": "elder", "furthest": "further", "farthest": "farther"}
    if w in irregular:
        return irregular[w]
    if w.endswith("est") and len(w) > 4:
        return w[:-3] + "er"
    return None


def article_for(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def pluralize(noun: str) -> str:
    inv = {v: k for k, v in _morph()["irregular_plurals"].items() if v != k}
    if noun in inv:
        return inv[noun]
    if noun.endswith("y") and len(noun) > 2 and noun[-2] not in "aeiou":
        return noun[:-1] + "ies"
    if noun.endswith(("s", "sh", "ch", "x", "z")):
        return noun + "es"
    return noun + "s"
