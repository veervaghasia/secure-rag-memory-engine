import pytest
from unittest.mock import patch
from ingestion.structures import ProcessedChunk
from retrieval.vector_store import ChromaVectorEngine
from retrieval.bm25_engine import BM25Engine

@pytest.fixture
def list_of_dummy_chunks():
    return [
        ProcessedChunk(
        chunk_id="test_chunk_001",
        parent_page_id="test_page_001",
        text_content="SQLite, ChromaDB, and BM25 must preserve state across process reboots.",
        chunk_index=0,
        notebook_name="Test Notebook",
        section_name="Test Section",
        parent_page_title="Persistence Page",
        content_hash="hash_12345"
        ),
        ProcessedChunk(
        chunk_id="test_chunk_002",
        parent_page_id="test_page_001",
        text_content="SQLite is used to persist sessions and its corrosponding messages.",
        chunk_index=1,
        notebook_name="Test Notebook",
        section_name="Test Section",
        parent_page_title="Persistence Page",
        content_hash="hash_12346"
        ),
        ProcessedChunk(
        chunk_id="test_chunk_003",
        parent_page_id="test_page_001",
        text_content="We are using a DTO to store the data in a structured format in SQLite.",
        chunk_index=2,
        notebook_name="Test Notebook",
        section_name="Test Section",
        parent_page_title="Persistence Page",
        content_hash="hash_12347"
        )
    ]

def test_chroma_persistence_across_reboots(tmp_path, list_of_dummy_chunks):
    test_db_dir = str(tmp_path / "chroma_db")

    # Mock config path to point to pytest's temporary folder
    with patch("retrieval.vector_store.config.vector_store.persist_directory", test_db_dir):
        # 1. Session A: Insert data into Chroma
        engine_a = ChromaVectorEngine()
        
        # Mock embedding API call to avoid live API hits in unit tests
        with patch.object(engine_a, "_compute_embeddings_batch", return_value=[[0.1] * 1536]*3):
            engine_a.upsert_chunks(list_of_dummy_chunks)

        # Force instance cleanup
        del engine_a

        # 2. Session B: Instantiate a completely new client pointing to the same disk path
        engine_b = ChromaVectorEngine()
        
        with patch.object(engine_b, "_compute_embeddings_batch", return_value=[[0.1] * 1536]):
            results = engine_b.search_similar_chunks(query_text="preserve state", top_k=3)

        # 3. Assert data survived
        retrieved_ids = results["ids"][0]
        assert len(retrieved_ids) == 3
        
        # Check presence via sets to avoid tie-breaker ordering issues
        expected_ids = {"test_chunk_001", "test_chunk_002", "test_chunk_003"}
        assert set(retrieved_ids) == expected_ids


def test_bm25_persistence_across_reboots(tmp_path, list_of_dummy_chunks):
    test_bm25_file = str(tmp_path / "bm25_index.pkl")

    with patch("retrieval.bm25_engine.config.bm25.index_path", test_bm25_file):
        # 1. Session A: Insert & Save to disk
        engine_a = BM25Engine()
        engine_a.upsert_chunks(list_of_dummy_chunks)
        del engine_a

        # 2. Session B: Re-instantiate (should auto-load from pickle)
        engine_b = BM25Engine()
        results = engine_b.search_similar_chunks(query_text="SQLite", top_k=3)

        # 3. Assert data survived
        retrieved_ids = results["ids"][0]
        assert len(retrieved_ids) == 3
        
        expected_ids = {"test_chunk_001", "test_chunk_002", "test_chunk_003"}
        assert set(retrieved_ids) == expected_ids