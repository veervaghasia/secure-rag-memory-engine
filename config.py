import os
from pydantic import BaseModel, Field, model_validator
from dotenv import load_dotenv

# Ensure env variables from .env are loaded into the process runtime
load_dotenv()

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
        default=120,
        description="Size of each text chunk."
    )
    chunk_overlap: int = Field(
        default=30,
        description="Overlap between consecutive text chunks."
    )

class VectorStoreConfig(BaseModel):
    collection_name: str = "onenote_knowledge_base"
    persist_directory: str = "data/chroma_db"
    embedding_model: str = "text-embedding-3-small"

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
    chunking: ChunkingConfig = ChunkingConfig()
    vector_store: VectorStoreConfig = VectorStoreConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    llm: LLMConfig = LLMConfig()
    telemetry: TelemetryConfig = TelemetryConfig()
    memory: MemoryConfig = MemoryConfig()

# Single Source of Truth instantiated instance (The Singleton)
config = AppConfig()