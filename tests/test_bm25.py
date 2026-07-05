import pytest
from dotenv import load_dotenv 

# Absolute first step: Load environment strings into system memory 
# BEFORE initializing any internal config modules to prevent empty state overrides.
load_dotenv()

from retrieval.bm25_engine import BM25Engine
from ingestion.structures import ProcessedChunk


def create_mock_chunk(chunk_id: str, text: str, notebook: str, section: str) -> ProcessedChunk:
    """
    Helper method to construct structured data blocks quickly.
    """
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

def test_bm25_exact_keyword_matching_and_contract_shape():
    """
    Verifies standard interface format returns match the Structured Chroma dictionary layout.
    """
    engine = BM25Engine()

    chunk1 = create_mock_chunk("id_1", "The authorization variable is user_auth_token.", "Dev_Notes", "Security")
    chunk2 = create_mock_chunk("id_2", "Database parameters handle connections pool size.", "Dev_Notes", "DB")
    dummy1 = create_mock_chunk("id_d1", "Random unrelated note about team meetings.", "Dev_Notes", "General")
    dummy2 = create_mock_chunk("id_d2", "Project planning timelines and general schedule data.", "Dev_Notes", "General")
    engine.upsert_chunks([chunk1, chunk2, dummy1, dummy2])

    # Target search engine sequence triggering unique keyword exactness
    results = engine.search_similar_chunks(query_text="user_auth_token", top_k=1)

    # Assert structural alignment parameters
    assert "ids" in results
    assert "documents" in results
    assert "metadatas" in results
    assert "distances" in results

    # Confimrs exact keyword hit sorted to the absolute front
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "id_1"
    assert "user_auth_token" in results["documents"][0][0]
    assert results["metadatas"][0][0]["section_name"] == "Security"
    assert results["distances"][0][0] > 0.0

def test_metadata_isolation_and_access_control():
    """
    Validates that items belonging to other notebooks are filtered out before scoring.
    """
    engine = BM25Engine()

    allowed_chunk = create_mock_chunk("id_ok", "Critical error code found ERR_404.", "Public_Notebook", "Logs")
    secret_chunk = create_mock_chunk("id_secret", "Critical error code found ERR_404.", "Private_Notebook", "Logs")
    dummy1 = create_mock_chunk("id_d1", "Random unrelated note about team meetings.", "Public_Notebook", "General")
    dummy2 = create_mock_chunk("id_d2", "Project planning timelines and general schedule data.", "Public_Notebook", "General")

    engine.upsert_chunks([allowed_chunk, secret_chunk, dummy1, dummy2])

    # Execute query restricted to the safe workspace partition boundary
    results = engine.search_similar_chunks(
        query_text="ERR_404", 
        top_k=5, 
        filter_dict={"notebook_name": "Public_Notebook"}
    )

    # Verify that data isolation prevents secret_chunk from bleeding out
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "id_ok"
    assert secret_chunk.chunk_id not in results["ids"][0]

def test_idempotence_and_duplicate_upserts():
    """Confirms uploading identical chunk keys updates existing allocations rather than replicating records."""
    engine = BM25Engine()

    chunk = create_mock_chunk("dup_id", "Isolated trace criteria.", "Workspace", "General")
    dummy1 = create_mock_chunk("id_d1", "Random unrelated note about team meetings.", "Dev_Notes", "General")
    dummy2 = create_mock_chunk("id_d2", "Project planning timelines and general schedule data.", "Dev_Notes", "General")

    # Upsert the same block multiple times to simulate re-indexing
    engine.upsert_chunks([chunk])
    engine.upsert_chunks([chunk])
    engine.upsert_chunks([dummy1, dummy2])

    results = engine.search_similar_chunks(query_text="trace", top_k=10)

    # Ensure inner state array references only track single distinct entity mapping records
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "dup_id"

def test_empty_or_non_matching_query_graceful_fallbacks():
    """
    Asserts that zero term intersections resolve into clean empty arrays without runtime exceptions.
    """
    engine = BM25Engine()

    chunk = create_mock_chunk("id_x", "Standard production configurations layout.", "Workspace", "Config")
    dummy1 = create_mock_chunk("id_d1", "Random unrelated note about team meetings.", "Dev_Notes", "General")
    dummy2 = create_mock_chunk("id_d2", "Project planning timelines and general schedule data.", "Dev_Notes", "General")
    engine.upsert_chunks([chunk, dummy1, dummy2])

    results = engine.search_similar_chunks(query_text="unrelated_jargon_word", top_k=2)

    assert results["ids"] == [[]]
    assert results["documents"] == [[]]
    assert results["metadatas"] == [[]]
    assert results["distances"] == [[]]
