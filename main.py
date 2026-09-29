"""
main.py

Interactive multi-turn CLI application for Secure RAG Memory Engine.
Initializes vector, lexical, and state engines once, then enters a 
continuous session loop to answer user queries or execute system slash commands.
"""

# from dotenv import load_dotenv

# load_dotenv()

import os
import time 
from config import config
from ingestion.experiment_registry import list_experiments
from memory.state_manager import StateManager
from retrieval.bm25_engine import BM25Engine
from retrieval.orchestrator import run_rag_pipeline
from retrieval.vector_store import ChromaVectorEngine
from telemetry import configure_telemetry, configure_litellm

def print_help():
    """
    Prints the available CLI slash commands and their descriptions.
    """
    print("\n" + "=" * 60)
    print("🛠️  AVAILABLE CLI COMMANDS")
    print("=" * 60)
    print("  /help                     - Show this help menu")
    print("  /exit, /quit              - Terminate the chat session")
    print("  /info                     - Show active experiment & system setup")
    print("  /sessions                 - List all stored chat session names")
    print("  /switch <session_name>    - Switch to an existing or new chat session")
    print("  /rename <new_session_name>- Rename the active chat session")
    print("  /history [session_name]   - Display full chat history for active/specified session")
    print("  /clear [session_name]     - Clear chat history for active/specified session")
    print("  /delete <session_name>    - Permanently purge a session and its history")
    print("  /experiments              - List all registered experiments in the registry")
    print("=" * 60 + "\n")

def print_info(current_session_name: str, current_session_id: str):
    """
    Prints active runtime state and configuration settings.
    """
    print("\n" + "=" * 60)
    print("ℹ️  ACTIVE SYSTEM CONFIGURATION")
    print("=" * 60)
    print(f"  • Active Session Name: {current_session_name}")
    print(f"  • Active Session ID  : {current_session_id}")
    print(f"  • Experiment ID      : {config.experiment.experiment_id}")
    print(f"  • Vector Collection  : {config.vector_store.collection_name}")
    print(f"  • BM25 Index Path    : {config.bm25.index_path}")
    print(f"  • Embedding Model    : {config.vector_store.embedding_model}")
    print(f"  • LLM Model          : {config.llm.model_name}")
    print("=" * 60 + "\n")

def main():
    print("=" * 60)
    print("🚀 INITIALIZING SECURE RAG ENGINE (MULTI-TURN CLI)")
    print("=" * 60)

    # Instantiate stateful engines ONCE outside the loop
    state_manager = StateManager()
    vector_engine = ChromaVectorEngine()
    bm25_engine = BM25Engine()

    # Track active runtime session ID locally
    current_session_name = "Default Session"

    print("✨ Engines successfully initialized. Ready for user queries!")
    print(f"💬 Active Session: '{current_session_name}'")
    print("💡 Type '/help' to view all available interactive commands.")
    print("💡 Type '/exit' or '/quit' to terminate the session.")
    print("-" * 60)

    # Continuous multi-turn interaction loop
    while True:
        try:
            user_input = input(f"\n[{current_session_name}] You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Session interrupted. Exiting...")
            break

        # 1. Edge Case: Empty input check
        if not user_input:
            print("⚠️ Input was empty. Please type a message or enter '/help' for commands.")
            continue

        # Extract normalized command key
        cmd_key = user_input.lower()

        # 2. Command: Exit
        if cmd_key in ["/exit", "/quit", "exit", "quit"]:
            print("👋 Ending session. Conversation saved to memory store.")
            break

        # 3. Command: Help Menu
        elif cmd_key == "/help":
            # Show available commands
            print_help()

        # 4. Command: System Context Info
        elif cmd_key == "/info":
            session_id = state_manager.get_or_create_session(current_session_name)
            print_info(current_session_name, session_id)   

        # 5. Command: List Sessions
        elif cmd_key == "/sessions":
            # Call state_manager.list(sessions) and print list
            sessions = state_manager.list_sessions()
            print("\n" + "=" * 60)
            print("📜 STORED CHAT SESSIONS")
            print("=" * 60)
            if sessions:
                for s in sessions:
                    name = s["session_name"]
                    updated = s["updated_at"]
                    active_marker = " (Active)" if name == current_session_name else ""
                    print(f"  • {name}{active_marker} [Last active: {updated}]")
            else:
                print("  (No recorded sessions found in database)")
            print("=" * 60 + "\n")  

        # 6. Command: Switch Active Session
        elif cmd_key.startswith("/switch"):
            # Extract the session_id from user_input.split() and update current_session_id
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                print("⚠️ Usage: /switch <session_name> (e.g. /switch Project Architecture)")
            else:
                target_session = parts[1].strip()
                current_session_name = target_session
                state_manager.get_or_create_session(current_session_name)
                print(f"🔄 Switched active session to: '{current_session_name}'")

        # 7. Command: Rename Session
        elif cmd_key.startswith("/rename"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                print("⚠️ Usage: /rename <new_session_name>")
            else:
                new_name = parts[1].strip()
                if state_manager.rename_session(current_session_name, new_name):
                    current_session_name = new_name
         
        # 8. Command: Display Active/Specified Session History
        elif cmd_key.startswith("/history"):
            parts = user_input.split(maxsplit=1)
            target_name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else current_session_name

            history = state_manager.get_full_history_by_name(target_name)
            print("\n" + "=" * 60)
            print(f"📖 CHAT HISTORY FOR SESSION: '{target_name}'")
            print("=" * 60)
            if history is None:
                print(f"⚠️ Session '{target_name}' does not exist.")
            elif history:
                for msg in history:
                    role_label = "👤 User" if msg["role"] == "user" else "🤖 Assistant"
                    timestamp = msg.get("timestamp", "N/A")
                    print(f"\n[{timestamp}] {role_label}:")
                    print(f"  {msg['content']}")
            else:
                print("  (No message history recorded for this session yet)")
            print("=" * 60 + "\n")

        # 9. Command: Clear Active/Specified Session Memory
        elif cmd_key.startswith("/clear"):
            parts = user_input.split(maxsplit=1)
            target_name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else current_session_name
            state_manager.clear_session_history_by_name(target_name)

        # 10. Command: Delete Session
        elif cmd_key.startswith("/delete"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                print("⚠️ Usage: /delete <session_name>")
            else:
                target_name = parts[1].strip()
                if state_manager.delete_session_by_name(target_name):
                    if target_name == current_session_name:
                        current_session_name = "Default Session"
                        state_manager.get_or_create_session(current_session_name)
                        print(f"🔄 Active session reset to: '{current_session_name}'")

        # 11. Command: List Registered Experiments
        elif cmd_key == "/experiments":
            # Call list_experiments() from experiment_regisrty.py
            experiments = list_experiments()
            print("\n" + "=" * 60)
            print("🧪 REGISTERED EXPERIMENTS")
            print("=" * 60)
            if experiments:
                for exp_id, record in experiments.items():
                    active_tag = " (Active Engine)" if exp_id == config.experiment.experiment_id else ""
                    print(f"\n  • ID: {exp_id}{active_tag}")
                    print(f"    Status     : {record.get('status', 'N/A')}")
                    print(f"    Description: {record.get('description', 'N/A')}")
                    print(f"    Chunk Size : {record.get('chunk_size')} | Overlap: {record.get('chunk_overlap')}")
            else:
                print("  (No experiments registered yet in data/experiments.json)")
            print("=" * 60 + "\n")

        # 12. Regular User Query: Route to RAG Pipeline
        else: 
            session_id = state_manager.get_or_create_session(current_session_name)
            print("\n🔍 Thinking & retrieving notes...")
            t_start = time.perf_counter()

            result = run_rag_pipeline(
                user_query=user_input,
                vector_engine=vector_engine,
                bm25_engine=bm25_engine,
                state_manager=state_manager,
                session_id=session_id
            )

            t_end = time.perf_counter()
            elapsed_time = t_end - t_start

            # Render assistant output, timing, and citations
            print("\n" + "=" * 60)
            print("[ASSISTANT RESPONSE]")
            print("=" * 60)
            print(result["content"])
            print(f"\n⏱️ Latency: {elapsed_time:.2f}s")

            print("\n[CITED SOURCES]")
            if result["sources"]:
                for src in result["sources"]:
                    print(
                        f" • [{src['notebook_name']} > {src['section_name']} > {src['parent_page_title']}] "
                        f"(ID: {src['chunk_id'][:8]}...)"
                    )
                    print(f"   Snippet: {src['snippet']}\n")
            else:
                print(" • No external document context was retrieved.")

        print("-" * 60)
        

if __name__ == "__main__":
    # Configure telemetry and litellm telemetry if enabled in config
    configure_telemetry()
    configure_litellm()

    # Initialize engine once and launch main loop...
    main()