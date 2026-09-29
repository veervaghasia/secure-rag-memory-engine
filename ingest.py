"""
ingest.py

Data ingestion pipeline entry point. Parses raw document files, splits
text into chunks, populates ChromaDB and BM25 search indices, and
tracks experiment metadata.
"""

import os
import argparse
from typing import List
from config import config
# from collections import Counter
from ingestion.experiment_registry import register_experiment, update_experiment_status
from ingestion.docx_parser import SecureDocxParser
from ingestion.base_parser import FixedSizeChunker
from ingestion.structures import ProcessedChunk
from retrieval.vector_store import ChromaVectorEngine
from retrieval.bm25_engine import BM25Engine
from telemetry import track, update_current_trace

def reset_experiment_pipeline():
    """
    Resets all persistent artifacts belonging to the active experiment.
    This does not delete or alter the experiment registry entry.

    Executes a 3-step reset sequence for the active experiment:
    1. Removes the manifest cache file.
    2. Resets/deletes the ChromaDB collection.
    3. Resets/deletes the BM25 index pickle file.
    """    
    exp_id = config.experiment.experiment_id
    manifest_path = config.experiment.manifest_path

    print(f"\n🔄 [Reset Pipeline] Commencing reset sequence for experiment: '{exp_id}'...")

    # Step 1: Remove experiment-speccific manifest cache if present
    if os.path.exists(manifest_path):
        try:
            os.remove(manifest_path)
            print(f"🗑️ [Reset] Removed manifest cache at '{manifest_path}'.")
        except Exception as e:
            print(f"⚠️ [Reset] Failed to remove manifest cache at '{manifest_path}': {e}")
    else:
        print(f"ℹ️ [Reset] No manifest cache found at '{manifest_path}'. Skipping.")

    # Step 2: Reset Vector Store Collection
    vector_engine = ChromaVectorEngine()
    vector_engine.reset_store()

    # Step 3: Reset Bm25 Index File
    bm25_engine = BM25Engine()
    bm25_engine.reset_index() 

    print(f"✅ [Reset Pipeline] Experiment artifacts for '{exp_id}' have been reset.\n")

@track(name="run_ingestion")
def run_ingestion(data_directory: str = os.path.join("data", "onenote_exports"), description: str = ""):
    """
    Runs the document parsing and chunking pipeline, 
    upserts to storage engines, and
    registers experiment metadata.
    """
    # Attach high-level metadata to the root trace
    update_current_trace(
        metadata = {
            "pipeline": "run_rag_pipeline",
        }
    )
    
    print(f"🚀 [Ingestion] Starting ingestion for experiment '{config.experiment.experiment_id}'...")

    # 1. Initialize components
    parser = SecureDocxParser()
    chunker = FixedSizeChunker()

    vector_engine = ChromaVectorEngine()
    bm25_engine = BM25Engine()

    # 2. Scan and parse document directory
    print(f"📂 [Ingestion] Scanning directory: '{data_directory}'...")
    raw_pages = parser.scan_directory(data_directory)

    if not raw_pages:
        print("ℹ️ [Ingestion] No new or modified documents found to process, or directory empty.")
        return

    print(f"📄 Extracted {len(raw_pages)} raw pages across sections.")

    # 3. Chunk raw pages into ProcessedChunk objects
    all_chunks: List[ProcessedChunk] = []
    for page in raw_pages:
        payload = chunker.chunk_page(page)
        all_chunks.extend(payload.chunks)

    if not all_chunks:
        print("⚠️ [Ingestion] Processing produced 0 chunks. Ingestion aborted.")
        return

    # Temp code to check duplicates: starts
    # chunk_ids = [chunk.chunk_id for chunk in all_chunks]

    # duplicate_ids = {
    #     id: count
    #     for id, count in Counter(chunk_ids).items()
    #     if count > 1
    # }

    # print(f"Total chunks: {len(chunk_ids)}")
    # print(f"Unique chunk IDs: {len(set(chunk_ids))}")
    # print(f"Duplicate IDs: {len(duplicate_ids)}")

    # for id, count in list(duplicate_ids.items())[:10]:
    #     print(f"\nDuplicate ID: {id} ({count} occurrences)")

    #     matching_chunks = [
    #         chunk for chunk in all_chunks
    #         if chunk.chunk_id == id
    #     ]

    #     for chunk in matching_chunks:
    #         print(
    #             f"section_name={chunk.section_name}",
    #             f"parent_page_id={chunk.parent_page_id},"
    #             f"parent_page_title={chunk.parent_page_title}, "
    #             f"chunk_index={chunk.chunk_index}"
    #         )
    # Temp code: ends

    print(f"✂️ [Ingestion] Generated {len(all_chunks)} ProcessedChunks across all pages.")

    # 4. Upsert into Presistent ChromaDB and BM25 Index
    v_count = vector_engine.upsert_chunks(all_chunks)
    print(f"✅ [Ingestion] Vector Store upsert complete: {v_count} vectors committed to ChromaDB ({config.vector_store.collection_name}).")

    b_count = bm25_engine.upsert_chunks(all_chunks)
    print(f"✅ [Ingestion] BM25 Index upsert complete: {b_count} records committed at Index Path ({config.bm25.index_path}).")

    print(f"\n🎉 [Ingestion] Ingestion pipeline finished successfully for '{config.experiment.experiment_id}'.\n")

def main():
    parser = argparse.ArgumentParser(description="Secure RAG Memory Engine - Document Ingestion Pipeline")
    parser.add_argument(
        "--experiment_id",
        type=str,
        default=config.experiment.experiment_id,
        help="Unique identifier tag for this experiment run (e.g. 'v1_chunk120)."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="If flag is set, deletes existing Chroma collection, BM25 pickle, and manifest cache before ingesting."
    )
    parser.add_argument(
        "--description",
        type=str,
        default="",
        help="Optional note or comment describing the purpose of this experiment."
    )
    parser.add_argument(
        "--docs_dir",
        type=str,
        default="data/onenote_exports",
        help="Path to folder containing source .docx documents."
    )

    args = parser.parse_args()

    # Synchronize AppConfig dynamic paths with the CLI experiment_id
    config.experiment.experiment_id = args.experiment_id
    config.synchronize_experiment_paths()

    # Register expeirment
    register_experiment(description=args.description)

    # Execute reset sequence if requested
    if args.reset:
        reset_experiment_pipeline()

    # Execute main ingestion pass
    run_ingestion(data_directory=args.docs_dir, description=args.description)


if __name__ == "__main__":
    main()


