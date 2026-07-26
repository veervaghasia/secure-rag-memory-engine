"""
retrieval/orchestrator.py

Coordinates hybrid retrieval (Vector + BM25), context assembly, 
and LiteLLM generation for Phase 1.

TODO:
- Add conversation memory management for multi-turn interactions.
"""

from opik import track, opik_context
from opik.opik_context import get_current_span_data
from config import config

from typing import Any, Dict, List, Optional
import litellm
from litellm import completion
from litellm.integrations.opik.opik import OpikLogger

from config import config
from ingestion.structures import ProcessedChunk
from retrieval.bm25_engine import BM25Engine
from retrieval.search_fusion import fuse_results 
from retrieval.vector_store import ChromaVectorEngine

opik_logger = OpikLogger()
litellm.callbacks = [opik_logger]

def format_chunk_for_context(chunk: ProcessedChunk) -> str:
    """
    Formats a single ProcessedChunk into a human-readable, token-efficient context string
    for the LLM prompt. Omits technical primary keys (eg, chunk_id, content_hash).
    """
    return (
        f"--- SOURCE: [{chunk.notebook_name} > {chunk.section_name} > {chunk.parent_page_title}] ---\n"
        f"{chunk.text_content}"
    )

@track(project_name="secure-rag-memory-engine")
def build_prompt_messages(
        user_query: str,
        retrieved_chunks: List[ProcessedChunk],
        system_prompt: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Assembles standard OpenAI/LiteLLM role-based message list.
    """
    if system_prompt is None:
       system_prompt = (
            "You are a secure, accurate AI research assistant answering questions based on the user's notes. "
            "Use ONLY the provided context snippets to answer the question. "
            "If the answer cannot be found in the context, explicitly state that you do not have enough information."
        )

    # Format retrieved context
    if retrieved_chunks:
        formatted_snippets = [format_chunk_for_context(chunk) for chunk in retrieved_chunks] 
        context_block = "\n\n".join(formatted_snippets)
    else:
        context_block = "No relevant document context found."

    user_content = f"CONTEXT:\n{context_block}\n\nUSER QUESTION: {user_query}"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

@track(project_name="secure-rag-memory-engine")
def run_rag_pipeline(
        user_query: str,
        vector_engine: ChromaVectorEngine,
        bm25_engine: BM25Engine,
        filter_dict: Optional[Dict[str, Any]] = None,
        top_k: int = config.retrieval.top_k,
        model: str = config.llm.model_name
) -> Dict[str, Any]:
    """
    Executes the Phase 1 User Query Lifecycle:
    1. Query Vector Engine (ChromaDB)
    2. Query BM25 Lexical Engine
    3. Fuse/Deduplicate Results (via search_fusion)
    4. Assemble Context & Prompt Messages
    5. Generate Response via LiteLLM
    6. Return Structured Output (response + citation metadata)
    """ 
    # Attach high-level metadata to the root trace
    if config.telemetry.enable_opik:
        opik_context.update_current_trace(
            metadata={
                "phase": config.telemetry.current_phase,
                "user_query": user_query,
                "top_k": top_k,
                "has_filter": filter_dict is not None
            }
        )

    # 1. Vector Search
    vector_results = vector_engine.search_similar_chunks(
        query_text=user_query,
        top_k=top_k,
        filter_dict=filter_dict
    )

    # 2. BM25 Search
    bm25_results = bm25_engine.search_similar_chunks(
        query_text=user_query,
        top_k=top_k,
        filter_dict=filter_dict
    )

    # 3. Fuse and Deduplicate Results
    fused_chunks: List[ProcessedChunk] = fuse_results(
        vector_results=vector_results,
        bm25_results=bm25_results,
        top_k=top_k
    )

    # 4. Construct Prompt Payload
    messages = build_prompt_messages(
        user_query=user_query,
        retrieved_chunks=fused_chunks
    )

    # 5. Invoke LLM Generation via LiteLLM
    llm_response = completion(
        model=model,
        messages=messages,
        temperature=config.llm.temperature,  # Deterministic factual extraction
        metadata={
            "opik": {
                "current_span_data": get_current_span_data()  # <--- THIS LINKS IT TO THE PARENT SPAN
            }
        }
    )

    assistant_reply = llm_response.choices[0].message.content

    # 6. Format Structured Citation Metadata
    sources = [
        {
            "chunk_id": chunk.chunk_id,
            "notebook_name": chunk.notebook_name,
            "section_name": chunk.section_name,
            "parent_page_title": chunk.parent_page_title,
            "snippet": chunk.text_content[:150] + "..." if len(chunk.text_content) > 150 else chunk.text_content
        }
        for chunk in fused_chunks
    ]

    return {
        "role": "assistant",
        "content": assistant_reply,
        "sources": sources,
        "fused_chunks_count": len(fused_chunks)
    }