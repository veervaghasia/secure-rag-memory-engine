import json
import os
import pytest
from unittest.mock import patch, MagicMock

from ingestion.docx_parser import SecureDocxParser
from ingestion.structures import RawOnenotePage

# --- FIXTURES ---

@pytest.fixture
def tmp_manifest_path(tmp_path):
    """
    Provides a temporary manifest file path for testing persistence without polluting disk.
    """
    return str(tmp_path / "test_manifest.json")

@pytest.fixture
def parser(tmp_manifest_path):
    """
    Initializes a SecureDocxParser pointing to a temporary manifest location.
    """
    return SecureDocxParser(manifest_path=tmp_manifest_path)


# --- UNIT TESTS ---

class TestSecretRedaction:
    def test_sanitize_text_redacts_known_secrets(self, parser):
        """Verifies that API keys and credential strings are replaced with REDACTED_SECRET."""
        sample_text = (
            "OpenAI: sk-1234567890abcdef1234567890abcdef1234567890abcdef\n"
            "Gemini: AIzaSy1234567890abcdef1234567890abcdef1\n"
            "HF: hf_1234567890abcdef1234567890abcdef123\n"
            "Generic: api_key='secret_key_1234567890'"
        )
        sanitized = parser._sanitize_text(sample_text)

        assert "sk-1234567890" not in sanitized
        assert "AIzaSy" not in sanitized
        assert "hf_" not in sanitized
        assert "REDACTED_SECRET" in sanitized 
        assert sanitized.count("REDACTED_SECRET") == 4

    def test_sanitize_text_preserves_standard_text_and_urls(self, parser):
        """
        Verify normal text and standard HTTP links remain uncorrupted.
        """
        normal_text = "Check the docs at https://docs.python.org/3/library/re.html for details."
        sanitized = parser._sanitize_text(normal_text)

        assert sanitized == normal_text


class TestManifestManagement:
    def test_load_manifest_nonexistant_returns_empty_dict(self, tmp_manifest_path):
        """
        Verify loading a missing manifest returns an empty dictionary gracefully.
        """
        parser = SecureDocxParser(manifest_path=tmp_manifest_path)
        assert parser.manifest == {}

    def test_save_and_load_manifest(self, parser, tmp_manifest_path):
        """
        Verify manifest changes are written to disk and can be reloaded.
        """
        parser.manifest = {"file1.docx": {"last_modified": 123456, "pages_count": 2}}
        parser._save_manifest()

        assert os.path.exists(tmp_manifest_path)
        with open(tmp_manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["file1.docx"]["last_modified"] == 123456

    def test_clear_manifest_cache(self, parser, tmp_manifest_path):
        """
        Verify clear_manifest_cache purges in-memory state and removes disk file.
        """
        parser.manifest = {"cached": True}
        parser._save_manifest()
        assert os.path.exists(tmp_manifest_path)

        result = parser.clear_manifest_cache()
        assert result is True
        assert parser.manifest == {}
        assert not os.path.exists(tmp_manifest_path)

    def test_clear_anifest_cache_when_no_file_exists(self, parser, tmp_manifest_path):
        """
        Verify clearing cache when no file exists executes without raising exceptions.
        """
        result = parser.clear_manifest_cache()
        assert result is True
        assert parser.manifest == {}


class TestDocxParsing:
    def test_parse_section_file_not_found_raises_exception(self, parser):
        """
        Verify FileNotFoundError is raised when target document path does not exist.
        """
        with pytest.raises(FileNotFoundError):
            parser.parse_section_into_pages("non_existent.docx", "Notebook", "Section")


    @patch("ingestion.docx_parser.Document")
    @patch("ingestion.docx_parser.opik_context")
    def test_parse_section_lookahead_page_splitting(self, mock_opik_context, mock_docx, parser, tmp_path):
        """Verify page splitting occurs when title + Date + Time lookahead pattern is matched."""
        dummy_file = str(tmp_path / "test.docx")
        with open(dummy_file, "w") as f:
            f.write("mock")

        # Mock document paragraph structure:
        # Page 1: Default Intro lines
        # Page 2: "New Topic" (title) + "28 May 2024" (date) + "04:58" (time) + content
        mock_p1 = MagicMock(text="Introduction content line.")
        mock_p2 = MagicMock(text="New Topic")
        mock_p3 = MagicMock(text="28 May 2024")
        mock_p4 = MagicMock(text="04:58")
        mock_p5 = MagicMock(text="Detailed notes inside new topic.")

        mock_doc_instance = MagicMock()
        mock_doc_instance.paragraphs = [mock_p1, mock_p2, mock_p3, mock_p4, mock_p5]
        mock_docx.return_value = mock_doc_instance

        pages = parser.parse_section_into_pages(dummy_file, "AI_Studies", "Transformers")

        assert len(pages) == 2
        assert pages[0].page_title == "Transformers - Introduction"
        assert "Introduction content line." in pages[0].text_content

        assert pages[1].page_title == "New Topic"
        assert "Detailed notes inside new topic." in pages[1].text_content


class TestDirectoryScanning:
    @patch.object(SecureDocxParser, "parse_section_into_pages")
    def test_scan_directory_skips_lockfiles_and_caches_hits(self, mock_parse, parser, tmp_path):
        """Verify scan_directory filters lockfiles (~$), parses valid docx files, and skips unchanged cached files."""
        # Setup temporary folder structure
        doc1 = tmp_path / "Section1.docx"
        lockfile = tmp_path / "~$Section1.docx"
        txtfile = tmp_path / "notes.txt"

        doc1.write_text("data")
        lockfile.write_text("lock")
        txtfile.write_text("text")

        mock_page = RawOnenotePage(
            page_id="p1",
            notebook_name="Default",
            section_name="Section1",
            page_title="Title",
            text_content="Content",
            page_hash="hash1",
            depth=0
        )
        mock_parse.return_value = [mock_page]

        # First scan: processes Section1.docx, ignores lockfile & textfile
        pages_run1 = parser.scan_directory(str(tmp_path))
        assert len(pages_run1) == 1
        assert mock_parse.call_count == 1

        # Second scan: file hasn't changed, should hit cache and skip re-parsing
        mock_parse.reset_mock()
        pages_run2 = parser.scan_directory(str(tmp_path))
        assert len(pages_run2) == 0
        assert mock_parse.call_count == 0