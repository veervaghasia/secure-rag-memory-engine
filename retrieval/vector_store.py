from typing import List, Optional
from config import config 
import chromadb
import litellm
from litellm import embedding
from ingestion.structures import ProcessedChunk
from telemetry import track, update_current_span, get_litellm_metadata

class ChromaVectorEngine:
    def __init__(self):
        """Initialize an persistent ChromaDB client pointing at local storage."""
        # Switched from EphemeralClient to PersistentClient
        self.client = chromadb.PersistentClient(path=config.vector_store.persist_directory)

        # We specify our embedding model standard for Phase 1 by dynamically pulling it form Pydantic AppConfig instance
        self.embedding_model = config.vector_store.embedding_model

        # We specify the collection name by also pulling it from AppConfig
        self.collection_name = config.vector_store.collection_name

        # Create or fetch our target storage collection
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def reset_store(self) -> None:
        """
        Deletes the underlying Chroma collection from disk and
        re-instantiates an empty collection.
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"🗑️ [VectorEngine] Successfully deleted Chroma collection '{self.collection_name}'.")
        except Exception as e:
            print(f"⚠️ [VectorEngine] Note during collection reset for '{self.collection_name}': {e}")

        # Re-create empty collection handle
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        print(f"✅ [VectorEngine] Re-initialized empty collection '{self.collection_name}'.")

    @track(name="_compute_embeddings_batch", capture_input=False, capture_output=False)
    def _compute_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Invokes LiteLLM to convert strings into fixed-dimension vectors in chunks
        defined by config.vector_store.embedding_batch_size to satisfy API token limits.
        """
        # Attach high-level metadata to the root trace
        update_current_span(
            {
                "embedding_model": config.vector_store.embedding_model,
                "batch_size": config.vector_store.embedding_batch_size,
            }
        )
        
        if not texts:
            return []

        batch_size= config.vector_store.embedding_batch_size
        all_embeddings: List[List[float]] = []

        # Iterate over text list in slices of `batch_size`
        for i in range(0, len(texts), batch_size):
            text_batch = texts[i : i + batch_size]

            # LiteLLM normalizes different API payloads into a isngle standard call format
            llm_kwargs = {
                "model": config.vector_store.embedding_model,
                "input": text_batch,
            }

            llm_kwargs.update(
                get_litellm_metadata()
            )

            response = litellm.embedding(**llm_kwargs)

            # Extract embedings for the current batch and extend output list
            batch_vectors = [item["embedding"] for item in response["data"]]
            all_embeddings.extend(batch_vectors)

        # Extract the raw float arrays from the standardized response payload
        return all_embeddings
    
    # Potential runtime boot order issue
    @track(name="vector_upsert_chunks", capture_input=False)
    def upsert_chunks(self, chunks: List[ProcessedChunk]) -> int:
        """Transforms ProcessedChunks into vectors and securely upserts them into ChromaDB."""
        # Attach high-level metadata to the root trace
        update_current_span(
            {
                "engine": "ChromaVectorEngine",
                "collection": config.vector_store.collection_name,
                "chunk_count": len(chunks),
            }
        )
        
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
        print(f"🔢 [VectorEngine] Requesting vectors from LiteLLM ({self.embedding_model}) for {len(chunk_texts)} inputs...")
        computed_vectors = self._compute_embeddings_batch(chunk_texts)

        # Chroma has its own maximum batch size, which is independent
        # of the embedding API batch size.
        upsert_batch_size = config.vector_store.chroma_upsert_batch_size

        for start in range(0, len(chunk_ids), upsert_batch_size):
            end = start + upsert_batch_size

            # Write into the vector storage layer
            self.collection.upsert(
                ids=chunk_ids[start:end],
                embeddings=computed_vectors[start:end],
                documents=chunk_texts[start:end],
                metadatas=chunk_metadatas[start:end],
            )

        return len(chunk_ids)

    @track(name="vector_search_similar_chunks")
    def search_similar_chunks(self, query_text: str, top_k: Optional[int] = None, filter_dict: dict = None) -> dict:
        """Embeds a raw query string and fetches the top_k most similar matching document chunks."""
        # Attach high-level metadata to the root trace
        update_current_span(
            {
                "engine": "ChromaVectorEngine",
                "collection": config.vector_store.collection_name,
                "embedding_model": config.vector_store.embedding_model,
                "top_k": top_k,
                "has_filter": filter_dict is not None
            }
        )        

        top_k = top_k or config.retrieval.top_k
        
        # Check the incoming query is not an empty string
        if not query_text.strip():
            print("⚠️ [VectorEngine] Search aborted: The provided query text is empty.")
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

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