import os
import ast
import re

def generate_codebase_map(root_dir="."):
    """Walks the codebase and uses AST to extract signatures and docstrings."""
    summary = []

    # Exclude directories we do not want to parse
    exclude_dirs = {'.git', '__pycache__', 'data', 'venv', 'env', 'docs', 'tools'}

    for root, dirs, files in os.walk(root_dir):
        # Filter directories in-place to prevent deep walking
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            # Parse only functional implementation python files
            if file.endswith(".py") and not file.startswith("test_") and file != "main.py":
                path = os.path.join(root, file).replace("\\", "/")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        node = ast.parse(f.read(), filename=path)
                except Exception as e:
                    print(f"ERROR OCCURED DURING PARSING FILE AT FILEPATH '{path}': {e}")
                    continue

                file_has_content = False
                file_buffer = [f"\n#### File: `{path}`"]

                for item in node.body:
                    # Parse Classes
                    if isinstance(item, ast.ClassDef):
                        file_has_content = True
                        class_doc = ast.get_docstring(item)
                        class_desc = f" -> *\"{class_doc.splitlines()[0]}\"*" if class_doc else ""
                        file_buffer.append(f"- `class {item.name}`{class_desc}")

                        for sub in item.body:
                            if isinstance(sub, ast.FunctionDef) and not sub.name.startswith("__"):
                                args = [a.arg for a in sub.args.args if a.arg != 'self']
                                fn_doc = ast.get_docstring(sub)
                                fn_desc = f"   - *\"{fn_doc.splitlines()[0]}\"*" if fn_doc else ""
                                file_buffer.append(f"  - `{sub.name}({', '.join(args)})`")
                                if fn_desc:
                                    file_buffer.append(f"   {fn_desc}")
                            
                    # Parse Standalone Functions
                    elif isinstance(item, ast.FunctionDef) and not item.name.startswith("__"):
                        file_has_content = True
                        args = [a.arg for a in item.args.args]
                        fn_doc = ast.get_docstring(item)
                        fn_desc = f" - *\"{fn_doc.splitlines()[0]}\"*" if fn_doc else ""
                        file_buffer.append(f"- `def {item.name}({', '.join(args)})`")
                        if fn_desc:
                            file_buffer.append(f"  {fn_desc}")

                if file_has_content:
                    summary.extend(file_buffer)

    return "\n".join(summary)

def inject_map_into_markdown(state_file_path="project_docs/03_CODEBASE.md"):
    """Injects the map in the markdown file."""
    if not os.path.exists(state_file_path):
        print(f"⚠️ Target file not found: {state_file_path}. Aborting injection.")
        return

    with open(state_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Generate the fresh layout structural map
    fresh_code_map = generate_codebase_map()

    with open(state_file_path, "w", encoding="utf-8") as f:
        f.write(fresh_code_map)
        
    print(f"✨ Successfully synchronized codebase map.")

if __name__ == "__main__":
    inject_map_into_markdown()
