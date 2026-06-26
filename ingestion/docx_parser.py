# TODO (Phase 2): The lookahead string-length heuristics below are vulnerable 
# to false positives from informal inline notes/tags placed just near page titles (e.g., "Left in middle:"). 
# Consider pivoting from .docx to a structural .html parsing approach using 
# BeautifulSoup to naturally isolate native OneNote <h1> tag boundaries.

# TODO (Phase 2): Test edge cases of logic ofr REDACTED SECRETS
# It is redacting parts of links as well (do we want this or not?)
# Is it redacting all the api keys?  

import os
import re
import json
import hashlib 
from typing import List, Dict, Any
from docx import Document
import opik
from opik import opik_context

from ingestion.structures import RawOnenotePage

# Remove these after testing
from config import config
from dotenv import load_dotenv

load_dotenv()


class SecureDocxParser:
    """
    Parses exported .docx sections from OneNote, applying strict automated security redaction filters,
    isolating true visual pages using lookahead timestamp validation, and 
    providing stateful caching via local manifest records for fault-tolerant executions.
    """
    
    def __init__(self, manifest_path: str = "data/ingestion_manifest.json"):
        # Compiled regular expressions for rapid, automated secret matching
        self.manifest_path = manifest_path
        self.secret_patterns = [
            re.compile(r"sk-[a-zA-Z0-9]{48}"),                  # OpenAI standard API Keys
            re.compile(r"AIzaSy[a-zA-Z0-9_\-]{33}"),             # Google Gemini API Keys
            re.compile(r"hf_[a-zA-Z0-9]{34,50}"),                # Hugging Face Access Tokens
            re.compile(r"(?:api_key|secret|password|passwd|comet)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", re.IGNORECASE), # Generic assignments
            re.compile(r"\b[a-zA-Z0-9]{32,64}\b")               # High-entropy standalone fallback
        ]
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        """Loads the historical ingestion ledger to check for previously parsed documents."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Manifest ledger corrupted. \nError occured: {e}.\nReinitializing empty state cache. ")
        return {}
    
    def clear_manifest_cache(self) -> bool:
        """
        Forcefully clears the local manifest file and resets the in-memory cache.
        Extremely useful for development testing and debugging structural pipeline iterations.
        """
        self.manifest = {}
        if os.path.exists(self.manifest_path):
            try: 
                os.remove(self.manifest_path)
                print(f"🧹 Manifest cache file at '{self.manifest_path}' successfully deleted.")
                return True
            except Exception as e:
                print(f"❌ Failed to delete manifest cache file: {str(e)}")
                return False
        else:
            print("ℹ️ No manifest file exists on disk to reset.")
            return True
        
    
    def _save_manifest(self):
        """Persists the updated operational status cache back onto local disk storage."""
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=8)

    def _sanitize_text(self, text:str) -> str:
        """Scans raw strings for potential credentials and replaces them with a redacted placeholder."""
        sanitized = text
        for pattern in self.secret_patterns:
            sanitized = pattern.sub("REDACTED_SECRET", sanitized)
        return sanitized

    def _generate_deterministic_hash(self, text: str) -> str:
        """Genereates a secure, deterministic SHA-256 hex digit for IDs and content tracking."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    
    @opik.track()
    def parse_section_into_pages(self, file_path: str, notebook_name: str, section_name: str) -> List[RawOnenotePage]:
        """
        Reads a single .docx section file, detects genuine page segments by validating OneNote's native timestamp signatures, 
        ignores false-positive formatting, scrubs secrets, and tracks state changes using SHA-256 page hashes.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Target document not found: {file_path}")
        
        doc = Document(file_path)
        pages: List[RawOnenotePage] = []

        # Regex patterns to validate OneNote's true page header timestamps (e.g., "28 May 2024" and "04:58")
        date_pattern = re.compile(r"^\d{1,2}\s+[A-Za-z]+\s+\d{4}")
        time_pattern = re.compile(r"^\d{2}:\d{2}")

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        total_p = len(paragraphs)

        current_page_title = f"{section_name} - Introduction"
        current_page_lines = []
        page_index = 0

        i = 0
        while i < total_p:
            raw_text = paragraphs[i]
            sanitized_line = self._sanitize_text(raw_text)

            # Lookahead Validation: Check if this line is a structural header candidate
            # It must be short, and the next two lines MUST look like a Date and Time block
            is_genuine_header = False
            if len(raw_text) < 90 and (i+2) < total_p:
                next_line_1 = paragraphs[i+1].strip()
                next_line_2 = paragraphs[i+2].strip()
                if date_pattern.match(next_line_1) and time_pattern.match(next_line_2):
                    is_genuine_header=True

            if is_genuine_header:
                # Package and flush the previosu page out before opening a new boundary slot
                if current_page_lines:
                    page_content = "\n".join(current_page_lines)
                    page_id = self._generate_deterministic_hash(f"{file_path}_{page_index}")
                    page_hash = self._generate_deterministic_hash(page_content)

                    pages.append(RawOnenotePage(
                        page_id=page_id,
                        notebook_name=notebook_name,
                        section_name=section_name,
                        page_title=current_page_title,
                        text_content=page_content,
                        page_hash=page_hash,
                        depth=0
                    ))
                    page_index += 1
                    current_page_lines = []
                
                # Assign the clean validated heading title, and advance past the title + 2 timestamp rows
                current_page_title = sanitized_line
                i += 3
                continue
            else:
                current_page_lines.append(sanitized_line)
                i += 1

        # Flush any trailing lines into the ifnal page slot
        if current_page_lines:
            page_content = "\n".join(current_page_lines)
            page_id = self._generate_deterministic_hash(f"{file_path}_{page_index}")
            page_hash = self._generate_deterministic_hash(page_content)

            pages.append(RawOnenotePage(
                page_id=page_id,
                notebook_name=notebook_name,
                section_name=section_name,
                page_title=current_page_title,
                text_content=page_content,
                page_hash=page_hash,
                depth=0
            ))

        # Log metrics to our Opik dashboard telemetry span
        opik_context.update_current_trace(
            metadata={
                "file_name": os.path.basename(file_path),
                "total_pages_extracted": len(pages),
            }
        )

        return pages
    
    @opik.track(project_name="secure-rag-memory-engine")
    def scan_directory(self, root_dir: str) -> List[RawOnenotePage]:
        """
        Recursively walks directories, checking local modification files against
        cached manifest records to enable stateful resume and robust fault containment.
        """
        all_parsed_pages = []

        if not os.path.exists(root_dir):
            print(f"⚠️ Target data directory does not exist: {root_dir}")
            return all_parsed_pages
        
        # Walks through file trees
        for root, _, files in os.walk(root_dir):
            for file in files:
                # Target docx documents while explicitly dropping active MS Word runtime lock files (~$)
                if file.endswith(".docx") and not file.startswith("~$"):
                    full_path = os.path.join(root, file)

                    # Compute file properties for cache validation, and
                    # Parse directory strings into Typed Metadata Concepts
                    last_modified = os.path.getmtime(full_path)
                    relative_path = os.path.relpath(root, root_dir)
                    notebook_name = "Default" if relative_path == "." else relative_path
                    section_name = os.path.splitext(file)[0]

                    # Look for historical cache hits in our manifest ledger
                    if full_path in self.manifest:
                        if self.manifest[full_path]["last_modified"] == last_modified:
                            print(f"✨ Skipping (Cached & Unchanged): [{section_name}] in Notebook: [{notebook_name}]")
                            # if cached and unchanged, read existing entries out to save cycle time if needed,
                            # or bypas based on master workflow coordinator preferences
                            continue

                    print(f"📦 Scraping Section: [{section_name}] inside Notebook: [{notebook_name}]")

                    try:
                        section_pages = self.parse_section_into_pages(full_path, notebook_name, section_name)
                        all_parsed_pages.extend(section_pages)

                        # Upon successful extraction, commit the file metrics to the local ledger
                        self.manifest[full_path] = {
                            "notebook_name": notebook_name,
                            "section_name": section_name,
                            "last_modified": last_modified,
                            "pages_count": len(section_pages),
                            "extracted_pages_metrics": [
                                {
                                    "title": p.page_title,
                                    "character_count": len(p.text_content) # Absolute verification check
                                }
                                for p in section_pages
                            ]
                        }
                        self._save_manifest()  # Save after every file for progressive persistence

                    except Exception as e:
                       # Fault containment: failure to read a file notes down the error but preserves runtime
                       print(f"❌ Fault Containment Triggered! Failed to process {file}: {str(e)}")
                             
        return all_parsed_pages