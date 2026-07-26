"""
tests/test_rag_pipeline.py

Integration test harness verifying the end-to-end Phase 1 RAG pipeline:
RawOnenotePage -> Chunker -> Vector & BM25 Upsert -> Orchestrator -> LiteLLM Response
"""

import os
from dotenv import load_dotenv

# Absolute first step: Load environment strings into system memory 
# BEFORE initializing any internal config modules to prevent empty state overrides.
load_dotenv()

from config import config
import opik

from ingestion.base_parser import FixedSizeChunker
from ingestion.structures import RawOnenotePage
from retrieval.bm25_engine import BM25Engine
from retrieval.orchestrator import run_rag_pipeline
from retrieval.vector_store import ChromaVectorEngine

@opik.track(project_name=config.telemetry.project_name)
def test_full_rag_pipeline():
    print("=" * 60)
    print(f"RUNNING INTEGRATION TEST: {config.telemetry.current_phase.upper()}")
    print("=" * 60) 

    # 1. Instantiate Sample Page
    mock_page = RawOnenotePage(
        page_id="dl-course-04a", 
        notebook_name="AI_Studies",
        section_name="Deeplearning_AI",
        page_title="Transformer_Mechanics",
        text_content=(
            "Self-attention allows tokens to dynamically weight their relevance to other tokens. "
            "Formula: Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V. "
            "Multi-head attention projects queries, keys, and values into lower-dimensional subspaces "
            "to jointly attend to information from different representation subspaces."
        ),
        depth=0,
        page_hash="mock_hash_123"
    )

    # 2. Chunk Page
    chunker = FixedSizeChunker(
        chunk_size=config.chunking.chunk_size, 
        chunk_overlap=config.chunking.chunk_overlap
    )
    payload = chunker.chunk_page(mock_page)
    print(f" Generated {payload.total_chunks} chunks from '{mock_page.page_title}'")

    # 3. Initialize Storage Engines
    print(" Initializing ChromaDB and BM25 Storage Engines...")
    vector_engine = ChromaVectorEngine()
    bm25_engine = BM25Engine()

    # 4. Upsert Chunks
    print(" Upserting chunks into Vector Store and BM25 Index...")
    v_count = vector_engine.upsert_chunks(payload.chunks)
    b_count = bm25_engine.upsert_chunks(payload.chunks)

    # 5. Execute Pipeline Query
    test_query = "What is the formula for self-attention?"
    print("\n" + "=" * 60)
    print(f"EXECUTING RAG PIPELINE QUERY: '{test_query}'")
    print("=" * 60)

    result = run_rag_pipeline(
        user_query=test_query,
        vector_engine=vector_engine,
        bm25_engine=bm25_engine
    )

    # Assertions on Output Schema
    assert result["role"] == "assistant"
    assert len(result["content"]) > 0, "Response content should not be empty!"
    assert len(result["sources"]) > 0, "Sources should be populated!"

    print("\n[ASSISTANT RESPONSE]")
    print(result["content"])
    print("\n[CITED SOURCES]")
    for src in result["sources"]:
        print(f" - [{src['notebook_name']} > {src['section_name']} > {src['parent_page_title']}] (ID: {src['chunk_id']})")
    print("=" * 60)
    print(" PIPELINE INTEGRATION TEST PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    try:
        opik.configure(
            api_key=os.getenv("OPIK_API_KEY"),
            workspace=os.getenv("OPIK_WORKSPACE"),
            force=False, # Fast startup using cached config without DNS spam
            automatic_approvals=True
        )
    except Exception as e:
        print(f"⚠️ [Telemetry Warning] Could not connect to Opik cloud: {e}. Continuing without tracing.")
    
    test_full_rag_pipeline()    