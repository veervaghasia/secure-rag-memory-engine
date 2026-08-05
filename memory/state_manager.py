import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional, Generator
from config import config
from memory.structures import ChatMessage

class StateManager:
    """
    Handles SQLite database persistence and state retrieval for chat sessions.
    Strictly responsible for database I/O contains no prompt or LLM logic.
    """

    def __init__(self, db_path: str = config.memory.database_path):
        self.db_path = db_path
        # Ensure parent directories exist before connecting
        db_dir = os.path.dirname(self.db_path)  # Get the directory part of the database path
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)  # Create directories if they don't exist

        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager that yields a managed SQLite connection.
        Handles commits, rollbacks on failure, and gurantees connection closure.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """
        Creates the messages schema and session indices if they do not exist.
        """
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON messages (session_id);
            """)

    def save_message(self, message: ChatMessage) -> None:
        """
        Persists a ChatMessage DTO into SQLite.
        Converts datetime timestamp into standard ISO string format.
        """
        timestamp_str = (
            message.timestamp.isoformat() 
            if isinstance(message.timestamp, datetime) 
            else str(message.timestamp)
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (session_id, user_id, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message.session_id,
                    message.user_id,
                    message.role,
                    message.content,
                    timestamp_str
                )
            )

    def clear_session(self, session_id: str) -> None:
        """
        Removes all stored messages for a specific session_id.
        """
        query = "DELETE FROM messages WHERE session_id = ?"
        with self._get_connection() as conn:
            conn.execute(query, (session_id,))

    def get_conversation_context(
            self,
            session_id: str = config.memory.default_session_id,
            limit: int = config.memory.history_limit
    ) -> List[Dict[str, str]]:
        """
        Retrieves the last `limit` messages for a session ordered chronologically.
        Returns a list of dicts formatted for LiteLLM completion calls:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content FROM (
                    SELECT id, role, content 
                    FROM messages 
                    WHERE session_id = ? 
                    ORDER BY id DESC 
                    LIMIT ?
                ) ORDER BY id ASC
                """,
                (session_id, limit)
            )
            rows = cursor.fetchall()

        return [{"role": row["role"], "content": row["content"]} for row in rows]