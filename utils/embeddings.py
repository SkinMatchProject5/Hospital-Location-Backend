from __future__ import annotations

import hashlib
import os
import openai
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
    """Embed text using OpenAI API if available, else fallback to hash vec."""
    
    # OpenAI API 키 확인
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    if not api_key or api_key == "your_openai_api_key_here":
        print("Warning: OpenAI API key not found, using hash fallback")
        return _hash_to_vec(text)
    
    try:
        # OpenAI 클라이언트 설정
        client = openai.OpenAI(api_key=api_key)
        
        # 임베딩 생성
        response = client.embeddings.create(
            input=text,
            model=model
        )
        
        return response.data[0].embedding
        
    except Exception as e:
        print(f"OpenAI embedding failed: {e}, using hash fallback")
        return _hash_to_vec(text)

