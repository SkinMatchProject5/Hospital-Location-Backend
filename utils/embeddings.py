from __future__ import annotations

import hashlib
from typing import Iterable, List, Optional


def _hash_to_vec(text: str, dim: int = 256) -> List[float]:
    """Deterministic pseudo-embedding using hashing for offline fallback."""
    vec = [0.0] * dim
    if not text:
        return vec
    # simple 3-gram hash accumulation
    t = text.strip().lower()
    for i in range(len(t) - 2):
        ngram = t[i : i + 3]
        h = int(hashlib.sha256(ngram.encode("utf-8")).hexdigest(), 16)
        vec[h % dim] += 1.0
    # l2 normalize
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def embed_text(text: str, model: Optional[str] = None, api_key: Optional[str] = None) -> List[float]:
    """Embed text using provider if available, else fallback to hash vec.

    Parameters are accepted for interface compatibility but unused in fallback.
    """
    # TODO: Optionally integrate OpenAI embeddings when api_key provided.
    return _hash_to_vec(text)

