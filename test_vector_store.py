import os
from dotenv import load_dotenv 
from ingestion.structures import RawOnenotePage
from ingestion.base_parser import FixedSizeChunker
from retrieval.vector_store import ChromaVectorEngine
from config import config
import opik

# Automatically find and load the .env file into the system memory
load_dotenv()

def run_retrieval_test():
    print("=" * 60)
    print("INITIALIZING VECTOR ENGINE STORE TEST")
    print("=" * 60)

    # Ensure we have our API key set up in our terminal environment
    # For Phase 1 testing, we check if the key exists before running
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("WARNING: OPENAI_API_KEY not found in your .env file.")
        print("Please create a .env file at your project root containing your key.")
        print("=" * 60)
        return
    
    # Re-create our mock page and chunks from main.py (phase1-intergation-test)
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

    chunker = FixedSizeChunker(chunk_size = 100, chunk_overlap = 20)
    payload = chunker.chunk_page(mock_page)
    print(f"Generated {len(payload.chunks)} chunks from ingestion engine.")

    # Instantiate our new Vector Store Layer
    print("Intializing Ephemeral ChromaDB Client...")
    engine = ChromaVectorEngine()

    # Attempt Upsert
    print("Slicing payload and initializing batch upload...")
    try:
        total_upserted = engine.upsert_chunks(payload.chunks)
        print("=" * 60)
        print(f"SUCCESS: Seccessfully embedded and stored {total_upserted} chunks")
        print(f"Database State: Collection count is now {engine.collection.count()}")
        print("=" * 60)
    except Exception as e:
        print("=" * 60)
        print(f"ERROR OCCURED DURING UPSERT: {e}")
        print("=" * 60)
        return

    # Run a Live Semantic Query
    try:
        print("\n" + "🔍" * 20)
        print("Running Live Semantic Retrieval Test")
        print("🔍" * 20)

        user_query = "How do I implement multi-head attention in PyTorch?"

        # We ask for the single top matches
        search_results = engine.search_similar_chunks(query_text=user_query, top_k=2)

        # Parse and display what Chroma returned
        print("\nTop Search Results Returned by ChrmaDB:")
        for idx, (doc, score, meta) in enumerate(zip(
            search_results['documents'][0], 
            search_results['distances'][0], 
            search_results['metadatas'][0]
        )):
            print(f"\n[Rank {idx + 1}] (Distance/Inexactness Score: {score:.4f})")
            print(f"   Notebook: {meta['notebook_name']} -> Section: {meta['section_name']}")
            print(f"   Content: {repr(doc)}")
        print("=" * 60)

    except Exception as e:
        print("=" * 60)
        print(f"ERROR OCCURED DURING QUERYING: {e}")
        print("=" * 60)

if __name__ == "__main__":
    if config.telemetry.enable_opik:
        opik.configure(
            api_key=os.getenv("OPIK_API_KEY"),
            workspace=os.getenv("OPIK_WORKSPACE"),
            force=True,
            automatic_approvals=True
        )

    run_retrieval_test() 

