# This file contains:
# - classes for data objects used through the ingestion pipeline

# Do we want to use pydantic here? 
from pydantic import BaseModel
from typing import List, Optional


class RawOnenotePage(BaseModel):
    """Represents the initial file import before any splitting happens"""
    page_id: str  # unique identifier
    notebook_name: str
    section_name: str
    page_title: str
    text_content: str
    depth: int = 0  # 0 = main page, 1 = subpage, etc.
    parent_page_id: Optional[str] = None  # Tracks hierarchy for sub-pages


class ProcessedChunk(BaseModel):
    """Represents a single text slice, complete with the redundant metadata fields we need for ChromaDB filtering."""
    chunk_id: str  # unique identifier (Deterministic text content hash)
    parent_page_id: str  # Linking back to the source page
    text_content: str  # The raw text inside this specific chunk
    chunk_index: int  # the relative position (0, 1, 2, etc.) within the page

    # --- METADATA for VECTOR FILTERING ---
    notebook_name: str
    section_name: str
    parent_page_title: str
    content_hash: str  # alphanumeric text hash for explicit deduplication checks
    # Note: Phase 2 will add "hierarchy_path" here; eg: "Apartment_Hunting/Koramangala_Options/Broker_Contacts"


class IngestionPayload(BaseModel): 
    """Container grouping all processed chunks of a page along with  telemetry."""
    source_page_id: str  # unique identifier of the source page
    chunks: List[ProcessedChunk]  
    total_chunks: int  # number of chunks created from source page
    parsing_latency_ms: float  # time taken to parse the page into chunks; helps to track parsing latency for Opik
