"""
retrieval/search_fusion.py

Implements result parsing and fusion logic across retrievers.
"""

from config import config

from typing import Any, Dict, List
from ingestion.structures import ProcessedChunk
from telemetry import track, update_current_span

def parse_retrieval_results_to_chunks(results: Dict[str, Any]) -> List[ProcessedChunk]:
    """
    Parses standardized retrieval dictionary output (Chroma/BM25)
    into validated domain ProcessedChunk models.
    """
    if not results or not results.get("ids") or not results["ids"][0]:
        return []
    
    chunks: List[ProcessedChunk] = []

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    for chunk_id, doc, meta in zip(ids, documents, metadatas):
        chunk = ProcessedChunk(
            chunk_id=chunk_id,
            parent_page_id=meta.get("parent_page_id", ""),
            text_content=doc,
            chunk_index=int(meta.get("chunk_index", 0)),
            notebook_name=meta.get("notebook_name", ""),
            section_name=meta.get("section_name", ""),
            parent_page_title=meta.get("parent_page_title", ""),
            content_hash=meta.get("content_hash", "")
        )
        chunks.append(chunk)

    return chunks

@track(name="fuse_results")
def fuse_results(
        vector_results: Dict[str, Any],
        bm25_results: Dict[str, Any],
        top_k: int = 5
) -> List[ProcessedChunk]:
    """
    Fuses results from vector and BM25 retrievers.
    Phase 1: Concatenates top hits and deduplicates by chunk_id.
    """
    # Attach high-level metadata to the root trace
    update_current_span(
        {
            "fusion_method": config.retrieval.fusion_strategy,
            "vector_result_count": len(vector_results),
            "bm25_result_count": len(bm25_results),
        }
    )
    
    vector_chunks = parse_retrieval_results_to_chunks(vector_results)
    bm25_chunks = parse_retrieval_results_to_chunks(bm25_results)

    combined_chunks = vector_chunks + bm25_chunks

    seen_ids = set()
    fused_chunks: List[ProcessedChunk] = []

    for chunk in combined_chunks:
        if chunk.chunk_id not in seen_ids:
            seen_ids.add(chunk.chunk_id)
            fused_chunks.append(chunk)

    return fused_chunks[:top_k]
