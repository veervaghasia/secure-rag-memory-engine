"""
retrieval/orchestrator.py

Coordinates hybrid retrieval (Vector + BM25), context assembly, 
and LiteLLM generation for Phase 1.
"""

from typing import Any, Dict, List, Optional
import litellm
from litellm import completion

from config import config
from ingestion.structures import ProcessedChunk
from memory.state_manager import StateManager
from memory.structures import ChatMessage
from retrieval.bm25_engine import BM25Engine
from retrieval.search_fusion import fuse_results 
from retrieval.vector_store import ChromaVectorEngine
from telemetry import track, get_litellm_metadata, update_current_trace, update_current_span

def format_chunk_for_context(chunk: ProcessedChunk) -> str:
    """
    Formats a single ProcessedChunk into a human-readable, token-efficient context string
    for the LLM prompt. Omits technical primary keys (eg, chunk_id, content_hash).
    """
    return (
        f"--- SOURCE: [{chunk.notebook_name} > {chunk.section_name} > {chunk.parent_page_title}] ---\n"
        f"{chunk.text_content}"
    )

@track(name="build_prompt_messages")
def build_prompt_messages(
        user_query: str,
        retrieved_chunks: List[ProcessedChunk],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Assembles standard OpenAI/LiteLLM role-based message list
    including system prompt, conversation history, and active RAG query context.
    """
    # Attach high-level metadata to the root trace
    update_current_span(
        {
            "retrieved_chunk_count": len(retrieved_chunks),
            "history_message_count": len(conversation_history) if conversation_history else 0,
        }
    )

    if system_prompt is None:
       system_prompt = (
            "You are a secure, accurate AI research assistant answering questions based on the user's notes. "
            "Use ONLY the provided context snippets to answer the question. "
            "If the answer cannot be found in the context, explicitly state that you do not have enough information."
        )

    # 1. System Prompt
    messages = [{"role": "system", "content": system_prompt}]

    # 2. Append Conversation History (if available)
    if conversation_history:
        messages.extend(conversation_history)

    # 3. Format Retrieved Context
    if retrieved_chunks:
        formatted_snippets = [format_chunk_for_context(chunk) for chunk in retrieved_chunks] 
        context_block = "\n\n".join(formatted_snippets)
    else:
        context_block = "No relevant document context found."

    user_content = f"CONTEXT:\n{context_block}\n\nUSER QUESTION: {user_query}"

    # Active User turn
    messages.append({"role": "user", "content": user_content})

    return messages

@track(name="run_rag_pipeline")
def run_rag_pipeline(
        user_query: str,
        vector_engine: ChromaVectorEngine,
        bm25_engine: BM25Engine,
        state_manager: Optional[StateManager] = None,
        session_id: Optional[str] = None,
        user_id: str = "default_user",
        filter_dict: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the Phase 1 User Query Lifecycle with Memory Persistence:
    1. Retrieve Past Conversation History from SQLite (if state_manager is provided)
    2. Query Vector Engine (ChromaDB)
    3. Query BM25 Lexical Engine
    4. Fuse/Deduplicate Search Results (via search_fusion)
    5. Assemble Context & Prompt Messages (System + History + Retrieved Context + Query)
    6. Generate Response via LiteLLM
    7. Save User Query and Assistant Response to SQLite (if state_manager is provided)
    8. Return Structured Output (response + citation metadata)
    """
    top_k = top_k or config.retrieval.top_k
    model = model or config.llm.model_name
    session_id = session_id or config.memory.default_session_id

    # Default StateManager fallback if not explicitly injected
    if state_manager is None:
        state_manager = StateManager()

    # Attach high-level metadata to the root trace
    update_current_trace(
        metadata={
            "pipeline": "run_rag_pipeline",
            "session_id": session_id,
            "user_id": user_id,
            "user_query": user_query,
            "user_query_length": len(user_query),
            "top_k": top_k,
            "has_filter": filter_dict is not None,
            "vector_retrieval": config.retrieval.use_vector,
            "bm25_retrieval": config.retrieval.use_bm25,
            "fusion_method": config.retrieval.fusion_strategy,
            "llm_model": config.llm.model_name,
        }
    )

    # 1. Fetch Conversation History (last k turns)
    conversation_history = state_manager.get_conversation_context(
        session_id=session_id,
        limit=config.memory.history_limit
    )

    # 2. Vector Search
    vector_results = vector_engine.search_similar_chunks(
        query_text=user_query,
        top_k=top_k,
        filter_dict=filter_dict
    )

    # 3. BM25 Search
    bm25_results = bm25_engine.search_similar_chunks(
        query_text=user_query,
        top_k=top_k,
        filter_dict=filter_dict
    )

    # 4. Fuse and Deduplicate Results
    fused_chunks: List[ProcessedChunk] = fuse_results(
        vector_results=vector_results,
        bm25_results=bm25_results,
        top_k=top_k
    )

    # 5. Construct Prompt Payload (System + History + Context + Query)
    messages = build_prompt_messages(
        user_query=user_query,
        retrieved_chunks=fused_chunks,
        conversation_history=conversation_history
    )

    # 6. Invoke LLM Generation via LiteLLM
    llm_kwargs = {
        "model": config.llm.model_name,
        "messages": messages,
        "temperature": config.llm.temperature,
    }

    llm_kwargs.update(
        get_litellm_metadata()
    )

    response = litellm.completion(**llm_kwargs)

    assistant_reply = response.choices[0].message.content

    # 7. Persist Both Turns to Memory Storage (User Query + Assistant Reply)
    user_msg = ChatMessage(
        role="user",
        content=user_query,
        session_id=session_id,
        user_id=user_id
    )
    assistant_msg = ChatMessage(
        role="assistant",
        content=assistant_reply,
        session_id=session_id,
        user_id=user_id
    )
    state_manager.save_message(user_msg)
    state_manager.save_message(assistant_msg)

    # 8. Format Structured Citation Metadata
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
        "fused_chunks_count": len(fused_chunks),
        "session_id": session_id
    }