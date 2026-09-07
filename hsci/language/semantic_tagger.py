"""
Trainable semantic tagger: the real NLP replacement for the regex/keyword
"understanding" layer.

Architecture (small, trained entirely from scratch -- no pretrained word
embeddings, no external API, no LLM):
    per-token features (learned lemma embedding + learned POS embedding +
    learned dependency-relation embedding + hand-crafted shape features)
        -> BiLSTM
        -> per-token BIO tagging head   (entity role: KNOWN vs UNKNOWN span)
        -> sentence-level intent head   (REDUCTION/COMPOSITION/SYNTHESIS/TRANSFORMATION)
        -> sentence-level relation head (ADD/SUBTRACT/.../POSSESSION/ACQUIRE/...)

spaCy (en_core_web_sm) supplies tokenization, POS tags, lemmas, and
dependency labels -- a small, local, non-generative statistical pipeline,
not a language model. It is a feature source, not a decision-maker.

Training signal starts from the synthetic bootstrap corpus
(hsci/language/synthetic_corpus.py) and is designed to keep learning from
real usage afterwards: update_from_feedback() runs one more real gradient
step whenever the downstream Z3/SymPy verification confirms or refutes a
parse, exactly like the proof-guided loop already used for
NativeNeuralClassifier (hsci/neural/native_neural_classifier.py).
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn

logger = logging.getLogger("HSCI.Language.SemanticTagger")

TOKEN_ROLES = ["O", "B-KNOWN", "I-KNOWN", "B-UNKNOWN", "I-UNKNOWN"]
INTENTS = ["REDUCTION", "COMPOSITION", "SYNTHESIS", "TRANSFORMATION"]
RELATIONS = [
    "NONE", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "EQUALS",
    "POSSESSION", "ACQUIRE", "GREATER_THAN", "LESS_THAN",
]

_UNIVERSAL_POS = [
    "ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ", "NOUN", "NUM",
    "PART", "PRON", "PROPN", "PUNCT", "SCONJ", "SYM", "VERB", "X", "SPACE", "<UNK>",
]

WEIGHTS_DIR = Path("weights")
DEFAULT_FILENAME = "semantic_tagger.pt"


class Vocab:
    """Simple string->id table with an <UNK> fallback, built from the training corpus."""

    def __init__(self, tokens: Optional[List[str]] = None):
        self.token_to_id: Dict[str, int] = {"<PAD>": 0, "<UNK>": 1}
        if tokens:
            for t in tokens:
                self.add(t)

    def add(self, token: str) -> int:
        if token not in self.token_to_id:
            self.token_to_id[token] = len(self.token_to_id)
        return self.token_to_id[token]

    def get(self, token: str) -> int:
        return self.token_to_id.get(token, 1)

    def __len__(self) -> int:
        return len(self.token_to_id)


class SpacyFeaturizer:
    """Wraps spaCy purely as a local feature source: tokens, POS, lemma, dep label."""

    def __init__(self, model: str = "en_core_web_sm"):
        import spacy

        try:
            self.nlp = spacy.load(model)
        except OSError as exc:
            raise RuntimeError(
                f"spaCy model '{model}' not found. Run: python -m spacy download {model}"
            ) from exc
        self.pos_vocab = Vocab(_UNIVERSAL_POS)
        self.dep_vocab = Vocab()

    def parse(self, text: str):
        return self.nlp(text)

    def shape_features(self, tok, index: int, length: int) -> List[float]:
        return [
            1.0 if tok.like_num or tok.is_digit else 0.0,
            1.0 if tok.is_alpha else 0.0,
            1.0 if tok.is_title else 0.0,
            1.0 if tok.is_stop else 0.0,
            1.0 if tok.is_punct else 0.0,
            index / max(1, length - 1),
        ]


SHAPE_DIM = 6


class SemanticTagger(nn.Module):
    """
    Small BiLSTM tagger: entity-role BIO tags + sentence intent + sentence relation.
    Every parameter is trained from scratch on this project's own data -- no
    pretrained weights are loaded from anywhere.
    """

    def __init__(
        self,
        lemma_vocab_size: int,
        pos_vocab_size: int,
        dep_vocab_size: int,
        lemma_dim: int = 32,
        pos_dim: int = 8,
        dep_dim: int = 8,
        hidden_dim: int = 64,
    ):
        super().__init__()
        self.lemma_emb = nn.Embedding(lemma_vocab_size, lemma_dim, padding_idx=0)
        self.pos_emb = nn.Embedding(pos_vocab_size, pos_dim, padding_idx=0)
        self.dep_emb = nn.Embedding(dep_vocab_size, dep_dim, padding_idx=0)

        input_dim = lemma_dim + pos_dim + dep_dim + SHAPE_DIM
        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers=1, batch_first=True, bidirectional=True
        )
        self.dropout = nn.Dropout(0.2)

        lstm_out_dim = hidden_dim * 2
        self.tag_head = nn.Linear(lstm_out_dim, len(TOKEN_ROLES))
        self.intent_head = nn.Linear(lstm_out_dim, len(INTENTS))
        self.relation_head = nn.Linear(lstm_out_dim, len(RELATIONS))

        self._init_weights()

    def _init_weights(self):
        for name, param in self.named_parameters():
            if param.dim() > 1:
                nn.init.xavier_uniform_(param)

    def forward(
        self, lemma_ids: torch.Tensor, pos_ids: torch.Tensor, dep_ids: torch.Tensor, shapes: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Shapes (batch=1 assumed for simplicity; this model is small enough that
        per-example training/inference is fast without batching complexity):
            lemma_ids, pos_ids, dep_ids: (seq_len,)
            shapes: (seq_len, SHAPE_DIM)
        Returns:
            tag_logits: (seq_len, num_roles)
            intent_logits: (num_intents,)
            relation_logits: (num_relations,)
        """
        x = torch.cat(
            [self.lemma_emb(lemma_ids), self.pos_emb(pos_ids), self.dep_emb(dep_ids), shapes],
            dim=-1,
        ).unsqueeze(0)  # (1, seq_len, input_dim)

        out, _ = self.lstm(x)
        out = self.dropout(out).squeeze(0)  # (seq_len, lstm_out_dim)

        tag_logits = self.tag_head(out)
        pooled = out.mean(dim=0)
        intent_logits = self.intent_head(pooled)
        relation_logits = self.relation_head(pooled)
        return tag_logits, intent_logits, relation_logits


class TrainableSemanticParser:
    """
    Ties SpacyFeaturizer + SemanticTagger + vocabularies into one object with
    a parse()/compile() surface that matches the existing rule-based parsers,
    so it can be dropped into LanguageBridge without changing anything downstream.
    """

    def __init__(self):
        self.featurizer = SpacyFeaturizer()
        self.lemma_vocab = Vocab()
        self.model: Optional[SemanticTagger] = None
        self.is_trained = False

    # ---- feature extraction -------------------------------------------------

    def _featurize(self, text: str, build_vocab: bool = False):
        doc = self.featurizer.parse(text)
        lemma_ids, pos_ids, dep_ids, shapes = [], [], [], []
        for i, tok in enumerate(doc):
            lemma = tok.lemma_.lower()
            if build_vocab:
                self.lemma_vocab.add(lemma)
                self.featurizer.dep_vocab.add(tok.dep_)
            lemma_ids.append(self.lemma_vocab.get(lemma))
            pos_ids.append(self.featurizer.pos_vocab.get(tok.pos_))
            dep_ids.append(self.featurizer.dep_vocab.get(tok.dep_))
            shapes.append(self.featurizer.shape_features(tok, i, len(doc)))
        return doc, (
            torch.tensor(lemma_ids, dtype=torch.long),
            torch.tensor(pos_ids, dtype=torch.long),
            torch.tensor(dep_ids, dtype=torch.long),
            torch.tensor(shapes, dtype=torch.float),
        )

    @staticmethod
    def labels_from_spans(doc, spans: List[Tuple[int, int, str]]) -> List[str]:
        labels = ["O"] * len(doc)
        for start, end, role in spans:
            first = True
            for i, tok in enumerate(doc):
                if tok.idx < end and (tok.idx + len(tok.text)) > start:
                    labels[i] = f"B-{role}" if first else f"I-{role}"
                    first = False
        return labels

    # ---- training ------------------------------------------------------------

    def build_vocab_and_model(self, texts: List[str]) -> None:
        for text in texts:
            self._featurize(text, build_vocab=True)
        self.model = SemanticTagger(
            lemma_vocab_size=len(self.lemma_vocab),
            pos_vocab_size=len(self.featurizer.pos_vocab),
            dep_vocab_size=len(self.featurizer.dep_vocab),
        )

    def train_step(self, example, optimizer) -> float:
        assert self.model is not None
        doc, (lemma_ids, pos_ids, dep_ids, shapes) = self._featurize(example.text)
        gold_labels = self.labels_from_spans(doc, example.entity_spans)
        gold_tag_ids = torch.tensor([TOKEN_ROLES.index(l) for l in gold_labels], dtype=torch.long)
        gold_intent_id = torch.tensor(INTENTS.index(example.intent), dtype=torch.long)
        gold_relation_id = torch.tensor(RELATIONS.index(example.relation), dtype=torch.long)

        tag_logits, intent_logits, relation_logits = self.model(lemma_ids, pos_ids, dep_ids, shapes)

        tag_loss = nn.functional.cross_entropy(tag_logits, gold_tag_ids)
        intent_loss = nn.functional.cross_entropy(intent_logits.unsqueeze(0), gold_intent_id.unsqueeze(0))
        relation_loss = nn.functional.cross_entropy(relation_logits.unsqueeze(0), gold_relation_id.unsqueeze(0))
        loss = tag_loss + intent_loss + relation_loss

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        return loss.item()

    # ---- inference -------------------------------------------------------

    def parse(self, text: str) -> Dict[str, Any]:
        """Returns a plain dict shaped like SemanticIR's fields; bridge.py adapts it."""
        assert self.model is not None, "Model not trained/loaded"
        self.model.eval()
        doc, (lemma_ids, pos_ids, dep_ids, shapes) = self._featurize(text)
        with torch.no_grad():
            tag_logits, intent_logits, relation_logits = self.model(lemma_ids, pos_ids, dep_ids, shapes)
            tag_ids = tag_logits.argmax(dim=-1).tolist()
            intent_id = intent_logits.argmax(dim=-1).item()
            relation_id = relation_logits.argmax(dim=-1).item()
            intent_conf = torch.softmax(intent_logits, dim=-1).max().item()

        entities: Dict[str, Any] = {}
        known_vals, unknown_name = [], None
        current_span: List[str] = []
        current_role: Optional[str] = None

        def flush():
            nonlocal current_span, current_role, unknown_name
            if not current_span:
                return
            span_text = "".join(current_span)
            if current_role == "KNOWN":
                try:
                    val: Any = float(span_text) if "." in span_text else int(span_text)
                except ValueError:
                    val = span_text
                known_vals.append(val)
            elif current_role == "UNKNOWN":
                unknown_name = span_text.strip().replace(" ", "_") or "result"
            current_span, current_role = [], None

        for i, tok in enumerate(doc):
            label = TOKEN_ROLES[tag_ids[i]]
            role = label.split("-")[-1] if label != "O" else None
            if label.startswith("B-"):
                flush()
                current_role = role
                current_span = [tok.text]
            elif label.startswith("I-") and role == current_role:
                current_span.append((" " if tok.whitespace_ == "" else " ") + tok.text)
            else:
                flush()
        flush()

        for idx, val in enumerate(known_vals):
            entities[f"op_{idx + 1}"] = val
        entities[unknown_name or "result"] = None

        return {
            "entities": entities,
            "intent": INTENTS[intent_id],
            "relation": RELATIONS[relation_id],
            "domain": "arithmetic" if INTENTS[intent_id] == "REDUCTION" else "general",
            "confidence": intent_conf,
            "raw_text": text,
            "parse_method": "trainable_semantic_tagger",
        }

    def compile(self, text: str):
        """Same result as parse(), packaged as a SemanticIR so it drops into
        LanguageBridge exactly like SemanticCompiler.compile() does."""
        from hsci.core.data_types import SemanticIR, RelationTriple

        result = self.parse(text)
        entities = result["entities"]
        known_keys = [k for k in entities if k.startswith("op_")]
        unknown_keys = [k for k in entities if not k.startswith("op_")]
        target_goal = unknown_keys[0] if unknown_keys else "result"

        relations: List[RelationTriple] = []
        if result["relation"] != "NONE" and len(known_keys) >= 2:
            relations.append(RelationTriple(subject=known_keys[0], relation=result["relation"], object=known_keys[1]))

        return SemanticIR(
            raw_text=text,
            entities=entities,
            relations=relations,
            ast_constraints=[],
            target_goal=target_goal,
            domain=result["domain"],
            intent=result["intent"],
            confidence=result["confidence"],
        )

    # ---- persistence ------------------------------------------------------

    def save(self, filename: Optional[str] = None) -> Path:
        WEIGHTS_DIR.mkdir(exist_ok=True)
        path = WEIGHTS_DIR / (filename or DEFAULT_FILENAME)
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "lemma_vocab": self.lemma_vocab.token_to_id,
                "pos_vocab": self.featurizer.pos_vocab.token_to_id,
                "dep_vocab": self.featurizer.dep_vocab.token_to_id,
            },
            path,
        )
        logger.info(f"Saved semantic tagger -> {path}")
        return path

    def load(self, filename: Optional[str] = None) -> bool:
        path = WEIGHTS_DIR / (filename or DEFAULT_FILENAME)
        if not path.exists():
            return False
        checkpoint = torch.load(path, weights_only=True)
        self.lemma_vocab.token_to_id = checkpoint["lemma_vocab"]
        self.featurizer.pos_vocab.token_to_id = checkpoint["pos_vocab"]
        self.featurizer.dep_vocab.token_to_id = checkpoint["dep_vocab"]
        self.model = SemanticTagger(
            lemma_vocab_size=len(self.lemma_vocab.token_to_id),
            pos_vocab_size=len(self.featurizer.pos_vocab.token_to_id),
            dep_vocab_size=len(self.featurizer.dep_vocab.token_to_id),
        )
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
        self.is_trained = True
        return True

    # ---- proof-guided continued learning (hook for step 2) ----------------

    def update_from_feedback(self, text: str, gold_intent: str, gold_relation: str,
                              entity_spans: List[Tuple[int, int, str]], optimizer) -> float:
        """
        One additional real gradient step from a verified live interaction.
        Intended to be called by LearningEngine after Z3/SymPy confirms (or
        refutes -- pass the corrected labels) the parse that was actually used,
        exactly like ProofGuidedWeightUpdater does for NativeNeuralClassifier.
        """
        from hsci.language.synthetic_corpus import LabeledExample

        example = LabeledExample(text=text, entity_spans=entity_spans, intent=gold_intent, relation=gold_relation)
        return self.train_step(example, optimizer)
