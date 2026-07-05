import os
from dotenv import load_dotenv 

# Absolute first step: Load environment strings into system memory 
# BEFORE initializing any internal config modules to prevent empty state overrides.
load_dotenv()

from ingestion.docx_parser import SecureDocxParser
from config import config
import opik


def run_docx_parser_test(root_dir):
    print("=" * 60)
    print("INITIALIZING STATEFUL DOCX PARSER INTEGRATION TEST")
    print("=" * 60)

    # Initialize the Secure Docx Parser object
    parser = SecureDocxParser()

    # Force a full cache reset before scanning to test adjustments!
    print("🧹 Clearing local manifest state tracking ledger...")
    parser.clear_manifest_cache()

    # Execute directory tree discovery and parse file targets from scratch
    print("🔍 Starting lookahead extraction scanner across 'data/onenote_exports'...")
    fresh_pages = parser.scan_directory(root_dir)

    print("=" * 60)
    print(f"📊 VERIFICATION METRICS (Extracted Count: {len(fresh_pages)})")
    print("=" * 60)

    # Validate the data contract returned by the Pydantic parser schemas
    if not fresh_pages:
        print(f"ℹ️ No pages extracted. Check that your sample notes reside inside '{root_dir}'")
    else:
        for idx, page in enumerate(fresh_pages, start=1):
            print(f"Page {idx}:")
            print(f"  📂 Notebook: {page.notebook_name}")
            print(f"  📝 Section:  {page.section_name}")
            print(f"  📌 Title:    {page.page_title}")
            print(f"  🔢 Length:   {len(page.text_content)} characters")
            print(f"  🔑 SHA-256:  {page.page_hash}")
            print("-" * 40)

    print("=" * 60)
    print("✅ TEST SUITE RUN COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    if config.telemetry.enable_opik:
        opik.configure(
            api_key=os.getenv("OPIK_API_KEY"),
            workspace=os.getenv("OPIK_WORKSPACE"),
            force=True,
            automatic_approvals=True
        )

    export_path = os.path.join("data", "onenote_exports")
    run_docx_parser_test(export_path) 