"""Compositional mathematical structure builder for HSCI Interpretation
(Cognitive Substrate Final Review, "Interpretation Extension").

Converts a math-shaped utterance -- symbolic ("x + 10 = 20") or natural
language ("a number increased by 10 is 20") -- into the SAME typed
representation Step 1 (semantic_model.py) already defined: EntityMention
(role=QUANTITY/VARIABLE) and SemanticRelation (OPERATION:*/EQUALS). This
module introduces no second, parallel mathematical data model.

This module performs NO solving and imports nothing from SymPy, Z3, or
hsci.reasoning.universal_math_engine -- it only recognizes structure. It
answers "what does this utterance assert?", never "what is the answer?".

Composition is achieved by combining three small, reusable, general steps
(not a per-sentence or per-question rule table):

  1. ATOM recognition (_classify_atom) -- is this span a bare numeral, or
     one of a small closed set of noun phrases that denote "the unknown
     quantity" ("a number", "the value", a single-letter symbol, ...)?
  2. PREDICATE recognition (_OPERATION_FRAMES / _parse_expression) -- does
     this span contain one of a small closed set of operation-denoting
     grammatical frames ("X plus Y", "X increased by Y", "Y added to X",
     "Y less than X" [reversed argument order], "X doubled", "X multiplied
     by Y", "X divided by Y", ...), each carrying its own operation type
     and argument roles? Some frames' surface word order differs from their
     mathematical argument order (see the "less than" frame below) -- the
     frame definition itself encodes the correct role, so this is resolved
     by which named regex group is which, not by any special-cased text.
  3. EQUALITY recognition (_compose_natural_language / _compose_symbolic)
     -- splits "<LHS> <copula> <RHS>" (or "<LHS> = <RHS>") once, then
     recurses steps 1-2 on each side.

If any step cannot confidently resolve a span, the whole function returns
None -- callers must fall back to their existing behavior rather than
guess. This module never manufactures a variable, operation, or equation
merely because the input contains numbers.

Explicitly out of scope (falls through to None, not a crash, not a guess):
quadratic/exponent terms ("x^2"), explicit-multiplication coefficients
("5*x" -- only implicit "5x" is supported), multi-variable systems, and
bare arithmetic with no unknown and no equality ("144 / 12" alone).
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from hsci.cognition.interpretation.semantic_model import (
    EntityMention,
    EntityRole,
    SemanticRelation,
)

# ---------------------------------------------------------------------------
# Normalization -- deliberately minimal and self-contained. NOT imported
# from hsci.reasoning.universal_math_engine, so Interpret stays fully
# decoupled from the solving layer (Cognitive Substrate Final Review §1.1).
# ---------------------------------------------------------------------------

_LEADING_COMMAND_RE = re.compile(
    r"^(?:solve|calc\w*|comput\w*|eval\w*|find)\s+(?:the\s+)?(?:value\s+of\s+)?(?:for\s+)?",
    re.IGNORECASE,
)
_LEADING_WHAT_IS_RE = re.compile(r"^what\s+is\s+", re.IGNORECASE)
_TRAILING_PUNCT_RE = re.compile(r"[\s?.!]+$")
_THOUSANDS_COMMA_RE = re.compile(r"(?<=\d),(?=\d{3}\b)")


def _normalize(text: str) -> str:
    t = (text or "").strip()
    t = _THOUSANDS_COMMA_RE.sub("", t)
    t = _LEADING_COMMAND_RE.sub("", t)
    t = _LEADING_WHAT_IS_RE.sub("", t)
    t = _TRAILING_PUNCT_RE.sub("", t)
    return t.strip()


# ---------------------------------------------------------------------------
# Step 1: ATOM recognition -- a single QUANTITY or VARIABLE.
# ---------------------------------------------------------------------------

_NUMERIC_ATOM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

# A small, closed set of noun phrases denoting "the unknown quantity being
# solved for" -- linguistic knowledge (recognizing a referring expression),
# not a per-question rule; none of these phrases encode any answer.
_VARIABLE_PHRASES = {
    "a number", "the number", "a value", "the value",
    "an unknown number", "an unknown value", "the unknown", "an unknown",
    "the original number", "the original value",
}


@dataclass
class _Atom:
    surface_form: str
    role: "EntityRole"
    numeric_value: Optional[float] = None


def _classify_atom(span: str) -> Optional[_Atom]:
    s = span.strip().strip(".,;:!?")
    if not s:
        return None
    if _NUMERIC_ATOM_RE.match(s):
        return _Atom(surface_form=s, role=EntityRole.QUANTITY, numeric_value=float(s))
    if s.lower() in _VARIABLE_PHRASES:
        return _Atom(surface_form=s, role=EntityRole.VARIABLE)
    if re.fullmatch(r"[a-zA-Z]", s):  # a single symbolic letter, e.g. "x"
        return _Atom(surface_form=s, role=EntityRole.VARIABLE)
    return None


# ---------------------------------------------------------------------------
# Mention/relation emission helpers, shared by the symbolic and
# natural-language composers below.
# ---------------------------------------------------------------------------

_OP_SYMBOL = {
    "OPERATION:ADD": "+",
    "OPERATION:SUBTRACT": "-",
    "OPERATION:MULTIPLY": "*",
    "OPERATION:DIVIDE": "/",
}


def _ensure_mention(mentions: List[EntityMention], atom: _Atom) -> None:
    if any(m.surface_form == atom.surface_form and m.role == atom.role for m in mentions):
        return
    mentions.append(EntityMention(
        surface_form=atom.surface_form,
        normalized_form=atom.surface_form.lower(),
        role=atom.role,
        numeric_value=atom.numeric_value,
        is_known=(atom.role == EntityRole.QUANTITY),
        confidence=0.95,
    ))


def _label(operand: Union[_Atom, str]) -> str:
    return operand.surface_form if isinstance(operand, _Atom) else operand


def _emit_binary_op(
    mentions: List[EntityMention],
    relations: List[SemanticRelation],
    left: Union[_Atom, str],
    op_type: str,
    right: Union[_Atom, str],
) -> str:
    """left/right are either an _Atom (a literal mention -- gets an
    EntityMention appended) or an already-composed synthetic result label
    from a prior operation (a plain str -- an intermediate expression, not
    itself a mention). Returns the synthetic label for THIS operation's
    result, for a caller to chain into a further operation or EQUALS.

    source_mention/target_mention ordering is preserved exactly as passed
    in (left -> source, right -> target), so SUBTRACT/DIVIDE read as
    "source op target" (source - target, source / target) -- callers are
    responsible for passing left/right in the correct semantic order,
    which is exactly what the frame definitions below encode.
    """
    if isinstance(left, _Atom):
        _ensure_mention(mentions, left)
    if isinstance(right, _Atom):
        _ensure_mention(mentions, right)
    left_label, right_label = _label(left), _label(right)
    relations.append(SemanticRelation(source_mention=left_label, relation_type=op_type, target_mention=right_label))
    return f"({left_label} {_OP_SYMBOL[op_type]} {right_label})"


def _emit_equals(mentions: List[EntityMention], relations: List[SemanticRelation], lhs_label: str, rhs_atom: _Atom) -> None:
    _ensure_mention(mentions, rhs_atom)
    relations.append(SemanticRelation(source_mention=lhs_label, relation_type="EQUALS", target_mention=rhs_atom.surface_form))


@dataclass
class ComposedStructure:
    mentions: List[EntityMention]
    relations: List[SemanticRelation]


# ---------------------------------------------------------------------------
# Symbolic composer: "x + 10 = 20", "3x + 7 = 25", "x - 5 = 12", "x / 4 = 3".
# ---------------------------------------------------------------------------

# An implicit-multiplication coefficient term, e.g. "3x" -> MULTIPLY(3, x).
# Deliberately does not match "5*x" (explicit "*") or "x^2" (exponent) --
# both out of scope for this step (see module docstring).
_COEFFICIENT_TERM_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([a-zA-Z])$")


def _compose_symbolic(text: str) -> Optional[ComposedStructure]:
    if "=" not in text or "==" in text:
        return None
    lhs_text, _, rhs_text = text.partition("=")
    lhs_text, rhs_text = lhs_text.strip(), rhs_text.strip()
    if not lhs_text or not rhs_text:
        return None

    rhs_atom = _classify_atom(rhs_text)
    if rhs_atom is None:
        return None

    mentions: List[EntityMention] = []
    relations: List[SemanticRelation] = []

    # A single division, no +/- chaining: "x / 4".
    if "/" in lhs_text and "+" not in lhs_text and "-" not in lhs_text:
        left_span, sep, right_span = lhs_text.partition("/")
        if sep:
            left_atom = _classify_atom(left_span)
            right_atom = _classify_atom(right_span)
            if left_atom is not None and right_atom is not None:
                result_label = _emit_binary_op(mentions, relations, left_atom, "OPERATION:DIVIDE", right_atom)
                _emit_equals(mentions, relations, result_label, rhs_atom)
                return ComposedStructure(mentions=mentions, relations=relations)
        return None

    # Additive/subtractive chain of terms, each term either a bare
    # QUANTITY/VARIABLE atom or an implicit coefficient*variable ("3x").
    raw_terms = re.findall(r"[+-]?\s*[^+-]+", lhs_text)
    if not raw_terms:
        return None

    parsed_terms: List[Tuple[str, str]] = []  # (sign, result_label)
    for raw_term in raw_terms:
        term = raw_term.strip()
        sign = "+"
        if term.startswith("+"):
            term = term[1:].strip()
        elif term.startswith("-"):
            sign = "-"
            term = term[1:].strip()
        if not term:
            return None

        coeff_m = _COEFFICIENT_TERM_RE.match(term)
        if coeff_m:
            coeff_atom = _Atom(surface_form=coeff_m.group(1), role=EntityRole.QUANTITY, numeric_value=float(coeff_m.group(1)))
            var_atom = _Atom(surface_form=coeff_m.group(2), role=EntityRole.VARIABLE)
            term_label = _emit_binary_op(mentions, relations, coeff_atom, "OPERATION:MULTIPLY", var_atom)
            parsed_terms.append((sign, term_label))
            continue

        atom = _classify_atom(term)
        if atom is None:
            return None  # an unrecognized term -- honest failure, no guess
        _ensure_mention(mentions, atom)
        parsed_terms.append((sign, atom.surface_form))

    if parsed_terms[0][0] != "+":
        return None  # a leading negative term ("-x + 10 = 20") is out of scope

    result_label = parsed_terms[0][1]
    for sign, term_label in parsed_terms[1:]:
        op = "OPERATION:ADD" if sign == "+" else "OPERATION:SUBTRACT"
        relations.append(SemanticRelation(source_mention=result_label, relation_type=op, target_mention=term_label))
        result_label = f"({result_label} {_OP_SYMBOL[op]} {term_label})"

    _emit_equals(mentions, relations, result_label, rhs_atom)
    return ComposedStructure(mentions=mentions, relations=relations)


# ---------------------------------------------------------------------------
# Natural-language composer: "a number increased by 10 is 20", etc.
# ---------------------------------------------------------------------------

# Each frame is (compiled_regex, operation_relation_type, implicit_operand).
# Every regex names its groups 'base' (the subject the operation applies
# to -- becomes source_mention) and, unless implicit_operand is given,
# 'operand' (the modifying quantity -- becomes target_mention). Group NAMES
# encode the correct semantic role regardless of surface word order: e.g.
# the "less than" frame captures the surface-first span as 'operand' (it is
# the subtrahend, not the base) precisely because English reverses their
# order ("12 less than a number" = a number - 12, not 12 - a number).
_FRAME_ADD_PLUS = re.compile(r"^(?P<base>.+?)\s+plus\s+(?P<operand>.+)$", re.IGNORECASE)
_FRAME_ADD_INCREASED = re.compile(r"^(?P<base>.+?)\s+increased\s+by\s+(?P<operand>.+)$", re.IGNORECASE)
_FRAME_ADD_ADDED_TO = re.compile(r"^(?P<operand>.+?)\s+added\s+to\s+(?P<base>.+)$", re.IGNORECASE)

_FRAME_SUB_MINUS = re.compile(r"^(?P<base>.+?)\s+minus\s+(?P<operand>.+)$", re.IGNORECASE)
_FRAME_SUB_DECREASED = re.compile(r"^(?P<base>.+?)\s+decreased\s+by\s+(?P<operand>.+)$", re.IGNORECASE)
_FRAME_SUB_REDUCED = re.compile(r"^(?P<base>.+?)\s+reduced\s+by\s+(?P<operand>.+)$", re.IGNORECASE)
_FRAME_SUB_LESS_THAN = re.compile(r"^(?P<operand>.+?)\s+less\s+than\s+(?P<base>.+)$", re.IGNORECASE)  # reversed

_FRAME_MUL_TIMES = re.compile(r"^(?P<base>.+?)\s+times\s+(?P<operand>.+)$", re.IGNORECASE)
_FRAME_MUL_MULTIPLIED = re.compile(r"^(?P<base>.+?)\s+multiplied\s+by\s+(?P<operand>.+)$", re.IGNORECASE)
_FRAME_MUL_DOUBLED = re.compile(r"^(?P<base>.+?)\s+doubled$", re.IGNORECASE)
_FRAME_MUL_TRIPLED = re.compile(r"^(?P<base>.+?)\s+tripled$", re.IGNORECASE)

_FRAME_DIV_DIVIDED = re.compile(r"^(?P<base>.+?)\s+divided\s+by\s+(?P<operand>.+)$", re.IGNORECASE)

_OPERATION_FRAMES: List[Tuple[re.Pattern, str, Optional[float]]] = [
    (_FRAME_ADD_PLUS, "OPERATION:ADD", None),
    (_FRAME_ADD_INCREASED, "OPERATION:ADD", None),
    (_FRAME_ADD_ADDED_TO, "OPERATION:ADD", None),
    (_FRAME_SUB_MINUS, "OPERATION:SUBTRACT", None),
    (_FRAME_SUB_DECREASED, "OPERATION:SUBTRACT", None),
    (_FRAME_SUB_REDUCED, "OPERATION:SUBTRACT", None),
    (_FRAME_SUB_LESS_THAN, "OPERATION:SUBTRACT", None),
    (_FRAME_MUL_TIMES, "OPERATION:MULTIPLY", None),
    (_FRAME_MUL_MULTIPLIED, "OPERATION:MULTIPLY", None),
    (_FRAME_DIV_DIVIDED, "OPERATION:DIVIDE", None),
    (_FRAME_MUL_DOUBLED, "OPERATION:MULTIPLY", 2.0),
    (_FRAME_MUL_TRIPLED, "OPERATION:MULTIPLY", 3.0),
]

_COPULA_RE = re.compile(r"^(?P<lhs>.+?)\s+(?:equals|is|gives|produces|yields|becomes)\s+(?P<rhs>.+)$", re.IGNORECASE)


def _parse_expression(text: str, mentions: List[EntityMention], relations: List[SemanticRelation]) -> Optional[str]:
    """Recognizes `text` as either a bare atom (base case) or one recognized
    operation frame applied to a (recursively-parsed) base and an operand
    (recursive case). Returns the result label, or None if nothing in the
    frame lexicon confidently applies -- never guesses."""
    text = text.strip()

    atom = _classify_atom(text)
    if atom is not None:
        _ensure_mention(mentions, atom)
        return atom.surface_form

    for frame_re, op_type, implicit_operand in _OPERATION_FRAMES:
        m = frame_re.match(text)
        if not m:
            continue

        base_label = _parse_expression(m.group("base"), mentions, relations)
        if base_label is None:
            continue  # this frame's base wasn't recognizable -- try the next frame

        if implicit_operand is not None:
            operand_str = str(int(implicit_operand)) if implicit_operand == int(implicit_operand) else str(implicit_operand)
            operand_atom = _Atom(surface_form=operand_str, role=EntityRole.QUANTITY, numeric_value=implicit_operand)
        else:
            operand_atom = _classify_atom(m.group("operand"))
            if operand_atom is None:
                continue  # try the next frame

        return _emit_binary_op(mentions, relations, base_label, op_type, operand_atom)

    return None


def _compose_natural_language(text: str) -> Optional[ComposedStructure]:
    m = _COPULA_RE.match(text)
    if not m:
        return None
    lhs_text, rhs_text = m.group("lhs").strip(), m.group("rhs").strip()
    if not lhs_text or not rhs_text:
        return None

    rhs_atom = _classify_atom(rhs_text)
    if rhs_atom is None:
        return None

    mentions: List[EntityMention] = []
    relations: List[SemanticRelation] = []
    lhs_label = _parse_expression(lhs_text, mentions, relations)
    if lhs_label is None:
        return None

    _emit_equals(mentions, relations, lhs_label, rhs_atom)
    return ComposedStructure(mentions=mentions, relations=relations)


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------

def compose_math_structure(raw_text: str) -> Optional[ComposedStructure]:
    """Tries symbolic parsing first (exact, for text already containing `=`
    and operator symbols), then natural-language frame composition. Returns
    None -- never a guess -- when neither confidently resolves a full
    Quantity/Variable/Operation/Equals structure; callers must fall back to
    their own existing behavior in that case."""
    text = _normalize(raw_text)
    if not text:
        return None
    result = _compose_symbolic(text)
    if result is not None:
        return result
    return _compose_natural_language(text)
