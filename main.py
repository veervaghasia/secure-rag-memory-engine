from ingestion.structures import RawOnenotePage
from ingestion.base_parser import FixedSizeChunker
import opik
from config import config
import os
from dotenv import load_dotenv

load_dotenv()

def run_integration_test():
    print("=" * 60)
    print("INITIALIZING SECURE RAG ENGINE: PHASE 1 INTEGRATION TEST")
    print("=" * 60)

    # Using a simulated slice of our mock study and project notes
    mock_page = RawOnenotePage(
        page_id="dl-course-04a", 
        notebook_name="AI_Studies",
        section_name="Deeplearning_AI",
        page_title="Transformer_Mechanics",
        text_content=(
            "### Self-Attention Overview\n"
            "Self-attention allows tokens to dynamically weight their relevance to other tokens.\n"
            "Formula: Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V\n"
            "Todo Idea: Implement a clean multi-head attention block from scratch in PyTorch tomorrow."
        ),
        depth=0
    )

    print(f"Input Page Loaded: '{mock_page.page_title}' ({len(mock_page.text_content)} characters)")
    print("-" * 60)

    # Instantiate our chunker with diagnostic print statements
    chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=20)

    # Run parsing execution
    print("Executing sliding-window chunking engine...")
    payload = chunker.chunk_page(mock_page)

    # Verify Batch Execution Telemetry
    print("Ingestion Pipeline Processing Complete!")
    print(f"Telemetry -> Latency: {payload.parsing_latency_ms:.4f} ms")
    print(f"Telemetry -> Total Chunks Generated: {payload.total_chunks}")
    print("=" * 60)

    # Print loop to check data object structure
    for chunk in payload.chunks:
        print(f"[CHUNK INDEX {chunk.chunk_index}]")
        print(f"ID / Hash: {chunk.chunk_id}")
        print(f"Context:   {repr(chunk.text_content)}") 
        print(f"Metadata:  Notebook={chunk.notebook_name} | Section={chunk.section_name} | Title={chunk.parent_page_title}")
        print("-" * 60)

if __name__ == "__main__":
    # initialize the tracking connection using values from our config file
    if config.telemetry.enable_opik:
        opik.configure(
            api_key=os.getenv("OPIK_API_KEY"),
            workspace=os.getenv("OPIK_WORKSPACE"),
            force=True,
            automatic_approvals=True
        )
    
    run_integration_test()