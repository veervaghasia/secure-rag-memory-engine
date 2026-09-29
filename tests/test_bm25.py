import os
from unittest.mock import patch
import pytest
from dotenv import load_dotenv 

load_dotenv()

from retrieval.bm25_engine import BM25Engine
from ingestion.structures import ProcessedChunk


@pytest.fixture
def isolated_bm25_engine(tmp_path):
    """
    Fixture providing a clean BM25Engine instance operating entirely
    within a pytest temporary directory to prevent production index pollution.
    """
    test_index_path = str(tmp_path / "bm25_test_index.pkl")
    with patch("retrieval.bm25_engine.config.bm25.index_path", test_index_path):
        engine = BM25Engine()
        yield engine, test_index_path


def create_mock_chunk(chunk_id: str, text: str, notebook: str, section: str) -> ProcessedChunk:
    return ProcessedChunk(
        chunk_id=chunk_id,
        parent_page_id="page_123",
        text_content=text,
        chunk_index=0,
        notebook_name=notebook,
        section_name=section,
        parent_page_title="Testing Title",
        content_hash="hash_" + chunk_id
    )


def test_bm25_exact_keyword_matching_and_contract_shape(isolated_bm25_engine):
    engine, _ = isolated_bm25_engine

    chunk1 = create_mock_chunk("id_1", "The authorization variable is user_auth_token.", "Dev_Notes", "Security")
    chunk2 = create_mock_chunk("id_2", "Database parameters handle connections pool size.", "Dev_Notes", "DB")
    dummy1 = create_mock_chunk("id_d1", "Random unrelated note about team meetings.", "Dev_Notes", "General")
    dummy2 = create_mock_chunk("id_d2", "Project planning timelines and general schedule data.", "Dev_Notes", "General")
    engine.upsert_chunks([chunk1, chunk2, dummy1, dummy2])

    results = engine.search_similar_chunks(query_text="pool size", top_k=1)

    assert "ids" in results
    assert "documents" in results
    assert "metadatas" in results
    assert "distances" in results

    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "id_2"
    assert "pool size" in results["documents"][0][0]
    assert results["metadatas"][0][0]["section_name"] == "DB"
    assert results["distances"][0][0] > 0.0


def test_metadata_isolation_and_access_control(isolated_bm25_engine):
    engine, _ = isolated_bm25_engine

    allowed_chunk = create_mock_chunk("id_ok", "Critical error code found ERR_404.", "Public_Notebook", "Logs")
    secret_chunk = create_mock_chunk("id_secret", "Critical error code found ERR_404.", "Private_Notebook", "Logs")
    dummy1 = create_mock_chunk("id_d1", "Random unrelated note about team meetings.", "Public_Notebook", "General")
    dummy2 = create_mock_chunk("id_d2", "Project planning timelines and general schedule data.", "Public_Notebook", "General")

    engine.upsert_chunks([allowed_chunk, secret_chunk, dummy1, dummy2])

    results = engine.search_similar_chunks(
        query_text="ERR_404", 
        top_k=5, 
        filter_dict={"notebook_name": "Public_Notebook"}
    )

    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "id_ok"
    assert secret_chunk.chunk_id not in results["ids"][0]


def test_idempotence_and_duplicate_upserts(isolated_bm25_engine):
    engine, _ = isolated_bm25_engine

    chunk = create_mock_chunk("dup_id", "Isolated trace criteria.", "Workspace", "General")
    dummy1 = create_mock_chunk("id_d1", "Random unrelated note about team meetings.", "Dev_Notes", "General")
    dummy2 = create_mock_chunk("id_d2", "Project planning timelines and general schedule data.", "Dev_Notes", "General")

    engine.upsert_chunks([chunk])
    engine.upsert_chunks([chunk])
    engine.upsert_chunks([dummy1, dummy2])

    results = engine.search_similar_chunks(query_text="trace", top_k=10)

    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "dup_id"


def test_empty_or_non_matching_query_graceful_fallbacks(isolated_bm25_engine):
    engine, _ = isolated_bm25_engine

    chunk = create_mock_chunk("id_x", "Standard production configurations layout.", "Workspace", "Config")
    dummy1 = create_mock_chunk("id_d1", "Random unrelated note about team meetings.", "Dev_Notes", "General")
    dummy2 = create_mock_chunk("id_d2", "Project planning timelines and general schedule data.", "Dev_Notes", "General")
    engine.upsert_chunks([chunk, dummy1, dummy2])

    results = engine.search_similar_chunks(query_text="unrelated_jargon_word", top_k=2)

    assert results["ids"] == [[]]
    assert results["documents"] == [[]]
    assert results["metadatas"] == [[]]
    assert results["distances"] == [[]]


def test_bm25_reset_index_clears_memory_and_disk(isolated_bm25_engine):
    engine, test_index_path = isolated_bm25_engine

    chunk = create_mock_chunk("reset_id", "Reset test document text.", "Dev_Notes", "General")
    engine.upsert_chunks([chunk])

    assert len(engine.corpus_ids) == 1
    assert engine.bm25 is not None
    assert os.path.exists(test_index_path)

    engine.reset_index()

    assert len(engine.corpus_ids) == 0
    assert len(engine.chunks_dict) == 0
    assert engine.bm25 is None
    assert not os.path.exists(test_index_path)

    results = engine.search_similar_chunks(query_text="Reset", top_k=1)
    assert results["ids"] == [[]]


def test_bm25_corrupted_pickle_fallback(tmp_path):
    corrupt_file_path = str(tmp_path / "bm25_corrupt.pkl")

    with open(corrupt_file_path, "wb") as f:
        f.write(b"CORRUPTED_NON_PICKLE_BINARY_DATA_12345")

    with patch("retrieval.bm25_engine.config.bm25.index_path", corrupt_file_path):
        engine = BM25Engine()

        assert engine.corpus_ids == []
        assert engine.chunks_dict == {}
        assert engine.bm25 is None

def test_bm25_tokenization_preserves_underscores(isolated_bm25_engine):
    """
    Verify that _tokenize preserves technical constructs containing underscores
    while properly stripping standard punctuation (colons, exclamation marks).
    """
    engine, _ = isolated_bm25_engine

    # 1. Arrange: Create a chunk with punctuation and an underscore identifier
    text_content = "Error: check user_auth_token!"
    chunk1 = create_mock_chunk("id_1", "The authorization variable is user_auth_token.", "Dev_Notes", "Security")
    chunk2 = create_mock_chunk("id_2", "Database parameters handle connections pool size.", "Dev_Notes", "DB")
    dummy1 = create_mock_chunk("id_d1", "Random unrelated note about team meetings.", "Dev_Notes", "General")
    dummy2 = create_mock_chunk("id_d2", "Project planning timelines and general schedule data.", "Dev_Notes", "General")

    # 2. Act: Index the chunk using the expected List[ProcessedChunk]
    engine.upsert_chunks([chunk1, chunk2, dummy1, dummy2])

    # 3. Assert: Exact match query on the full identifier returns the chunk
    results = engine.search_similar_chunks(query_text="pool size", top_k=1)
    
    assert "ids" in results
    assert "documents" in results
    assert "metadatas" in results
    assert "distances" in results

    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "id_2"
    assert "pool size" in results["documents"][0][0]
    assert results["metadatas"][0][0]["section_name"] == "DB"
    assert results["distances"][0][0] > 0.0