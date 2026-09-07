"""
Trains the SemanticTagger (hsci/language/semantic_tagger.py) on the synthetic
bootstrap corpus (hsci/language/synthetic_corpus.py).

No external dataset, no pretrained weights, no API calls: every training
example is generated from templates and labeled exactly because the text
was constructed from known spans. This is the one-time bootstrap; further
learning happens online via update_from_feedback() once wired into the
live proof-guided loop.

Usage:
    .venv\\Scripts\\python.exe train_semantic_parser.py
"""
import random
import sys
import time

import torch

from hsci.language.semantic_tagger import TrainableSemanticParser, TOKEN_ROLES, INTENTS, RELATIONS
from hsci.language.synthetic_corpus import generate_corpus


def main() -> int:
    print("=" * 60)
    print("Training SemanticTagger (real backprop, in-house, no LLM)")
    print("=" * 60)

    corpus = generate_corpus(size=2000, seed=42)
    random.Random(7).shuffle(corpus)
    split = int(len(corpus) * 0.9)
    train_set, eval_set = corpus[:split], corpus[split:]
    print(f"Corpus: {len(corpus)} examples ({len(train_set)} train / {len(eval_set)} eval)")

    parser = TrainableSemanticParser()
    parser.build_vocab_and_model([ex.text for ex in train_set])
    print(f"Vocab: {len(parser.lemma_vocab)} lemmas, "
          f"{len(parser.featurizer.pos_vocab)} POS tags, "
          f"{len(parser.featurizer.dep_vocab)} dep labels")

    optimizer = torch.optim.Adam(parser.model.parameters(), lr=1e-3, weight_decay=1e-5)

    epochs = 8
    start = time.time()
    for epoch in range(1, epochs + 1):
        random.Random(epoch).shuffle(train_set)
        total_loss = 0.0
        for example in train_set:
            total_loss += parser.train_step(example, optimizer)
        avg_loss = total_loss / len(train_set)
        print(f"Epoch {epoch}/{epochs}  avg_loss={avg_loss:.4f}")
    print(f"Training took {time.time() - start:.1f}s")

    # ---- evaluation on held-out synthetic examples ----
    parser.model.eval()
    tag_correct = tag_total = 0
    intent_correct = relation_correct = 0
    with torch.no_grad():
        for example in eval_set:
            doc, (lemma_ids, pos_ids, dep_ids, shapes) = parser._featurize(example.text)
            gold_tags = parser.labels_from_spans(doc, example.entity_spans)
            tag_logits, intent_logits, relation_logits = parser.model(lemma_ids, pos_ids, dep_ids, shapes)
            pred_tags = [TOKEN_ROLES[i] for i in tag_logits.argmax(dim=-1).tolist()]
            tag_correct += sum(p == g for p, g in zip(pred_tags, gold_tags))
            tag_total += len(gold_tags)
            if INTENTS[intent_logits.argmax(dim=-1).item()] == example.intent:
                intent_correct += 1
            if RELATIONS[relation_logits.argmax(dim=-1).item()] == example.relation:
                relation_correct += 1

    print("-" * 60)
    print(f"Held-out token-tag accuracy: {tag_correct / max(1, tag_total):.3%}")
    print(f"Held-out intent accuracy:    {intent_correct / len(eval_set):.3%}")
    print(f"Held-out relation accuracy:  {relation_correct / len(eval_set):.3%}")

    path = parser.save()
    print(f"Saved weights -> {path}")

    # ---- sanity check on paraphrases NOT in the template set at all ----
    print("-" * 60)
    print("Sanity check on free-form paraphrases (not from templates):")
    parser.model.eval()
    for text in [
        "What is 2 + 2?",
        "can you tell me what 15 minus 4 equals",
        "hey, what's up",
        "please write a script that sorts an array",
    ]:
        result = parser.parse(text)
        print(f"  '{text}' -> intent={result['intent']} relation={result['relation']} "
              f"entities={result['entities']} confidence={result['confidence']:.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
