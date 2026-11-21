"""Tests for neural intuition (concept-graph R-GCN + category statistics)."""
import os
import statistics
import warnings

from hsci.mind import Mind
from hsci.mind.logic import IS
from hsci.mind.neural import evaluation as nev
from hsci.mind.neural.graph_net import ConceptGraphNet

warnings.filterwarnings("ignore")
os.environ.setdefault("HSCI_MIND_NEURAL", "off")  # these tests do not exercise the neural parser


def test_network_learns_held_out_facts_better_than_chance():
    aucs = []
    for seed in range(4):
        known, train, test_pos, test_neg = nev.make_world(seed)
        net = ConceptGraphNet(dim=16, seed=seed).fit([(e, IS, c) for e, c in known] + [(e, IS, p) for e, p in train])
        f = lambda ps: [x for x in (net.plausibility((e, IS, p)) for e, p in ps) if x is not None]
        aucs.append(nev.auc(f(test_pos), f(test_neg)))
    assert statistics.mean(aucs) > 0.8


def test_intuition_answers_are_labelled_and_never_verified():
    out = nev.run_mind(0)
    assert out["wrong_verified"] == 0
    said = {k: v for side in ("pos", "neg") for k, v in out[side].items()}
    assert said.get("probably yes", 0) + said.get("probably not", 0) > 0
    right = out["pos"].get("probably yes", 0) + out["neg"].get("probably not", 0)
    wrong = out["pos"].get("probably not", 0) + out["neg"].get("probably yes", 0)
    assert right / max(1, right + wrong) >= 0.8


def test_no_intuition_without_experience():
    m = Mind(encoder="hash")
    m.process("Rex is a dog. Fido is a dog. Fido is loud.", "small")
    it = m.process("Is Rex loud?", "small").items[-1]
    assert it.status in ("unknown", "probable") and "network" not in it.method


def test_proof_beats_intuition():
    m = Mind(encoder="hash")
    lines = [f"D{i} is a dax. D{i} is brave." for i in range(8)] + ["Fep is a dax.", "No dax is a coward."]
    m.process(" ".join(lines), "p", direct=True)
    it = m.process("Is Fep a coward?", "p").items[-1]
    assert it.answer.startswith("No") and it.verified and it.method.startswith("deduction")
