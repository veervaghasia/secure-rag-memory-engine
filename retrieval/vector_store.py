from typing import List
import chromadb
import litellm
from litellm import embedding
from litellm.integrations.opik.opik import OpikLogger
from ingestion.structures import ProcessedChunk
from config import config 
from opik import opik_context, track
from opik.opik_context import get_current_span_data 

# Initialize the dedicated logger and pass it to LiteLLM's callback collection
opik_logger = OpikLogger()
litellm.callbacks = [opik_logger]

class ChromaVectorEngine:
    def __init__(self):
        """Initialize an ephemeral, high-speed in-memory ChromaDB client"""
        # Ephemeral means that the data will not persist after the program ends
        # Using EphemeralCLient ensures no database state files are written to disk during testing
        self.client = chromadb.EphemeralClient()

        # We specify our embedding model standard for Phase 1 by dynamically pulling it form Pydantic AppConfig instance
        self.embedding_model = config.vector_store.embedding_model

        # We specify the collection name by allso pulling it from AppConfig
        self.collection_name = config.vector_store.collection_name

        # Create or fetch our target storage collection
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    @track(project_name="secure-rag-memory-engine")
    def _compute_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Invokes LiteLLM to convert a batch of strings into fixed-dimension vectors."""
        # LiteLLM normalizes different API payloads into a isngle standard call format
        response = embedding(
            model=self.embedding_model,
            input=texts,
            metadata={
                "opik": {
                    "current_span_data": get_current_span_data()
                }
            }
        )
        # Extract the raw float arrays from the standardized response payload
        return [item["embedding"] for item in response["data"]]
    
    # @opik.track(tags=[config.telemetry.current_phase]) 
    # Potential runtime boot order issue
    @track(project_name="secure-rag-memory-engine")
    def upsert_chunks(self, chunks: List[ProcessedChunk]) -> int:
        """Transforms ProcessedChunks into vectors and securely upserts them into ChromaDB."""
        # Update the current trace metadata cleanly using the context module
        opik_context.update_current_trace(metadata={
            "phase": config.telemetry.current_phase
        })
        
        if not chunks or len(chunks) == 0:
            print("[VectorEngine] Upsert aborted: The provided chunk list is completely empty.")
            return 0
        
        # Unzip our clean Pydantic object properties into separate parallel lists
        chunk_ids = [c.chunk_id for c in chunks]
        chunk_texts = [c.text_content for c in chunks]

        # Double check: did any text contents actually extract?
        if not chunk_texts or len(chunk_texts) == 0:
            print("⚠️ [VectorEngine] Upsert aborted: Extracted text content list is empty.")
            return 0

        # Build structured dictionaries for metadata filtering operations later
        chunk_metadatas = [
            {
                "parent_page_id": c.parent_page_id,
                "notebook_name": c.notebook_name,
                "section_name": c.section_name,
                "parent_page_title": c.parent_page_title,
                "chunk_index": c.chunk_index 
            }
            for c in chunks
        ]

        # Compute the uniform numerical representations
        print(f"Requesting vectors from LiteLLM ({self.embedding_model}) for {len(chunk_texts)} inputs...")
        computed_vectors = self._compute_embeddings_batch(chunk_texts)

        # Write into the vector storage layer
        self.collection.add(
            ids=chunk_ids,
            embeddings=computed_vectors,
            documents=chunk_texts,
            metadatas=chunk_metadatas
        )

        return len(chunk_ids)
    
    @track(project_name="secure-rag-memory-engine")
    def search_similar_chunks(self, query_text: str, top_k: int = 3, filter_dict: dict = None) -> dict:
        """Embeds a raw query string and fetches the top_k most similar matching document chunks."""
        # Update the current trace metadata cleanly using the context module
        opik_context.update_current_trace(metadata={
            "phase": config.telemetry.current_phase
        })
        
        # Check the incoming query is not an empty string
        if not query_text.strip():
            print("⚠️ [VectorEngine] Search aborted: The provided query text is empty.")
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

        # Transform the user's plain text query into the exact same vector space
        print(f"Generating vector embedding for query: '{query_text}'...")
        query_vector = self._compute_embeddings_batch([query_text])[0]

        # Query the underlying ChromaDB collection using its native search method
        print(f"Traversing HNSW graph for top {top_k} nearest neighbors...")
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=filter_dict  # This handles our metadata scoping
        )
        return results