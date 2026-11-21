"""Tests for the HSCI Mind: knowledge-driven reasoning with verified answers."""
import os

import pytest

os.environ.setdefault("HSCI_MIND_NEURAL", "off")  # these tests do not exercise the neural parser

from hsci.mind import Mind
from hsci.mind.logic import IS, Atom, Rule
from hsci.mind.reasoner import Closure, Derivation, proof_tree, saturate, saturate_all
from hsci.mind.verifier import verify_proof
from hsci.mind import evaluation


@pytest.fixture(scope="module")
def mind():
    return Mind(encoder="hash")


def ask(mind, world, text):
    mind.reset(world)
    return mind.process(text, world).items


def last(mind, world, text):
    return ask(mind, world, text)[-1]


# ---------------------------------------------------------------- reasoning core

def test_forward_chaining_records_verifiable_proofs():
    rules = [Rule((Atom(IS, ("?x", "man")),), Atom(IS, ("?x", "mortal")))]
    c = saturate(Closure(), rules, [Derivation(Atom(IS, ("socrates", "man")), None, (), "told", 0)])
    goal = Atom(IS, ("socrates", "mortal"))
    assert goal in c
    assert verify_proof(proof_tree(c, goal)).verified


def test_verifier_rejects_a_forged_step():
    rule = Rule((Atom(IS, ("?x", "man")),), Atom(IS, ("?x", "mortal")))
    forged = {"atom": Atom(IS, ("plato", "mortal")), "rule": rule, "source": "", "depth": 1,
              "premises": [{"atom": Atom(IS, ("socrates", "man")), "rule": None, "source": "told", "premises": []}]}
    assert not verify_proof(forged).verified


def test_defaults_are_blocked_by_exceptions():
    fly = Atom(IS, ("?x", "can fly"))
    rules = [Rule((Atom(IS, ("?x", "bird")),), fly, origin="default")]
    given = [Derivation(Atom(IS, (e, "bird")), None, (), "", 0) for e in ("tweety", "pingu")]
    given.append(Derivation(Atom(IS, ("pingu", "can fly"), True), None, (), "", 0))
    c = saturate_all(rules, given)
    assert Atom(IS, ("tweety", "can fly")) in c
    assert Atom(IS, ("pingu", "can fly")) not in c
    assert not c.contradictions()


# ---------------------------------------------------------------- end to end

def test_syllogism_is_proven_and_verified(mind):
    it = last(mind, "t1", "Socrates is a man. All men are mortal. Is Socrates mortal?")
    assert it.status == "answered" and it.answer.startswith("Yes") and it.verified
    assert any("All men are mortal" in line for line in it.explanation)


def test_generic_question_uses_hypothetical_reasoning(mind):
    it = last(mind, "t2", "A dog is a mammal. A mammal is an animal. Is a dog an animal?")
    assert it.answer.startswith("Yes") and it.verified


def test_strong_negation_answers_no(mind):
    it = last(mind, "t3", "Every wug is a blicket. No blicket is a dax. Zorp is a wug. Is Zorp a dax?")
    assert it.answer.startswith("No") and it.verified


def test_open_world_says_i_dont_know(mind):
    it = last(mind, "t4", "Alice likes Bob. Does Alice like Carol?")
    assert it.status == "unknown"


def test_unknown_concept_is_refused_not_hallucinated(mind):
    it = last(mind, "t5", "What is a quasar?")
    assert it.status == "unknown" and not it.verified


def test_comparatives_superlatives_and_opposites(mind):
    items = ask(mind, "t6", "Alice is older than Bob. Bob is older than Carol. Who is the youngest? "
                            "Who is the oldest? Is Carol older than Alice?")
    assert "Carol" in items[2].answer and items[2].verified
    assert "Alice" in items[3].answer
    assert items[4].answer.startswith("No")


def test_contradictions_are_rejected_and_not_stored(mind):
    items = ask(mind, "t7", "Sam is tall. Sam is not tall. Is Sam tall?")
    assert items[1].status == "contradiction"
    assert items[2].answer.startswith("Yes")


def test_default_with_exception(mind):
    items = ask(mind, "t8", "Birds can fly. Tweety is a bird. Pingu is a bird. Pingu cannot fly. "
                            "Can Tweety fly? Can Pingu fly?")
    assert items[3].status == "learned" and "exception" in items[3].answer
    assert items[4].answer.startswith("Yes (by default)")
    assert items[5].answer.startswith("No")


def test_conditional_rules_with_variables(mind):
    it = last(mind, "t9", "If X is a parent of Y and Y is a parent of Z then X is a grandparent of Z. "
                          "Ann is a parent of Bob. Bob is a parent of Cid. Who is a grandparent of Cid?")
    assert it.answer.startswith("Ann") and it.verified


def test_relative_clause_and_counting(mind):
    items = ask(mind, "t10", "People who are rich are happy. Bob is rich. Ann is rich. How many people are happy?")
    assert items[-1].answer.startswith("2")


def test_quantity_chaining_with_units(mind):
    it = last(mind, "t11", "If mass is 10 kg and velocity is 3 m/s, what is the kinetic energy?")
    assert it.status == "answered" and "45" in it.answer and "kg" in it.answer and it.verified


def test_taught_formula_in_new_world(mind):
    it = last(mind, "t12", "The zib equals the mork times the plon. The mork is 6. The plon is 7. What is the zib?")
    assert "42" in it.answer and it.verified


def test_algebra_and_arithmetic(mind):
    items = ask(mind, "t13", "solve x^2 - 5x + 6 = 0. What is the square root of 16?")
    assert "2" in items[0].answer and "3" in items[0].answer and items[0].verified
    assert items[1].answer == "4"


def test_induction_is_labelled_unproven_and_refutable(mind):
    items = ask(mind, "t14", "Rex is a dog. Fido is a dog. Rex is loyal. Fido is loyal. Max is a dog. Is Max loyal?")
    assert items[-1].status == "probable" and not items[-1].verified
    items = mind.process("Bo is a dog. Bo is not loyal. Is Max loyal?", "t14").items
    assert any("refutes" in i.answer for i in items)
    assert items[-1].status == "unknown"


def test_typo_tolerant_grounding(mind):
    it = last(mind, "t15", "A mammal is an animal. Is a mamal an animal?")
    assert it.answer.startswith("Yes") and any("mammal" in n for n in it.notes)


def test_forget_retracts_dependent_conclusions(mind):
    mind.reset("t16")
    r = mind.process("Socrates is a man. All men are mortal.", "t16")
    sid = r.items[1].statement_id
    assert mind.forget(sid, "t16")
    assert mind.process("Is Socrates mortal?", "t16").items[-1].status == "unknown"


def test_worlds_are_isolated(mind):
    ask(mind, "t17a", "Zed is a pilot.")
    mind.reset("t17b")
    assert mind.process("Is Zed a pilot?", "t17b").items[-1].status == "unknown"


def test_persistence_across_restarts(tmp_path):
    db = str(tmp_path / "mind.db")
    m1 = Mind(db_path=db, encoder="hash")
    m1.process("Every glorp is a snib. Quill is a glorp.", "p")
    m1.kb.close()
    m2 = Mind(db_path=db, encoder="hash")
    assert m2.process("Is Quill a snib?", "p").items[-1].answer.startswith("Yes")


# ---------------------------------------------------------------- no hard-coding

@pytest.mark.parametrize("suite", list(evaluation.SUITES))
def test_generated_nonce_word_suites(mind, suite):
    """Invented vocabulary + randomised structure: only real parsing + reasoning can pass."""
    results, summary = evaluation.run(n=12, seed=11, suites=[suite], mind=mind)
    failures = [(r.problem.context, r.problem.question, r.answer) for r in results if not r.correct]
    assert summary["overall_accuracy"] >= 0.95, failures
    assert all(r.verified for r in results if r.status == "answered" and r.problem.suite != "default"), failures


# ---------------------------------------------------------------- API

def test_api_round_trip(monkeypatch, tmp_path):
    # Route functions are called directly (no starlette TestClient: it pulls in httpx2, see commit 3e1281e).
    from fastapi import HTTPException
    from pydantic import ValidationError
    import hsci.mind.api as api
    monkeypatch.setattr(api, "_mind", Mind(db_path=str(tmp_path / "api.db"), encoder="hash"))

    out = api.chat(api.ChatRequest(text="Rex is a dog. Dogs are mammals. Is Rex a mammal?", world="api"))
    assert out["items"][-1]["answer"].startswith("Yes")
    snap = api.snapshot("api")
    assert snap["stats"]["facts"] >= 1 and snap["rules"]

    with pytest.raises(HTTPException) as e:
        api.chat(api.ChatRequest(text="x", world="__common__"))
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        api.chat(api.ChatRequest(text="hi", world="../etc"))
    assert e.value.status_code == 422
    with pytest.raises(ValidationError):
        api.ChatRequest(text="   ", world="api")
    with pytest.raises(HTTPException) as e:
        api.forget("api", 999999)
    assert e.value.status_code == 404
    taught = api.teach(api.TeachRequest(surface="Fep has Lo as a friend.", canonical="Fep is a friend of Lo.", world="api"))
    assert taught["learned"] and "friend of" in taught["means"]
    with pytest.raises(HTTPException) as e:
        api.teach(api.TeachRequest(surface="glorp", canonical="the of and", world="api"))
    assert e.value.status_code == 422
    assert "experiences" in api.understanding()
    assert api.reset("api")["status"] == "reset"
    paths = {getattr(r, "path", None) for r in api.router.routes} | {getattr(r, "path", None) for r in api.create_app().routes}
    assert {"/v2/chat", "/v2/worlds/{world}", "/mind"} <= paths
