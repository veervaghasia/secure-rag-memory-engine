import os
from pydantic import BaseModel, model_validator
from dotenv import load_dotenv

# Ensure env variables from .env are loaded into the process runtime
load_dotenv()

class ChunkingConfig(BaseModel):
    chunk_size: int = 120
    chunk_overlap: int = 30

class VectorStoreConfig(BaseModel):
    collection_name: str = "retrieval_baseline"
    embedding_model: str = "text-embedding-3-small"

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
    telemetry: TelemetryConfig = TelemetryConfig()

# Single Source of Truth instantiated instance (The Singleton)
config = AppConfig()