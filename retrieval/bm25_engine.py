import os
import pickle
import string
from typing import List, Dict, Any, Optional
from config import config
from rank_bm25 import BM25Okapi
from ingestion.structures import ProcessedChunk
from telemetry import track, update_current_span

class BM25Engine:
    """
    Stateful lexical retrieval engine implementing the BM25Okapi algorithm.
    Provides exact keyword tracking over ProcessedChunks.
    """
    def __init__(self):
        """Initialize the BM25Okapi engine and hydrate state if index exists."""
        # Master record holding our data chunks indexed cleanly by unique chunk_id
        self.chunks_dict: Dict[str, ProcessedChunk] = {}
        # Parallel list maintaining structural sequence mapping to chunk keys
        self.corpus_ids: List[str] = []
        # Underlying matehmatical index initialized on state hydrate / upsert
        self.bm25: Optional[BM25Okapi] = None  

        # Load state automatically upon initialization
        self._load_index()

    def _load_index(self) -> None:
        """
        Hydrates BM25 state from disk if index file exists and is valid.
        """
        index_path = config.bm25.index_path

        if not os.path.exists(index_path):
            print(f"ℹ️ [BM25Engine] No existing index found at '{index_path}'. Starting with empty state.")
            return

        try:
            with open(index_path, "rb") as f:
                data = pickle.load(f)
                self.chunks_dict = data.get("chunks_dict", {})
                self.corpus_ids = data.get("corpus_ids", [])
                self.bm25 = data.get("bm25", None)
                print(f"✅ [BM25Engine] Hydrated persistent index with {len(self.corpus_ids)} chunks from '{index_path}'.")
        except Exception as e:
            print(f"⚠️ [BM25Engine] Index at '{index_path}' is invalid/corrupted ({e}). Starting empty.")
            self.chunks_dict = {}
            self.corpus_ids = []
            self.bm25 = None

    def _save_index(self) -> None:
        """
        Serializes in-memory dictionary and BM25 model arrays directly to disk.
        """
        index_path = config.bm25.index_path

        # Ensures dictionary exists before saving (e.g. data/)
        os.makedirs(os.path.dirname(index_path), exist_ok=True)

        payload = {
            "chunks_dict": self.chunks_dict,
            "corpus_ids": self.corpus_ids,
            "bm25": self.bm25
        }

        with open(index_path, "wb") as f:
            pickle.dump(payload, f)

        print(f"✅ [BM25Engine] Successfully persisted index ({len(self.corpus_ids)} total records) to '{index_path}'.")

    def reset_index(self) -> None:
        """
        Clears in-memory data structures and removes the 
        serialized pickle file from disk.
        """
        index_path = config.bm25.index_path
        self.chunks_dict = {}
        self.corpus_ids = []
        self.bm25 = None

        if os.path.exists(index_path):
            try:
                os.remove(index_path)
                print(f"🗑️ [BM25Engine] Removed persistent index pickle file at '{index_path}'.")
            except Exception as e:
                print(f"⚠️ [BM25Engine] Failed to delete pickle file at '{index_path}': {e}")
        else:
            print(f"ℹ️ [BM25Engine] No index file found at '{index_path}' to delete.")

        print("✅ [BM25Engine] Reset to clean empty state.")

    def _tokenize(self, text: str) -> List[str]:
        """
        Cleans and splits text into explicit lowercase word tokens.
        Preserves special technical constructs like underscores while stripping punctuation.
        """
        lowered = text.lower()
        # Remove common syntax punctuation elements but keep word text symbols intact
        cleaned = lowered.translate(str.maketrans("", "", string.punctuation.replace("_", "")))
        return cleaned.split()

    @track(name="bm25_upsert_chunks", capture_input=False)
    def upsert_chunks(self, chunks: List[ProcessedChunk]) -> int:
        """
        Deduplicates chunks via unique hash IDs, caches them in memory, 
        and fits the BM25 statistical text index arrays.
        """
        # Attach high-level metadata to the root trace
        update_current_span(
            {
                "engine": "BM25Engine",
                "index_path": config.bm25.index_path,
                "chunk_count": len(chunks),
            }
        )

        if not chunks:
            print("⚠️ [BM25Engine] Upsert aborted: The provided chunk list is completely empty.")
            return 0
        
        # Deduplicate and register payload blocks using memory map dictionary
        for chunk in chunks:
            self.chunks_dict[chunk.chunk_id] = chunk

        # Extract operational data sequences for model re-indexing
        self.corpus_ids = list(self.chunks_dict.keys())

        # Double check: did any unique keys register in the system?
        if not self.corpus_ids or len(self.corpus_ids) == 0:
            print("⚠️ [BM25Engine] Upsert aborted: Compiled tracking corpus identifier list is empty.")
            return 0

        tokenized_corpus = [
            self._tokenize(self.chunks_dict[cid].text_content)
            for cid in self.corpus_ids
        ]

        # Instantiate/re-index the statistical BM25 storage tables
        print(f"🔢 [BM25Engine] Building statistical BM25Okapi arrays over {len(tokenized_corpus)} processed text sequences...")
        self.bm25 = BM25Okapi(tokenized_corpus)

        # Persist updated state to disk
        self._save_index()

        return len(chunks)

    @track(name="bm25_search_similar_chunks")
    def search_similar_chunks(
            self, query_text: str, top_k: Optional[int] = None, filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enforces workspace filtering constraints before calculation, computes BM25
        scores, and returns results in a layout that mirrors the CrhomaDB's output structure.
        """
        # Attach high-level metadata to the root trace
        update_current_span(
            {
                "engine": "BM25Engine",
                "index_path": config.bm25.index_path,
                "top_k": top_k,
                "has_filter": filter_dict is not None
            }
        )
        
        # Late binding with explicit None checks to avoid truthiness traps (e.g., limit=0)
        if top_k is None:
            top_k = config.retrieval.top_k
        
        # Formulate standard empty response pattern matching Chroma layout contracts
        default_response = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

        # Check the incoming query is not an empty string or spaces
        if not query_text.strip():
            print("⚠️ [BM25Engine] Search aborted: The provided query text is empty.")
            return default_response

        if not self.bm25 or not self.corpus_ids or top_k <= 0:
            print("⚠️ [BM25Engine] Search aborted: Engine state table uninstantiated or top_k parameter invalid.")
            return default_response
        
        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            print("⚠️ [BM25Engine] Search aborted: No valid alphanumeric terms extracted after tokenization parsing.")
            return default_response
        
        # Step 1: pre-filter chunks according to filter_dict constraints, if any are provided
        valid_indices = []
        filtered_tokens_corpus = []

        print(f"Evaluating metadata filters over global index repository across {len(self.corpus_ids)} partitions...")
        for idx, cid in enumerate(self.corpus_ids):
            chunk = self.chunks_dict[cid]

            # Evaluate explicit metadata assertions if a filter dict is provided
            is_valid = True
            if filter_dict:
                for key, val in filter_dict.items():
                    if getattr(chunk, key, None) != val:
                        is_valid = False
                        break
            if is_valid:
                valid_indices.append(idx)
                filtered_tokens_corpus.append(self._tokenize(chunk.text_content))

        if not valid_indices:
            print(f"⚠️ [BM25Engine] Scope isolation constraint returned 0 matching records for criteria: {filter_dict}")
            return default_response

        # Step 2: Compute math scores exclusively on safe, filtered documents
        print(f"Generating matching term-frequency scores across {len(filtered_tokens_corpus)} tenant-isolated documents...")
        temp_bm25 = BM25Okapi(filtered_tokens_corpus)
        scores = temp_bm25.get_scores(query_tokens)

        # Map scores back to the original matching master data items
        scored_candidates = []
        for local_idx, original_idx in enumerate(valid_indices):
            cid = self.corpus_ids[original_idx]
            score = float(scores[local_idx])
            # Only return chunks that offer actual keyword intersections
            if score > 0.0:
                scored_candidates.append((self.chunks_dict[cid], score))
        
        # Step 3: Sort relevance scores in descending order
        print(f"Sorting candidate records and extracting the top {top_k} high-scoring exact keyword lexical matches...")
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_matches = scored_candidates[:top_k]

        if not top_matches:
            print(f"No positive text intersections found for current query keywords: {query_tokens}")
            return default_response
        
        # Step 4: Extract payload elements into parallel arrays matching Chroma DB maps
        res_ids = [c.chunk_id for c, _ in top_matches]
        res_docs = [c.text_content for c, _ in top_matches]
        res_scores = [score for _, score in top_matches]
        res_metas = [
            {
                "parent_page_id": c.parent_page_id,
                "notebook_name": c.notebook_name,
                "section_name": c.section_name,
                "parent_page_title": c.parent_page_title,
                "chunk_index": c.chunk_index
            }
            for c, _ in top_matches
        ]

        return {
            "ids": [res_ids],
            "documents": [res_docs],
            "metadatas": [res_metas],
            "distances": [res_scores]  # Keeps the response swappable with test scripts
        }