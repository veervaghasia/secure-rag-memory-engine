"""
tests/test_memory_engine.py

Test harness verifying Pillar 3 (State & Memory Engine)
1. StateManager unit persistence, retrieval, and session cleanup.
2. Multi-turn conversation retention in end-to-end run_rag_pipeline execution.
"""

import os
import sqlite3
import pytest


from dotenv import load_dotenv
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import opik
from config import config
from memory.state_manager import StateManager
from memory.structures import ChatMessage


# --- FIXTURES ---

@pytest.fixture
def state_mgr(tmp_path):
    """
    Provides a fresh, isolated StateManager instance pointing to 
    a temporary SQLite database created inside pytest's tmp_path.
    """
    test_db_path = str(tmp_path / "test_memory.db")
    mgr = StateManager(db_path=test_db_path)
    return mgr


@pytest.fixture
def sample_messages():
    """Provides standard ChatMessage DTO instances for history testing."""
    return [
        ChatMessage(
            role="user",
            content="Hello, I am testing memory context.",
            session_id="dummy_session_id",
            user_id="user_1"
        ),
        ChatMessage(
            role="assistant",
            content="Hello! State persistence confirmed.",
            session_id="dummy_session_id",
            user_id="assistant"
        ),
        ChatMessage(
            role="user",
            content="Can you summarize our previous turn?",
            session_id="dummy_session_id",
            user_id="user_1"
        )
    ]


# --- UNIT TESTS: STATE MANAGER ---

class TestStateManagerSessions:

    def test_init_db_creates_default_session(self, state_mgr):
        """Verify _init_db automatically creates default_session_id in database."""
        sessions = state_mgr.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == config.memory.default_session_id
        assert sessions[0]["session_name"] == "Default Session"

    def test_get_or_create_session_new_and_existing(self, state_mgr):
        """Verify get_or_create_session creates a new session ID and reuses it on subsequent calls."""
        session_name = "Architecture Discussions"

        # First call: Should create a new UUID session entry
        session_id_1 = state_mgr.get_or_create_session(session_name)
        assert isinstance(session_id_1, str)
        assert len(session_id_1) > 0

        # Second call: Should lookup and return the exact same session_id
        session_id_2 = state_mgr.get_or_create_session(session_name)
        assert session_id_1 == session_id_2

        # Verify list_sessions reflects default session + new session
        all_sessions = state_mgr.list_sessions()
        assert len(all_sessions) == 2

    def test_rename_session_success(self, state_mgr):
        """Verify renaming an existing session updates session_name correctly."""
        old_name = "Initial Session Name"
        new_name = "Refactored Session Name"

        session_id = state_mgr.get_or_create_session(old_name)
        success = state_mgr.rename_session(old_name, new_name)

        assert success is True
        # Lookup using new name should resolve to original session_id
        assert state_mgr._get_session_id_by_name(new_name) == session_id
        # Lookup using old name should yield None
        assert state_mgr._get_session_id_by_name(old_name) is None

    def test_rename_session_non_existent_and_collision(self, state_mgr):
        """Verify rename_session returns False when old name missing or target name exists."""
        state_mgr.get_or_create_session("Session Alpha")
        state_mgr.get_or_create_session("Session Beta")

        # Case 1: Non-existent old name
        assert state_mgr.rename_session("NonExistent", "New Name") is False

        # Case 2: Target name collision
        assert state_mgr.rename_session("Session Alpha", "Session Beta") is False


class TestStateManagerMessages:

    def test_save_and_retrieve_conversation_context(self, state_mgr, sample_messages):
        """Verify message persistence, chronological retrieval order, and content matching."""
        session_id = state_mgr.get_or_create_session("Chat Thread 1")

        for msg in sample_messages:
            msg.session_id = session_id
            state_mgr.save_message(msg)

        context = state_mgr.get_conversation_context(session_id=session_id)

        assert len(context) == 3
        # Assert chronological ordering (User turn 1 -> Assistant turn 1 -> User turn 2)
        assert context[0] == {"role": "user", "content": "Hello, I am testing memory context."}
        assert context[1] == {"role": "assistant", "content": "Hello! State persistence confirmed."}
        assert context[2] == {"role": "user", "content": "Can you summarize our previous turn?"}

    def test_get_conversation_context_limit(self, state_mgr, sample_messages):
        """Verify limit parameter restricts output to N most recent messages in chronological order."""
        session_id = state_mgr.get_or_create_session("Limit Test Thread")

        for msg in sample_messages:
            msg.session_id = session_id
            state_mgr.save_message(msg)

        # Retrieve last 2 messages
        limited_context = state_mgr.get_conversation_context(session_id=session_id, limit=2)

        assert len(limited_context) == 2
        # Should return the 2 latest turns ordered chronologically
        assert limited_context[0]["content"] == "Hello! State persistence confirmed."
        assert limited_context[1]["content"] == "Can you summarize our previous turn?"

    def test_get_full_history_by_name(self, state_mgr, sample_messages):
        """Verify get_full_history_by_name returns formatted dictionaries with timestamps."""
        session_name = "Detailed History Thread"
        session_id = state_mgr.get_or_create_session(session_name)

        for msg in sample_messages:
            msg.session_id = session_id
            state_mgr.save_message(msg)

        full_history = state_mgr.get_full_history_by_name(session_name)

        assert full_history is not None
        assert len(full_history) == 3
        assert "timestamp" in full_history[0]
        assert full_history[0]["role"] == "user"

        # Non-existent session name should return None
        assert state_mgr.get_full_history_by_name("Missing Session") is None


class TestStateManagerDeletion:

    def test_clear_session_history_by_name(self, state_mgr, sample_messages):
        """Verify clearing history wipes messages but preserves session metadata row."""
        session_name = "Clear History Thread"
        session_id = state_mgr.get_or_create_session(session_name)

        for msg in sample_messages:
            msg.session_id = session_id
            state_mgr.save_message(msg)

        # Confirm messages present
        assert len(state_mgr.get_conversation_context(session_id)) == 3

        # Clear message history
        cleared = state_mgr.clear_session_history_by_name(session_name)
        assert cleared is True

        # Messages should be empty, but session row should still exist
        assert len(state_mgr.get_conversation_context(session_id)) == 0
        assert state_mgr._get_session_id_by_name(session_name) == session_id

    def test_delete_session_by_name(self, state_mgr, sample_messages):
        """Verify delete_session_by_name purges both messages and session metadata."""
        session_name = "Purge Thread"
        session_id = state_mgr.get_or_create_session(session_name)

        for msg in sample_messages:
            msg.session_id = session_id
            state_mgr.save_message(msg)

        # Delete session completely
        deleted = state_mgr.delete_session_by_name(session_name)
        assert deleted is True

        # Session metadata and history should both be removed
        assert state_mgr._get_session_id_by_name(session_name) is None
        assert len(state_mgr.get_conversation_context(session_id)) == 0

    def test_delete_and_clear_non_existent_session(self, state_mgr):
        """Verify clear and delete operations return False gracefully for invalid names."""
        assert state_mgr.clear_session_history_by_name("Ghost Session") is False
        assert state_mgr.delete_session_by_name("Ghost Session") is False


# --- INTEGRATION TEST: RAG PIPELINE CONVERSATION ---

class TestMultiTurnMemoryIntegration:

    @patch("retrieval.orchestrator.run_rag_pipeline")
    def test_multi_turn_rag_pipeline_memory_flow(self, mock_pipeline, state_mgr):
        """
        Simulates end-to-end multi-turn dialog state progression using StateManager.
        """
        session_name = "Multi-Turn Pipeline Session"
        session_id = state_mgr.get_or_create_session(session_name)

        # Simulated Turn 1
        turn1_user = ChatMessage(
            role="user",
            content="My favorite topic is Dense Retrieval.",
            session_id=session_id
        )
        turn1_assistant = ChatMessage(
            role="assistant",
            content="Duly noted! I'll keep Dense Retrieval in mind.",
            session_id=session_id
        )
        state_mgr.save_message(turn1_user)
        state_mgr.save_message(turn1_assistant)

        history_t1 = state_mgr.get_conversation_context(session_id=session_id)
        assert len(history_t1) == 2

        # Simulated Turn 2
        turn2_user = ChatMessage(
            role="user",
            content="What did I say my favorite topic was?",
            session_id=session_id
        )
        turn2_assistant = ChatMessage(
            role="assistant",
            content="You mentioned that your favorite topic is Dense Retrieval.",
            session_id=session_id
        )
        state_mgr.save_message(turn2_user)
        state_mgr.save_message(turn2_assistant)

        history_t2 = state_mgr.get_conversation_context(session_id=session_id)
        assert len(history_t2) == 4
        assert "Dense Retrieval" in history_t2[3]["content"]