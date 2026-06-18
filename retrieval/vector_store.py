from typing import List
import chromadb
from litellm import embedding
from ingestion.structures import ProcessedChunk

class ChromaVectorEngine:
    def __init__(self, collection_name: str = "retrieval_baseline"):
        """Initialize an ephemeral, high-speed in-memory ChromaDB client"""
        # Ephemeral means that the data will not persist after the program ends
        # Using EphemeralCLient ensures no database state files are written to disk during testing
        self.client = chromadb.EphemeralClient()

        # We specify our embedding model standard for Phase 1
        self.embedding_model = "text-embedding-3-small"

        # Create or fetch our target storage collection
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def _compute_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Invokes LiteLLM to convert a batch of strings into fixed-dimension vectors."""
        # LiteLLM normalizes different API payloads into a isngle standard call format
        response = embedding(
            model=self.embedding_model,
            input=texts
        )
        # Extract the raw float arrays from the standardized response payload
        return [item["embedding"] for item in response["data"]]
    
    def upsert_chunks(self, chunks: List[ProcessedChunk]) -> int:
        """Transforms ProcessedChunks into vectors and securely upserts them into ChromaDB."""
        if not chunks:
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

    def search_similar_chunks(self, query_text: str, top_k: int = 3, filter_dict: dict = None) -> list:
        """Embeds a raw query string and fetches the top_k most similar matching document chunks."""
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