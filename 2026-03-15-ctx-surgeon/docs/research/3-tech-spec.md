# Technical Specification Document (Tech Spec)

## Product Name: ctx-surgeon

### 1. Architecture Overview
`ctx-surgeon` is a single, zero-dependency Python 3 script that executes in two primary phases:
1. **Directory Traversal:** Using `os.walk`, it recursively scans the target directory, ignoring common build and dependency folders (`.git`, `node_modules`, `venv`, `dist`, etc.) to generate a clean, ASCII directory tree.
2. **Signature Extraction:** For every supported file extension (`.py`, `.ts`, `.js`, `.go`, `.rs`, `.c`, `.cpp`, `.java`), it opens the file and applies a pre-compiled set of language-agnostic regular expressions to extract structural definitions (functions, classes, interfaces, structs, types).

### 2. Regular Expression Definitions
The core extraction logic relies on identifying the *start* of structural blocks without needing a full AST parser. The following regexes are optimized for the most common languages:

*   **Python:** `^\s*(async\s+)?def\s+` and `^\s*class\s+`
*   **TypeScript/JavaScript:**
    *   `^\s*(export\s+)?(async\s+)?function\s+`
    *   `^\s*(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s+)?(\(.*\)|\w+)\s*=>`
    *   `^\s*(export\s+)?interface\s+`
    *   `^\s*(export\s+)?type\s+`
*   **Go:**
    *   `^\s*func\s+`
    *   `^\s*type\s+.*\s+(struct|interface)`
*   **Rust:**
    *   `^\s*(pub\s+)?(fn|struct|enum|trait|impl)\s+`

### 3. Execution Flow
1. Parse `sys.argv[1]` as the target directory (defaulting to `.`).
2. Print the Markdown header (`# 🧠 ctx-surgeon: Codebase Skeleton Extraction`).
3. Print the Directory Structure inside a ````text` code block.
4. Iterate through all valid files, running the `extract_signatures` function on each line.
5. If signatures are found for a file, print the relative file path as a Markdown header (`### relative/path/to/file.ext`) and enclose the signatures in a markdown code block matching the file extension.

### 4. Constraints
- **Performance:** Because it processes lines sequentially with regexes, it is significantly faster and uses less memory than a full AST parser like `tree-sitter`.
- **Accuracy:** It is an approximation. It does not parse multi-line function signatures perfectly (it extracts the first line), but this is by design: the LLM only needs the *name* and the *start* of the signature to know it exists.
- **Portability:** The script must run on any Unix-like system with Python 3 installed, requiring no `pip` packages.
