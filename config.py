"""
config.py

Central configuration management for the Secure RAG Memeory Engine.
Provides a single source of truth for experiment tracking, chunking,
storage engine paths, LLM, memory, and telemetry.
"""

import os
from pydantic import BaseModel, Field, model_validator
from dotenv import load_dotenv

# Ensure env variables from .env are loaded into the process runtime
load_dotenv()

class ExperimentConfig(BaseModel):
    """
    Configuration for experiment isolation and metadata registry.
    """
    experiment_id: str = Field(
        default="v1_baseline_chunk520_overlap_130",
        description="Unique identifier for the current experiment run."
    )
    registry_path: str = Field(
        default="data/experiments.json",
        description="Local JSON file tracking all registered experiment metadata."
    )
    manifest_path: str = Field(
        default="data/ingestion_manifest_v1_baseline.json",
        description="Dynamic manifest cache path, updated based on experiment_id."
    )

class MemoryConfig(BaseModel):
    """
    Configuration settings for memory management and persistence.
    """
    database_path: str = Field(
        default="data/conversations.db",
        description="Local disk path for SQLite state database."
    )
    default_session_id: str = Field(
        default="default_session",
        description="Fallback session ID for single-user testing/Phase 1."
    )
    history_limit: int = Field(
        default=10,
        description="Number of past messages (k) retrieved during get_conversation_context()."
    )

class ChunkingConfig(BaseModel):
    chunk_size: int = Field(
        default=520,
        description="Size of each text chunk."
    )
    chunk_overlap: int = Field(
        default=130,
        description="Overlap between consecutive text chunks."
    )

class VectorStoreConfig(BaseModel):
    collection_name: str = Field(
        default="onenote_knowledge_base_v1_baseline",
        description="Dynamic Chroma collection name derived from experiment_id."
    )
    persist_directory: str = Field(
        default="data/chroma_db",
        description="Root directory for persistent Chroma DB vector store."
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model used for dense retrieval."
    )
    embedding_batch_size: int = Field(
        default=250,
        description="Maximum number of text chunks per embedding API call to stay within OpenAI token limits."
    )
    chroma_upsert_batch_size: int = Field(
        default=5000,
        description="Maximum number of vectors per upsert call to ChromaDB to avoid memory issues."
    )

class BM25Config(BaseModel):
    """
    Configuration settings for BM25 index storage and persistence.
    """
    index_path: str = Field(
        default="data/bm25_index_v1_baseline.pkl",
        description="Dynamic local path for serialized BM25 pickle file based on experiment_id."
    )

class RetrievalConfig(BaseModel):
    """
    Configuration governing hybrid retrieval execution and strategy toggles.
    Enables single-flag toggles for ablation studies.
    """
    top_k: int = 5
    use_vector: bool = True
    use_bm25: bool = True
    fusion_strategy: str = "concat"  # Phase 1: "concat" | Phase 2: "rrf"

class LLMConfig(BaseModel):
    """
    Configuration for LiteLLM generation parameters.
    """
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.0
    # max_tokens: int = 1000

class TelemetryConfig(BaseModel):
    enable_opik: bool = True
    project_name: str = "secure-rag-memory-engine"  # Unified root project
    current_phase: str = "phase-1-baseline"  # Filterable workspace tag

    @model_validator(mode="after")
    def verify_telemetry_environment(self):
        # Global absolute dependency check
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("❌ [Config Error] CRITICAL: OPENAI_API_KEY is missing from environment or .env file.")
        else: 
            print("✅ [Telemetry Config] OPENAI_API_KEY detected.")

        # Conditional telemetry tracking check
        if self.enable_opik:
            opik_key = os.getenv("OPIK_API_KEY")
            if not opik_key:
                print("⚠️ [Telemetry Warning] OPIK_API_KEY not found. Telemetry will trace locally (http://localhost:5173).")
            else: 
                print("✅ [Telemetry Config] OPIK_API_KEY detected. Traces will stream to cloud dashboard.")
        else:
            print("🛑 [Telemetry Config] Opik tracing is explicitly disabled.")

        return self
    
class AppConfig(BaseModel):
    experiment: ExperimentConfig = ExperimentConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    vector_store: VectorStoreConfig = VectorStoreConfig()
    bm25: BM25Config = BM25Config()
    retrieval: RetrievalConfig = RetrievalConfig()
    llm: LLMConfig = LLMConfig()
    telemetry: TelemetryConfig = TelemetryConfig()
    memory: MemoryConfig = MemoryConfig()

    @model_validator(mode="after")
    def synchronize_experiment_paths(self):
        """
        Ensures all store collection names, BM25 index paths, and manifest paths
        are automatically synchronized with the configured experiment_id.
        """
        exp_id = self.experiment.experiment_id

        # Dynamically set collection name, index path, and manifest path
        self.vector_store.collection_name = f"onenote_knowledge_base_{exp_id}"
        self.bm25.index_path = f"data/bm25_index_{exp_id}.pkl"
        self.experiment.manifest_path = f"data/ingestion_manifest_{exp_id}.json"

        return self

# Single Source of Truth instantiated instance (The Singleton)
config = AppConfig()