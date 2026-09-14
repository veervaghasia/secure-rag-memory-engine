import sqlite3
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional, Generator
from config import config
from memory.structures import ChatMessage

class StateManager:
    """
    Handles SQLite database persistence and state retrieval for chat sessions.
    Strictly responsible for database I/O contains no prompt or LLM logic.
    Manages relational integrity across 'sessions' and 'messages' tables.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.memory.database_path
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
        Creates the sessions and messages schemas with relational 
        constraints, and session indices if they do not exist.
        """
        with self._get_connection() as conn:
            # Table 1: Sessions Metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    session_name TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            # Table 2: Messages History
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
                );
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON messages (session_id);
            """)

            # Ensure baseline default session exists
            default_id = config.memory.default_session_id
            now_str = datetime.now().isoformat()
            conn.execute("""
                INSERT OR IGNORE INTO sessions (session_id, session_name, created_at, updated_at)
                VALUES (?, ?, ?, ?);
            """, (default_id, "Default Session", now_str, now_str))

    def _get_session_id_by_name(self, session_name: str) -> Optional[str]:
        """
        Private helper to resolve session_name to session_id.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM sessions WHERE session_name = ?", (session_name,))
            row = cursor.fetchone()
            return row["session_id"] if row else None

    def get_or_create_session(self, session_name: str) -> str:
        """
        Lookup a session_id by session_name. 
        If non-existant, creates a new entry.
        Returns the session_id string.
        """
        session_id = self._get_session_id_by_name(session_name)
        if session_id:
            return session_id      

        # Generate new session entry if it does not exist
        new_id = str(uuid.uuid4())
        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO sessions (session_id, session_name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (new_id, session_name, now_str, now_str))

        print(f"✨ Created new session thread: '{session_name}' (ID: {new_id[:8]}...)")
        return new_id

    def rename_session(self, old_name: str, new_name: str) -> bool:
        """
        Renames a session display name. Validates uniqueness before updating.
        """
        session_id = self._get_session_id_by_name(old_name)

        # Check if old session record exists
        if not session_id:
            print(f"❌ Session '{old_name}' not found.")
            return False

        # Check if the target name already exists
        if self._get_session_id_by_name(new_name):
            print(f"⚠️ Cannot rename: A session named '{new_name}' already exists.")
            return False

        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:           
            conn.execute("""
                UPDATE sessions
                SET session_name = ?, updated_at = ?
                WHERE session_id = ?
            """, (new_name, now_str, session_id))

        print(f"✅ Successfully renamed session '{old_name}' -> '{new_name}'.")
        return True

    def save_message(self, message: ChatMessage) -> None:
        """
        Persists a ChatMessage DTO into SQLite.
        Ensures parent session exists first.
        Converts datetime timestamp into standard ISO string format.
        """
        timestamp_str = (
            message.timestamp.isoformat() 
            if isinstance(message.timestamp, datetime) 
            else str(message.timestamp)
        )

        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sessions SET updated_at = ? WHERE session_id = ?
            """, (now_str, message.session_id))

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

    def clear_session_history_by_name(self, session_name: str) -> bool:
        """
        Deletes messages for a session by session_name
        while preserving session metadata.
        """
        session_id = self._get_session_id_by_name(session_name)
        if not session_id:
            print(f"⚠️ Session '{session_name}' does not exist.")
            return False

        with self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

        print(f"🗑️ Cleared history for session '{session_name}'.")
        return True

    def delete_session_by_name(self, session_name: str) -> bool:
        """
        Purges session metadata and all associated messages by session_name.
        """
        session_id = self._get_session_id_by_name(session_name)
        if not session_id:
            print(f"⚠️ Session '{session_name}' does not exist.")
            return False

        with self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        print(f"🔥 Permanently deleted session '{session_name}'.")
        return True

    def get_conversation_context(
            self,
            session_id: Optional[str] = None,
            limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Retrieves the last `limit` messages for a session ordered chronologically.
        Returns a list of dicts formatted for LiteLLM completion calls:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        # Late binding with explicit None checks to avoid truthiness traps (e.g., limit=0)
        if session_id is None:
            session_id = config.memory.default_session_id
            
        if limit is None:
            limit = config.memory.history_limit

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

    def get_full_history_by_name(self, session_name: str) -> Optional[List[Dict[str, str]]]:
        """
        Retrieves complete message istory by session_name.
        Returns None if session does not exist, or a list of message dicts.
        """
        session_id = self._get_session_id_by_name(session_name)
        if not session_id:
            return None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content, timestamp
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC 
                """,
                (session_id,)
            )
            rows = cursor.fetchall()

        return [
            {
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"]
            }
            for row in rows
        ]

    def list_sessions(self) -> List[str]:
        """
        Retrieves a list of all distinct session metadata records stored in the database.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT session_id, session_name, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                """
            )
            rows = cursor.fetchall()

        return [
            {
                "session_id": row["session_id"],
                "session_name": row["session_name"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]