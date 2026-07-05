Current Phase:
Phase 1

---
Current Pillar:
Retrieval

---
Current Branch:
`feature/phase1-bm25`

---
Current Goal:
Implement lexical retrieval.

---
Completed:
Ingestion
* Document Parser 
* Document Sanitization
* Chunk Generation using Fixed Size Chunker

Chromma Vector Engine
* Chunk Embedding 
* Upsert Chunks in chromadb
* Search Similar Chunks using chromadb

---
Data Models used: 
* class RawOnenotePage(BaseModel):
page_id: str 
notebook_name: str
section_name: str
page_title: str
text_content: str
page_hash: str
depth: int = 0  # 0 = main page, 1 = subpage, etc.
parent_page_id: Optional[str] = None  # Tracks hierarchy for sub-pages

class ProcessedChunk(BaseModel):
chunk_id: str 
parent_page_id: str
text_content: str
chunk_index: int
notebook_name: str
section_name: str
parent_page_title: str
content_hash: str  

class IngestionPayload(BaseModel): 
source_page_id: str
chunks: List[ProcessedChunk]
total_chunks: int
parsing_latency_ms: float

---
Definition of Done
* BM25 created
* search similar chunks using bm25