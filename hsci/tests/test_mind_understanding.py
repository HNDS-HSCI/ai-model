"""Tests for experience-driven language understanding in the HSCI Mind."""
import pytest

from hsci.mind import Mind
from hsci.mind.understanding import evaluation as uev


@pytest.fixture()
def mind():
    return Mind(encoder="hash")


def say(mind, text, world="u"):
    return mind.process(text, world).items


def test_unknown_phrasing_is_asked_not_guessed(mind):
    it = say(mind, "Fep is known to be brave.")[-1]
    assert it.status == "clarify"
    assert mind.snapshot("u")["stats"]["facts"] == 0          # nothing stored on a guess


def test_rephrasing_teaches_a_phrasing_that_generalises(mind):
    say(mind, "Fep is known to be brave.")
    it = say(mind, "Fep is brave.")[-1]
    assert it.status == "learned" and "from now on" in it.answer
    it = say(mind, "Gub is known to be calm.")[-1]                # new words, same phrasing
    assert it.status == "learned" and any("analogy" in n for n in it.notes)
    assert say(mind, "Is Gub calm?")[-1].answer.startswith("Yes")


def test_no_then_rephrase(mind):
    first = say(mind, "Zib is known to be kind.")[-1]
    assert first.status == "clarify"
    if first.answer.startswith("Do you mean"):
        assert say(mind, "no")[-1].answer.startswith("OK. Could you say")
    assert say(mind, "Zib is kind.")[-1].status == "learned"
    assert say(mind, "Is Zib kind?")[-1].answer.startswith("Yes")


def test_explicit_teach_api(mind):
    mind.teach("Mork has Lind as a friend.", "Mork is a friend of Lind.", "u")
    it = say(mind, "Tobb has Quen as a friend.")[-1]
    assert it.status == "learned" and "friend of" in " ".join(it.logic)


def test_taught_meaning_beats_literal_grammar(mind):
    say(mind, "Rex is a dog.")
    # seeded teaching pair: "Tell me if Rex is a dog." => "Is Rex a dog?"
    assert say(mind, "Tell me if Rex is a dog.")[-1].answer.startswith("Yes")


def test_previous_silent_misreads_are_now_questioned(mind):
    for s in ("Water boils at 100 degrees.", "Alice gave Bob a book yesterday."):
        assert say(mind, s)[-1].status == "clarify", s


def test_maths_is_never_adapted_by_analogy(mind):
    say(mind, "solve 2x + 3 = 11")
    assert "x = -6" in say(mind, "solve 7x + 15 = -27")[-1].answer


def test_quantifiers_are_never_dropped(mind):
    say(mind, "Trog is a pond. Rex is a dog.")
    it = say(mind, "Each klomp is a prand.")[-1]
    assert it.status == "learned" and any("->" in l for l in it.logic)


def test_affirmation_without_a_question(mind):
    assert "nothing" in say(mind, "yes")[-1].answer.lower()


def test_casual_speech_confirmed_once_then_understood(mind):
    it = say(mind, "btw rex is kinda old")[-1]
    assert it.status == "clarify" and "rex is old" in it.answer.lower()   # understood, but checks first
    assert say(mind, "yes")[-1].answer.startswith("Thanks")
    assert say(mind, "Is Rex old?")[-1].answer.startswith("Yes")
    it = say(mind, "btw max is kinda tall")[-1]                      # same style, new words: no question now
    assert it.status == "learned"
    assert say(mind, "Is Max tall?")[-1].answer.startswith("Yes")


def test_learning_curve_one_example_suffices():
    res = uev.run(k=4, seed=1, encoder="hash")
    before = {k: sum(r["before"][k] for r in res.values()) for k in ("correct", "asked", "wrong")}
    after = {k: sum(r["after"][k] for r in res.values()) for k in ("correct", "asked", "wrong")}
    n = sum(before.values())
    assert before["wrong"] == 0 and after["wrong"] == 0
    assert after["correct"] / n >= 0.9
