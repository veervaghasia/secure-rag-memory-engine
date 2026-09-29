
#### File: `./config.py`
- `class ExperimentConfig` -> *"Configuration for experiment isolation and metadata registry."*
- `class MemoryConfig` -> *"Configuration settings for memory management and persistence."*
- `class ChunkingConfig`
- `class VectorStoreConfig`
- `class BM25Config` -> *"Configuration settings for BM25 index storage and persistence."*
- `class RetrievalConfig` -> *"Configuration governing hybrid retrieval execution and strategy toggles."*
- `class LLMConfig` -> *"Configuration for LiteLLM generation parameters."*
- `class TelemetryConfig`
  - `verify_telemetry_environment()`
- `class AppConfig`
  - `synchronize_experiment_paths()`
      - *"Ensures all store collection names, BM25 index paths, and manifest paths"*

#### File: `./ingest.py`
- `def reset_experiment_pipeline()`
   - *"Resets all persistent artifacts belonging to the active experiment."*
- `def run_ingestion(data_directory, description)`
   - *"Runs the document parsing and chunking pipeline, "*
- `def main()`

#### File: `./ingestion/base_parser.py`
- `class FixedSizeChunker` -> *"Splits a given text into fixed-size chunks of a specified size."*
  - `_generate_deterministic_hash(text)`
      - *"Generates a stable SHA-256 hex string for deduplication."*
  - `chunk_page(page)`
      - *"Slices a RawOnenotePage into fixed-character ProcessedChunks with metadata."*

#### File: `./ingestion/docx_parser.py`
- `class SecureDocxParser` -> *"Parses exported .docx sections from OneNote, applying strict automated security redaction filters,"*
  - `_load_manifest()`
      - *"Loads the historical ingestion ledger to check for previously parsed documents."*
  - `clear_manifest_cache()`
      - *"Forcefully clears the local manifest file and resets the in-memory cache."*
  - `_save_manifest()`
      - *"Persists the updated operational status cache back onto local disk storage."*
  - `_sanitize_text(text)`
      - *"Scans raw strings for potential credentials and replaces them with a redacted placeholder."*
  - `_generate_deterministic_hash(text)`
      - *"Genereates a secure, deterministic SHA-256 hex digit for IDs and content tracking."*
  - `parse_section_into_pages(file_path, notebook_name, section_name)`
      - *"Reads a single .docx section file, detects genuine page segments by validating OneNote's native timestamp signatures, "*
  - `scan_directory(root_dir)`
      - *"Recursively walks directories, checking local modification files against"*

#### File: `./ingestion/experiment_registry.py`
- `def _load_registry()`
   - *"Helper to read the JSON registry file from disk if it exists."*
- `def _save_registry(data)`
   - *"Helper to write the dictionary back to disk."*
- `def register_experiment(description, status)`
   - *"Logs the current active configuration settings as an experiment "*
- `def update_experiment_description(experiment_id, new_description)`
   - *"Updates the description field for an existing registered experiment "*
- `def update_experiment_status(experiment_id, new_status)`
   - *"Updates the operational status (e.g., 'active', 'archived', 'purged') for an experiment."*
- `def list_experiments()`
   - *"Retrieves all previously registered experiment metadata entries."*

#### File: `./ingestion/structures.py`
- `class RawOnenotePage` -> *"Represents the initial file import before any splitting happens"*
- `class ProcessedChunk` -> *"Represents a single text slice, complete with the redundant metadata fields we need for ChromaDB filtering."*
- `class IngestionPayload` -> *"Container grouping all processed chunks of a page along with  telemetry."*

#### File: `./memory/state_manager.py`
- `class StateManager` -> *"Handles SQLite database persistence and state retrieval for chat sessions."*
  - `_get_connection()`
      - *"Context manager that yields a managed SQLite connection."*
  - `_init_db()`
      - *"Creates the sessions and messages schemas with relational "*
  - `_get_session_id_by_name(session_name)`
      - *"Private helper to resolve session_name to session_id."*
  - `get_or_create_session(session_name)`
      - *"Lookup a session_id by session_name. "*
  - `rename_session(old_name, new_name)`
      - *"Renames a session display name. Validates uniqueness before updating."*
  - `save_message(message)`
      - *"Persists a ChatMessage DTO into SQLite."*
  - `clear_session_history_by_name(session_name)`
      - *"Deletes messages for a session by session_name"*
  - `delete_session_by_name(session_name)`
      - *"Purges session metadata and all associated messages by session_name."*
  - `get_conversation_context(session_id, limit)`
      - *"Retrieves the last `limit` messages for a session ordered chronologically."*
  - `get_full_history_by_name(session_name)`
      - *"Retrieves complete message istory by session_name."*
  - `list_sessions()`
      - *"Retrieves a list of all distinct session metadata records stored in the database."*

#### File: `./memory/structures.py`
- `class ChatMessage` -> *"Data Transfer Object (DTO) representing a single message turn."*
  - `to_llm_dict()`
      - *"Helper method converting the DTO into standard LiteLLM format."*

#### File: `./retrieval/bm25_engine.py`
- `class BM25Engine` -> *"Stateful lexical retrieval engine implementing the BM25Okapi algorithm."*
  - `_load_index()`
      - *"Hydrates BM25 state from disk if index file exists and is valid."*
  - `_save_index()`
      - *"Serializes in-memory dictionary and BM25 model arrays directly to disk."*
  - `reset_index()`
      - *"Clears in-memory data structures and removes the "*
  - `_tokenize(text)`
      - *"Cleans and splits text into explicit lowercase word tokens."*
  - `upsert_chunks(chunks)`
      - *"Deduplicates chunks via unique hash IDs, caches them in memory, "*
  - `search_similar_chunks(query_text, top_k, filter_dict)`
      - *"Enforces workspace filtering constraints before calculation, computes BM25"*

#### File: `./retrieval/orchestrator.py`
- `def format_chunk_for_context(chunk)`
   - *"Formats a single ProcessedChunk into a human-readable, token-efficient context string"*
- `def build_prompt_messages(user_query, retrieved_chunks, conversation_history, system_prompt)`
   - *"Assembles standard OpenAI/LiteLLM role-based message list"*
- `def run_rag_pipeline(user_query, vector_engine, bm25_engine, state_manager, session_id, user_id, filter_dict, top_k, model)`
   - *"Executes the Phase 1 User Query Lifecycle with Memory Persistence:"*

#### File: `./retrieval/search_fusion.py`
- `def parse_retrieval_results_to_chunks(results)`
   - *"Parses standardized retrieval dictionary output (Chroma/BM25)"*
- `def fuse_results(vector_results, bm25_results, top_k)`
   - *"Fuses results from vector and BM25 retrievers."*

#### File: `./retrieval/vector_store.py`
- `class ChromaVectorEngine`
  - `reset_store()`
      - *"Deletes the underlying Chroma collection from disk and"*
  - `_compute_embeddings_batch(texts)`
      - *"Invokes LiteLLM to convert strings into fixed-dimension vectors in chunks"*
  - `upsert_chunks(chunks)`
      - *"Transforms ProcessedChunks into vectors and securely upserts them into ChromaDB."*
  - `search_similar_chunks(query_text, top_k, filter_dict)`
      - *"Embeds a raw query string and fetches the top_k most similar matching document chunks."*

#### File: `./telemetry/opik_adapter.py`
- `def is_enabled()`
- `def is_available()`
- `def configure_telemetry()`
   - *"Configure Opik only when telemetry is enabled."*
- `def configure_litellm()`
   - *"Register the Opik LiteLLM callback only when Opik is enabled."*
- `def track()`
   - *"Backend-neutral tracking decorator."*
- `def update_current_trace(metadata)`
   - *"Update the current telemetry trace when telemetry is enabled."*
- `def update_current_span(metadata)`
   - *"Update the currently active Opik span when telemetry is available."*
- `def get_litellm_metadata()`
   - *"Return metadata required to connect a LiteLLM call to the"*