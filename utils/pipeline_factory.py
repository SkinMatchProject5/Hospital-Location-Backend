"""Pipeline initialization helpers using keys from config.py.

This wires Qdrant and an LLM (LangChain ChatOpenAI) into HospitalRAGPipeline.

Usage:
    from utils.pipeline_factory import create_pipeline_from_config
    pipeline = create_pipeline_from_config()
    result = pipeline.search_from_ft_xml(xml_str)
"""

from __future__ import annotations

from typing import Optional

from qdrant_client import QdrantClient

from pipeline.rag_pipeline import HospitalRAGPipeline


def _init_llm_from_config() -> Optional[object]:
    try:
        from config import OPENAI_API_KEY  # type: ignore
    except Exception:
        return None

    if not OPENAI_API_KEY:
        return None

    try:
        # Lazy import to avoid hard dependency during tests
        from langchain_openai import ChatOpenAI  # type: ignore

        # Default lightweight model; adjust as needed
        return ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini", temperature=0)
    except Exception:
        # LangChain or provider not available; proceed without LLM
        return None


def create_pipeline_from_config(rerank_model_type: str = "llm") -> HospitalRAGPipeline:
    """
    Create HospitalRAGPipeline with specified reranking model
    
    Args:
        rerank_model_type: "llm", "ce" (cross-encoder), or "off"
    """
    try:
        from config import (
            QDRANT_URL,  # type: ignore
            QDRANT_API_KEY,  # type: ignore
        )
    except ImportError:
        # Fallback to environment variables
        import os
        QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    
    # Collection name - BACKEND_PLAN.md uses derm_children
    CHILDREN_COLLECTION = "derm_children"

    # Qdrant client
    if QDRANT_API_KEY:
        qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    else:
        qdrant = QdrantClient(url=QDRANT_URL)

    # Create pipeline with specified reranker type
    pipeline = HospitalRAGPipeline(
        qdrant_client=qdrant, 
        collection_name=CHILDREN_COLLECTION,
        rerank_model_type=rerank_model_type
    )

    # Attach LLM for reranker if needed
    if rerank_model_type == "llm":
        llm = _init_llm_from_config()
        if llm is not None:
            pipeline.reranker.llm = llm

    return pipeline

