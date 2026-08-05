
#### File: `./config.py`
- `class ChunkingConfig`
- `class VectorStoreConfig`
- `class RetrievalConfig` -> *"Configuration governing hybrid retrieval execution and strategy toggles."*
- `class LLMConfig` -> *"Configuration for LiteLLM generation parameters."*
- `class TelemetryConfig`
  - `verify_telemetry_environment()`
- `class AppConfig`

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

#### File: `./ingestion/structures.py`
- `class RawOnenotePage` -> *"Represents the initial file import before any splitting happens"*
- `class ProcessedChunk` -> *"Represents a single text slice, complete with the redundant metadata fields we need for ChromaDB filtering."*
- `class IngestionPayload` -> *"Container grouping all processed chunks of a page along with  telemetry."*

#### File: `./retrieval/bm25_engine.py`
- `class BM25Engine` -> *"Stateful lexical retrieval engine implementing the BM25Okapi algorithm."*
  - `_tokenize(text)`
      - *"Cleans and splits text into explicit lowercase word tokens."*
  - `upsert_chunks(chunks)`
      - *"Deduplicates chunks via unique hash IDs, caches them in memory, "*
  - `search_similar_chunks(query_text, top_k, filter_dict)`
      - *"Enforces workspace filtering constraints before calculation, computes BM25"*

#### File: `./retrieval/orchestrator.py`
- `def format_chunk_for_context(chunk)`
   - *"Formats a single ProcessedChunk into a human-readable, token-efficient context string"*
- `def build_prompt_messages(user_query, retrieved_chunks, system_prompt)`
   - *"Assembles standard OpenAI/LiteLLM role-based message list."*
- `def run_rag_pipeline(user_query, vector_engine, bm25_engine, filter_dict, top_k, model)`
   - *"Executes the Phase 1 User Query Lifecycle:"*

#### File: `./retrieval/search_fusion.py`
- `def parse_retrieval_results_to_chunks(results)`
   - *"Parses standardized retrieval dictionary output (Chroma/BM25)"*
- `def fuse_results(vector_results, bm25_results, top_k)`
   - *"Fuses results from vector and BM25 retrievers."*

#### File: `./retrieval/vector_store.py`
- `class ChromaVectorEngine`
  - `_compute_embeddings_batch(texts)`
      - *"Invokes LiteLLM to convert a batch of strings into fixed-dimension vectors."*
  - `upsert_chunks(chunks)`
      - *"Transforms ProcessedChunks into vectors and securely upserts them into ChromaDB."*
  - `search_similar_chunks(query_text, top_k, filter_dict)`
      - *"Embeds a raw query string and fetches the top_k most similar matching document chunks."*