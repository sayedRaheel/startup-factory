# Product Requirements Document (PRD)

## Product Name: ctx-surgeon (Precision Context Extraction for AI)

### 1. Goal Alignment Trace:
I am proposing **ctx-surgeon** -> because Dr. Silas identified the "100-hour gap" caused by AI agents losing the plot as codebases grow -> because this wasted time suffocates developer velocity and prevents rapid iteration on features, leading to compile errors and hallucinations -> because inefficient, frustrating LLM developer experience directly impacts our ability to build and ship high-quality, impactful projects quickly, which is critical for achieving viral adoption and securing GitHub stars, our ultimate goal.

### 2. One-sentence Pitch:
`ctx-surgeon` is a lightning-fast, zero-dependency Python CLI tool that scans any repository and extracts a Codebase Context Skeleton—containing the directory tree and every single function/class/struct/interface signature—without the actual implementation bloat.

### 3. The Target Audience:
Any developer building AI agents, writing custom Claude Code tools, or operating a multi-file project with AI coding assistants. It gives their local LLMs the "X-ray vision" needed to map a repository without blowing up the token window.

### 4. Core Feature Set (Maximum 3):
These three features are the absolute minimum to achieve viral adoption by solving the identified gap with surgical precision. Bloat will be ruthlessly cut.

*   **Zero-Dependency AST/Regex Extraction:** A single executable script that uses robust regex patterns to parse AST-like structures for major languages (Go, TS, JS, Python, Rust, C++). No heavy parsers, no `npm install`, no `pip install`.
*   **Markdown Codebase Context Skeleton:** Generates a highly-optimized, token-efficient Markdown output containing the directory structure (`tree`) and the structural signatures of every file (`class`, `def`, `func`, `interface`).
*   **Universal Agent Compatibility:** Can be seamlessly integrated into any agentic workflow (like `SKILL.md` for OpenClaw/Claude Code) as a precursor step before reading or editing files.

### 5. Technical Stack Recommendation:
Python 3. It's ubiquitous, requires zero compilation, and its `re` and `os` standard libraries are more than sufficient for high-speed file traversal and regex-based signature extraction.

### 6. User Flow (3 Steps):
1. **Surgeon Scan:** `ctx-surgeon ./target-dir > skeleton.md`
2. **Target File Read:** The AI agent reads `skeleton.md` to identify the file it needs to edit (e.g., finding `func AuthenticateUser` in `auth.go`).
3. **Deep Read & Edit:** The AI reads *only* the specific file it needs to edit using `cat` or `read`, and writes the code with full contextual awareness.
