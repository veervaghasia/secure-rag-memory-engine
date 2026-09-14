import hashlib
import pytest
from unittest.mock import patch, MagicMock

from ingestion.base_parser import FixedSizeChunker
from ingestion.structures import RawOnenotePage, IngestionPayload, ProcessedChunk
from config import config

# --- FIXTURES ---

@pytest.fixture
def mock_onenote_page():
    """Provides a standard RawOnenotePage object for chunking tests."""
    return RawOnenotePage(
        page_id="test-page-123",
        notebook_name="Engineering_Notes",
        section_name="Architecture",
        page_title="RAG_Pipelines",
        text_content="abcdefghijklmnopqrstuvwxyz",  # 26 characters
        depth=0,
        page_hash="page_hash_abc",
    )

@pytest.fixture
def empty_onenote_page():
    """Provides a RawOnenotePage object with empty text content."""
    return RawOnenotePage(
        page_id="empty-page-000",
        notebook_name="Engineering_Notes",
        section_name="Architecture",
        page_title="Empty_Page",
        text_content="",
        depth=0,
        page_hash="empty_hash",
    )

# --- UNIT TESTS ---

class TestFixedSizeChunkerInitialization:
    def test_default_initialization_uses_config(self):
        """Verify chunker falls back to global config defaults when arguments are omitted."""
        chunker = FixedSizeChunker()
        assert chunker.chunk_size == config.chunking.chunk_size
        assert chunker.chunk_overlap == config.chunking.chunk_overlap

    def test_custom_initialization_overrides_config(self):
        """Verify explicit initialization arguments override system config defaults."""
        chunker = FixedSizeChunker(chunk_size=50, chunk_overlap=10)
        assert chunker.chunk_size == 50
        assert chunker.chunk_overlap == 10

    def test_zero_overlap_initialization(self):
        """Verify explicit zero overlap is correctly respected instead of triggering fallback."""
        chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=0)
        assert chunker.chunk_overlap == 0


class TestFixedSizeChunkerHashing:
    def test_generate_deterministic_hash(self):
        """Verify SHA-256 hashing produces correct, stable output for given strings."""
        chunker = FixedSizeChunker()
        sample_text = "Self-Attention Mechanism"
        expected_hash = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()
        
        assert chunker._generate_deterministic_hash(sample_text) == expected_hash


class TestFixedSizeChunkerExecution:
    @patch("ingestion.base_parser.opik_context")
    def test_chunk_page_sliding_window(self, mock_opik_context, mock_onenote_page):
        """
        Verify sliding window logic, chunk indexes, metadata preservation,
        and hash invariants under normal operation.
        """
        # Text: 26 characters ("abcdefghijklmnopqrstuvwxyz")
        # chunk_size=10, overlap=2 => stride=8
        # Window 0: [0:10]   -> "abcdefghij" (index 0)
        # Window 1: [8:18]   -> "ijklmnopqr" (index 1)
        # Window 2: [16:26]  -> "qrstuvwxyz" (index 2)
        chunker = FixedSizeChunker(chunk_size=10, chunk_overlap=2)
        payload = chunker.chunk_page(mock_onenote_page)
        print(payload)

        assert isinstance(payload, IngestionPayload)
        assert payload.source_page_id == mock_onenote_page.page_id
        assert payload.total_chunks == 4
        assert len(payload.chunks) == 4
        assert payload.parsing_latency_ms >= 0.0

        # Validate chunk 0
        c0 = payload.chunks[0]
        assert c0.chunk_index == 0
        assert c0.text_content == "abcdefghij"
        assert c0.parent_page_id == mock_onenote_page.page_id
        assert c0.notebook_name == mock_onenote_page.notebook_name
        assert c0.section_name == mock_onenote_page.section_name
        assert c0.parent_page_title == mock_onenote_page.page_title
        assert c0.chunk_id == hashlib.sha256("abcdefghij".encode("utf-8")).hexdigest()

        # Validate chunk 1
        c1 = payload.chunks[1]
        assert c1.chunk_index == 1
        assert c1.text_content == "ijklmnopqr"

        # Validate chunk 2 (boundary edge end)
        c2 = payload.chunks[2]
        assert c2.chunk_index == 2
        assert c2.text_content == "qrstuvwxyz"

        # Validate chunk 3 (boundary edge end)
        c3 = payload.chunks[3]
        assert c3.chunk_index == 3
        assert c3.text_content == "yz"

        # Verify Opik trace update call
        mock_opik_context.update_current_trace.assert_called_once_with(
            metadata={"phase": config.telemetry.current_phase}
        )

    @patch("ingestion.base_parser.opik_context")
    def test_chunk_page_text_smaller_than_chunk_size(self, mock_opik_context, mock_onenote_page):
        """Verify handling when page text is shorter than the configured chunk_size."""
        chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=10)
        payload = chunker.chunk_page(mock_onenote_page)

        assert payload.total_chunks == 1
        assert len(payload.chunks) == 1
        assert payload.chunks[0].text_content == mock_onenote_page.text_content
        assert payload.chunks[0].chunk_index == 0

    @patch("ingestion.base_parser.opik_context")
    def test_chunk_page_empty_text(self, mock_opik_context, empty_onenote_page):
        """Verify early exit guard rail when processing empty text content."""
        chunker = FixedSizeChunker(chunk_size=10, chunk_overlap=2)
        payload = chunker.chunk_page(empty_onenote_page)

        assert payload.source_page_id == empty_onenote_page.page_id
        assert payload.total_chunks == 0
        assert payload.chunks == []
        assert payload.parsing_latency_ms >= 0.0

    @patch("ingestion.base_parser.opik_context")
    def test_chunk_page_invalid_stride(self, mock_opik_context, mock_onenote_page):
        """Verify guard rail triggers when overlap is greater than or equal to chunk size (stride <= 0)."""
        # overlap >= chunk_size causes stride <= 0
        chunker = FixedSizeChunker(chunk_size=10, chunk_overlap=10)
        payload = chunker.chunk_page(mock_onenote_page)

        assert payload.total_chunks == 0
        assert payload.chunks == []