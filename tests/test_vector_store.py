from unittest.mock import patch
import pytest
from dotenv import load_dotenv

load_dotenv()

from retrieval.vector_store import ChromaVectorEngine
from ingestion.structures import ProcessedChunk


@pytest.fixture
def isolated_vector_engine(tmp_path):
    """
    Fixture providing a ChromaVectorEngine sandboxed inside pytest's tmp_path.
    Embeddings are mocked to avoid live API hits during unit tests.
    """
    test_db_dir = str(tmp_path / "chroma_db")
    with patch("retrieval.vector_store.config.vector_store.persist_directory", test_db_dir):
        engine = ChromaVectorEngine()
        # Mock embeddings to return 1536-dim vector of constant values
        with patch.object(engine, "_compute_embeddings_batch", side_effect=lambda texts: [[0.1] * 1536 for _ in texts]):
            yield engine


def create_mock_chunk(chunk_id: str, text: str, notebook: str, section: str) -> ProcessedChunk:
    return ProcessedChunk(
        chunk_id=chunk_id,
        parent_page_id="page_123",
        text_content=text,
        chunk_index=0,
        notebook_name=notebook,
        section_name=section,
        parent_page_title="Testing Vector Store",
        content_hash="hash_" + chunk_id
    )


def test_vector_store_upsert_and_contract_shape(isolated_vector_engine):
    engine = isolated_vector_engine
    chunk = create_mock_chunk("vec_1", "Transformer multi-head attention mechanism.", "AI_Studies", "Transformers")
    
    upserted_count = engine.upsert_chunks([chunk])
    assert upserted_count == 1

    results = engine.search_similar_chunks(query_text="attention mechanism", top_k=1)

    assert "ids" in results
    assert "documents" in results
    assert "metadatas" in results
    assert "distances" in results
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "vec_1"


def test_vector_store_empty_query_fallback(isolated_vector_engine):
    engine = isolated_vector_engine
    
    results = engine.search_similar_chunks(query_text="   ", top_k=1)
    
    # Contract shape verification
    assert results["ids"] == [[]]
    assert results["documents"] == [[]]
    assert results["metadatas"] == [[]]
    assert results["distances"] == [[]]


def test_vector_store_metadata_filtering(isolated_vector_engine):
    engine = isolated_vector_engine
    chunk_a = create_mock_chunk("id_a", "Public data context.", "Public_NB", "General")
    chunk_b = create_mock_chunk("id_b", "Private data context.", "Private_NB", "General")

    engine.upsert_chunks([chunk_a, chunk_b])

    results = engine.search_similar_chunks(
        query_text="context",
        top_k=5,
        filter_dict={"notebook_name": "Public_NB"}
    )

    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "id_a"


def test_vector_store_reset(isolated_vector_engine):
    engine = isolated_vector_engine
    chunk = create_mock_chunk("id_reset", "Temporary payload.", "Test_NB", "General")
    engine.upsert_chunks([chunk])

    assert engine.collection.count() == 1

    engine.reset_store()

    assert engine.collection.count() == 0