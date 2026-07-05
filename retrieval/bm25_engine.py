import string
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from ingestion.structures import ProcessedChunk
from config import config
import opik
from opik import opik_context

class BM25Engine:
    """
    Stateful lexical retrieval engine implementing the BM25Okapi algorithm.
    Provides exact keyword tracking over ProcessedChunks.
    """
    def __init__(self):
        """Initialize the BM25Okapi engine with an empty corpus."""
        # Master record holding our data chunks indexed cleanly by unique chunk_id
        self.chunks_dict: Dict[str, ProcessedChunk] = {}
        # Parallel list maintaining structural sequence mapping to chunk keys
        self.corpus_ids: List[str] = []
        # Underlying matehmatical index initialized on state hydrate / upsert
        self.bm25: Optional[BM25Okapi] = None  

    def _tokenize(self, text: str) -> List[str]:
        """
        Cleans and splits text into explicit lowercase word tokens.
        Preserves special technical constructs like underscores while stripping punctuation.
        """
        lowered = text.lower()
        # Remove common syntax punctuation elements but keep word text symbols intact
        cleaned = lowered.translate(str.maketrans("", "", string.punctuation.replace("_", "")))
        return cleaned.split()
    
    @opik.track(project_name="secure-rag-memory-engine")
    def upsert_chunks(self, chunks: List[ProcessedChunk]) -> int:
        """
        Deduplicates chunks via unique hash IDs, caches them in memory, 
        and fits the BM25 statistical text index arrays.
        """
        opik_context.update_current_trace(
            metadata={
                "phase": config.telemetry.current_phase,
                "chunk_count": len(chunks),
                "engine_type": "bm25"
            }
        )

        if not chunks:
            print("[BM25Engine] Upsert aborted: The provided chunk list is completely empty.")
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
        print(f"Building statistical BM25Okapi arrays over {len(tokenized_corpus)} processed text sequences...")
        self.bm25 = BM25Okapi(tokenized_corpus)

        return len(chunks)
    
    @opik.track(project_name="secure-rag-memory-engine")
    def search_similar_chunks(
            self, query_text: str, top_k: int, filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enforces workspace filtering constraints before calculation, computes BM25
        scores, and returns results in a layout that mirrors the CrhomaDB's output structure.
        """
        opik_context.update_current_trace(
            metadata={
                "phase": config.telemetry.current_phase,
                "query": query_text,
                "top_k": top_k,
                "has_filter": filter_dict is not None,
                "engine_type": "bm25"
            }
        )
        
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





        


