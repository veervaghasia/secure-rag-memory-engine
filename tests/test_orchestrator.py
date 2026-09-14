import pytest
from unittest.mock import patch, MagicMock, ANY
from typing import List

from ingestion.structures import ProcessedChunk
from memory.structures import ChatMessage
from retrieval.orchestrator import (
    format_chunk_for_context,
    build_prompt_messages,
    run_rag_pipeline,
)


# --- FIXTURES ---

@pytest.fixture
def sample_processed_chunk():
    """Provides a single ProcessedChunk for testing string formatting and pipelines."""
    return ProcessedChunk(
        chunk_id="chunk_001",
        parent_page_id="page_100",
        text_content="Self-attention allows tokens to dynamically weight relevance.",
        chunk_index=0,
        notebook_name="AI_Studies",
        section_name="Transformers",
        parent_page_title="Self_Attention_Guide",
        content_hash="hash_001",
    )


@pytest.fixture
def mock_vector_engine():
    """Provides a mocked ChromaVectorEngine returning a standard 2D vector search contract."""
    engine = MagicMock()
    engine.search_similar_chunks.return_value = {
        "ids": [["chunk_001"]],
        "documents": [["Self-attention allows tokens to dynamically weight relevance."]],
        "metadatas": [[
            {
                "notebook_name": "AI_Studies",
                "section_name": "Transformers",
                "parent_page_title": "Self_Attention_Guide",
            }
        ]],
        "distances": [[0.15]],
    }
    return engine


@pytest.fixture
def mock_bm25_engine():
    """Provides a mocked BM25Engine returning a standard 2D BM25 search contract."""
    engine = MagicMock()
    engine.search_similar_chunks.return_value = {
        "ids": [["chunk_001"]],
        "documents": [["Self-attention allows tokens to dynamically weight relevance."]],
        "metadatas": [[
            {
                "notebook_name": "AI_Studies",
                "section_name": "Transformers",
                "parent_page_title": "Self_Attention_Guide",
            }
        ]],
        "distances": [[2.45]],
    }
    return engine


@pytest.fixture
def mock_state_manager():
    """Provides a mocked StateManager for chat history and message persistence."""
    manager = MagicMock()
    manager.get_conversation_context.return_value = [
        {"role": "user", "content": "What are transformers?"},
        {"role": "assistant", "content": "Transformers are neural network architectures."},
    ]
    return manager


@pytest.fixture
def mock_litellm_completion():
    """Provides a mocked LiteLLM completion response object."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Self-attention dynamically weights token relevance."))
    ]
    return mock_response


# --- UNIT TESTS ---

class TestFormattingAndPrompting:
    def test_format_chunk_for_context(self, sample_processed_chunk):
        """Verify chunk formatting creates human-readable title tags without technical primary keys."""
        formatted = format_chunk_for_context(sample_processed_chunk)
        expected_header = "--- SOURCE: [AI_Studies > Transformers > Self_Attention_Guide] ---"
        
        assert expected_header in formatted
        assert sample_processed_chunk.text_content in formatted
        assert "chunk_001" not in formatted  # Ensures primary key chunk_id is omitted

    def test_build_prompt_messages_with_history_and_chunks(self, sample_processed_chunk):
        """Verify message payload assembly when conversation history and retrieved chunks are present."""
        history = [{"role": "user", "content": "Prior question"}]
        query = "How does attention work?"

        messages = build_prompt_messages(
            user_query=query,
            retrieved_chunks=[sample_processed_chunk],
            conversation_history=history,
            system_prompt="Custom System Prompt",
        )

        assert len(messages) == 3
        assert messages[0] == {"role": "system", "content": "Custom System Prompt"}
        assert messages[1] == {"role": "user", "content": "Prior question"}
        assert messages[2]["role"] == "user"
        assert "CONTEXT:\n--- SOURCE: [AI_Studies" in messages[2]["content"]
        assert f"USER QUESTION: {query}" in messages[2]["content"]

    def test_build_prompt_messages_empty_chunks_fallback(self):
        """Verify fallback context string is injected into prompt when retrieved chunks list is empty."""
        messages = build_prompt_messages(
            user_query="Unknown query",
            retrieved_chunks=[],
            conversation_history=None,
        )

        assert len(messages) == 2  # Default system prompt + user turn
        assert "No relevant document context found." in messages[1]["content"]


class TestRunRAGPipeline:
    @patch("retrieval.orchestrator.completion")
    @patch("retrieval.orchestrator.fuse_results")
    def test_run_rag_pipeline_full_success_flow(
        self,
        mock_fuse_results,
        mock_completion,
        mock_vector_engine,
        mock_bm25_engine,
        mock_state_manager,
        mock_litellm_completion,
        sample_processed_chunk,
    ):
        """
        Verify end-to-end orchestration: history fetch, hybrid query execution,
        fusion, LiteLLM call, message persistence, and citation generation.
        """
        mock_fuse_results.return_value = [sample_processed_chunk]
        mock_completion.return_value = mock_litellm_completion

        query = "What is self-attention?"
        result = run_rag_pipeline(
            user_query=query,
            vector_engine=mock_vector_engine,
            bm25_engine=mock_bm25_engine,
            state_manager=mock_state_manager,
            session_id="test_session_123",
            user_id="user_test",
        )

        # 1. Check Retrieval & Fusion calls
        # 1. Check Retrieval & Fusion calls
        mock_state_manager.get_conversation_context.assert_called_once()
        mock_vector_engine.search_similar_chunks.assert_called_once_with(
            query_text=query, top_k=ANY, filter_dict=None
        )
        mock_bm25_engine.search_similar_chunks.assert_called_once_with(
            query_text=query, top_k=ANY, filter_dict=None
        )
        mock_fuse_results.assert_called_once()

        # 2. Check LiteLLM Completion call
        mock_completion.assert_called_once()

        # 3. Check State Persistence calls (User turn + Assistant turn)
        assert mock_state_manager.save_message.call_count == 2
        saved_args = [call.args[0] for call in mock_state_manager.save_message.call_args_list]
        assert isinstance(saved_args[0], ChatMessage)
        assert saved_args[0].role == "user"
        assert saved_args[0].content == query
        assert saved_args[1].role == "assistant"
        assert saved_args[1].content == "Self-attention dynamically weights token relevance."

        # 4. Check Output Response Schema & Sources
        assert result["role"] == "assistant"
        assert result["content"] == "Self-attention dynamically weights token relevance."
        assert result["session_id"] == "test_session_123"
        assert result["fused_chunks_count"] == 1
        assert len(result["sources"]) == 1
        assert result["sources"][0]["chunk_id"] == "chunk_001"
        assert result["sources"][0]["notebook_name"] == "AI_Studies"

    @patch("retrieval.orchestrator.StateManager")
    @patch("retrieval.orchestrator.completion")
    @patch("retrieval.orchestrator.fuse_results")
    def test_run_rag_pipeline_default_state_manager_fallback(
        self,
        mock_fuse_results,
        mock_completion,
        mock_state_manager_cls,
        mock_vector_engine,
        mock_bm25_engine,
        mock_litellm_completion,
    ):
        """Verify default StateManager instantiation when state_manager argument is omitted/None."""
        mock_fuse_results.return_value = []
        mock_completion.return_value = mock_litellm_completion
        mock_instance = MagicMock()
        mock_state_manager_cls.return_value = mock_instance

        result = run_rag_pipeline(
            user_query="Query without state manager",
            vector_engine=mock_vector_engine,
            bm25_engine=mock_bm25_engine,
            state_manager=None,
        )

        mock_state_manager_cls.assert_called_once()
        mock_instance.get_conversation_context.assert_called_once()
        assert result["fused_chunks_count"] == 0
        assert result["sources"] == []