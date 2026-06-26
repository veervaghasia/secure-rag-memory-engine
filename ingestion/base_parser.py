import hashlib  # to import cryptographic fns to calculate the hash of a chunk
import time  # to track latency of the ingestion process
from typing import List  
from ingestion.structures import RawOnenotePage, ProcessedChunk, IngestionPayload
from config import config
from opik import opik_context, track

class FixedSizeChunker:
    """Splits a given text into fixed-size chunks of a specified size."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """Initialize the chunker with specific execution parameters."""
        self.chunk_size = chunk_size or config.chunking.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunking.chunk_overlap

    def _generate_deterministic_hash(self, text: str) -> str:
        """Generates a stable SHA-256 hex string for deduplication."""
        # hashlib requires byte streams, so we encode the python string to utf-8 first
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    @track(project_name="secure-rag-memory-engine")
    def chunk_page(self, page: RawOnenotePage) -> IngestionPayload:
        """Slices a RawOnenotePage into fixed-character ProcessedChunks with metadata."""
        # Update the current trace metadata cleanly using the context module
        opik_context.update_current_trace(metadata={
            "phase": config.telemetry.current_phase
        })
        
        start_time = time.time()  # Start the stopwatch for telemetry

        text = page.text_content
        chunks_list: List[ProcessedChunk] = []

        start_index = 0
        chunk_sequence_counter = 0
        stride = self.chunk_size - self.chunk_overlap

        # Ensure we don't spin up an infinite loop if text is empty or configs are corrupted
        if not text or stride <= 0:
            execution_time_ms = (time.time() - start_time) * 1000
            return IngestionPayload(
                source_page_id=page.page_id,
                chunks=[],
                total_chunks=0,
                parsing_latency_ms=execution_time_ms
            )
        
        # Loop until our sliding window pointer passes the total character length
        while start_index < len(text):
            # Calculate the safe oundry using our min() guard rail
            end_index = min(start_index + self.chunk_size, len(text))

            # Slice the target chunk string
            chunk_text = text[start_index:end_index]

            # Generate the immutable SHA-256 ID
            content_sha = self._generate_deterministic_hash(chunk_text)

            # COnstruct our pydantic object wrapping database-level metadata
            processed_chunk = ProcessedChunk(
                chunk_id = content_sha,
                parent_page_id=page.page_id,
                text_content=chunk_text,
                chunk_index=chunk_sequence_counter,
                notebook_name=page.notebook_name,
                section_name=page.section_name,
                parent_page_title=page.page_title,
                content_hash=content_sha
            )

            chunks_list.append(processed_chunk)

            # --- CRITICAL SLIDING ENGINE STATE UPDATES ---
            start_index += stride  # Shift the sliding window forward by stride distance
            chunk_sequence_counter += 1  # Advance our structural sequence tracker

        # Stop the stopwatch
        execution_time_ms = (time.time() - start_time) * 1000

        # Package the whole batch operation together
        return IngestionPayload(
            source_page_id=page.page_id,
            chunks=chunks_list, 
            total_chunks=len(chunks_list),
            parsing_latency_ms=execution_time_ms
        )