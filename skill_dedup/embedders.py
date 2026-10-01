"""Embedders for phase 2. All return unit-normalized float32 vectors."""

from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

from .skill import Skill

# The description decides when a skill triggers, so it dominates the similarity.
DESC_WEIGHT, BODY_WEIGHT = 0.7, 0.3
BODY_CHARS = 2000


class Embedder(Protocol):
    name: str
    dim: int

    def encode(self, texts: list[str]) -> np.ndarray: ...


def embed_skills(embedder: Embedder, skills: list[Skill]) -> np.ndarray:
    """One batched call for all skills: (name + description) and body, blended."""
    if not skills:
        return np.zeros((0, embedder.dim), dtype=np.float32)
    heads = [f"{s.name}: {s.description}" for s in skills]
    bodies = [s.body[:BODY_CHARS] or s.description for s in skills]
    enc = embedder.encode(heads + bodies)
    head_v, body_v = enc[: len(skills)], enc[len(skills):]
    v = DESC_WEIGHT * head_v + BODY_WEIGHT * body_v
    return _normalize(v)


def _normalize(v: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    return (v / np.where(norms == 0, 1, norms)).astype(np.float32)


class SentenceTransformerEmbedder:
    """Local, free, CPU-friendly. `pip install sentence-transformers`."""

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:  # pragma: no cover - depends on optional install
            raise SystemExit(
                "sentence-transformers is not installed: "
                "pip install sentence-transformers  (or use --embedder hashing)"
            ) from e
        self._model = SentenceTransformer(model)
        self.name = f"st:{model}"
        get_dim = getattr(self._model, "get_embedding_dimension", None) or \
            self._model.get_sentence_embedding_dimension
        self.dim = get_dim()

    def encode(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(texts, normalize_embeddings=True, batch_size=64).astype(np.float32)


class HashingEmbedder:
    """Zero-dependency lexical fallback (hashed bag of words + bigrams).

    Not semantic: it catches reworded copies, not paraphrases. Use it for tests,
    CI without model downloads, or as a stopgap until a real model is available.
    """

    def __init__(self, dim: int = 1024):
        self.name = f"hashing:{dim}"
        self.dim = dim

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            words = re.findall(r"[a-z0-9]+", text.lower())
            for tok in words + [f"{a} {b}" for a, b in zip(words, words[1:])]:
                h = int.from_bytes(hashlib.md5(tok.encode()).digest()[:4], "little")
                out[row, h % self.dim] += 1.0 if h & 1 << 31 else -1.0
        return _normalize(out)


def make_embedder(spec: str) -> Embedder:
    """'hashing', 'st' (default model) or 'st:<model-name>'."""
    if spec == "hashing":
        return HashingEmbedder()
    if spec == "st":
        return SentenceTransformerEmbedder()
    if spec.startswith("st:"):
        return SentenceTransformerEmbedder(spec[3:])
    raise ValueError(f"unknown embedder {spec!r}")
