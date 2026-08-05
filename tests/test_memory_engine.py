"""
tests/test_memory_engine.py

Test harness verifying Pillar 3 (State & Memory Engine)
1. StateManager unit persistence, retrieval, and session cleanup.
2. Multi-turn conversation retention in end-to-end run_rag_pipeline execution.
"""

import os
from dotenv import load_dotenv

# Load environment variables before initializing internal config modules
load_dotenv()

import opik
from config import config
from ingestion.base_parser import FixedSizeChunker
from ingestion.structures import RawOnenotePage
from memory.state_manager import StateManager
from memory.structures import ChatMessage
from retrieval.bm25_engine import BM25Engine
from retrieval.orchestrator import run_rag_pipeline
from retrieval.vector_store import ChromaVectorEngine


def test_state_manager_unit():
    print("\n" + "=" * 60)
    print("TEST 1: StateManager Persistence & Retrieval Unit Test")
    print("=" * 60)

    test_db = "data/test_conversations.db"
    test_session = "test_unit_session"
    state_mgr = StateManager(db_path=test_db)

    # Clean previous run state
    state_mgr.clear_session(test_session)
    assert len(state_mgr.get_conversation_context(session_id=test_session)) == 0

    # 1. Save User and Assistant Messages
    msg1 = ChatMessage(
        role="user", 
        content="Hello, I am testing memory.", 
        session_id=test_session
    )
    msg2 = ChatMessage(
        role="assistant", 
        content="Hello! Memory test acknowledged.", 
        session_id=test_session
    )

    state_mgr.save_message(msg1)
    state_mgr.save_message(msg2)

    # 2. Retrieve History
    history = state_mgr.get_conversation_context(session_id=test_session)

    assert len(history) == 2, f"Expected 2 messages, got {len(history)}"
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello, I am testing memory."
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hello! Memory test acknowledged."

    print("✅ Message insertion and chronological retrieval verified.")

    # 3. Test Session Cleanup
    state_mgr.clear_session(test_session)
    history_after_clear = state_mgr.get_conversation_context(session_id=test_session)
    assert len(history_after_clear) == 0, f"Session should be empty after clear_session(); has {len(history_after_clear)} messages remaining."

    # Cleanup temporary DB file
    if os.path.exists(test_db):
        os.remove(test_db)

    print("✅ Session cleanup verified.")

@opik.track(project_name=config.telemetry.project_name)
def test_multi_turn_rag_pipeline():
    print("\n" + "=" * 60)
    print("TEST 2: Multi-Turn End-to-End RAG Pipeline Memory Test")
    print("=" * 60)

    # 1. Setup Mock Knowledge Base Data
    mock_page = RawOnenotePage(
        page_id="arch-notes-01",
        notebook_name="Engineering",
        section_name="Architecture",
        page_title="RAG_Specs",
        text_content="The Secure RAG Engine uses ChromaDB for dense vector search and BM25 for lexical search.",
        depth=0,
        page_hash="mock_hash_memory_test"
    )

    chunker = FixedSizeChunker(
        chunk_size=config.chunking.chunk_size,
        chunk_overlap=config.chunking.chunk_overlap
    )

    payload = chunker.chunk_page(mock_page)

    vector_engine = ChromaVectorEngine()
    bm25_engine = BM25Engine()
    vector_engine.upsert_chunks(payload.chunks)
    bm25_engine.upsert_chunks(payload.chunks)

    # Initialize StateManager for Pipeline Test
    state_mgr = StateManager(db_path="data/test_pipeline_memory.db")
    test_session = "multi_turn_integration_session"
    state_mgr.clear_session(test_session)

    # TURN 1: State Establishment
    turn_1_query = "Hi, my favorite research topic is Dense Retrieval."
    print(f"\n[TURN 1 QUERY]: {turn_1_query}")

    res_1 = run_rag_pipeline(
        user_query=turn_1_query,
        vector_engine=vector_engine,
        bm25_engine=bm25_engine,
        state_manager=state_mgr,
        session_id=test_session
    )
    print(f"[TURN 1 ASSISTANT]: {res_1['content']}")

    # Verify Turn 1 Persistence (2 rows: User + Assistant)
    saved_history = state_mgr.get_conversation_context(session_id=test_session)
    assert len(saved_history) == 2, f"Expected 2 messages after Turn 1, got {len(saved_history)}"

    # TURN 2: Contextual Follow-up Query (Relies on Turn 1 History)
    turn_2_query = "What did I say my favorite research topic was?"
    print(f"\n[TURN 2 QUERY]: {turn_2_query}")

    res_2 = run_rag_pipeline(
        user_query=turn_2_query,
        vector_engine=vector_engine,
        bm25_engine=bm25_engine,
        state_manager=state_mgr,
        session_id=test_session
    )
    print(f"[TURN 2 ASSISTANT]: {res_2['content']}")

    # Assertions
    assert "Dense Retrieval" in res_2["content"] or "dense retrieval" in res_2["content"].lower(), \
        "Assistant failed to recall state from Turn 1 history!"

    # Final History Verification (4 rows total)
    final_history = state_mgr.get_conversation_context(session_id=test_session)
    assert len(final_history) == 4, f"Expected 4 messages after both turns, got {len(final_history)}"

    # Cleanup
    state_mgr.clear_session(test_session)

    if os.path.exists("data/test_pipeline_memory.db"):
        os.remove("data/test_pipeline_memory.db")

    print("\n" + "=" * 60)
    print("🎉 MULTI-TURN MEMORY INTEGRATION TEST PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        opik.configure(
            api_key=os.getenv("OPIK_API_KEY"),
            workspace=os.getenv("OPIK_WORKSPACE"),
            force=False,
            automatic_approvals=True
        )
    except Exception as e:
        print(f"⚠️ [Telemetry Warning] Could not connect to Opik cloud: {e}. Continuing without tracing.")

    test_state_manager_unit()
    test_multi_turn_rag_pipeline()
