## MergeGuard Product Requirements Document

### 1. Product Name
MergeGuard

### 2. One-sentence Pitch
An automated AI code reviewer that catches bugs and enforces style guidelines on your GitHub Pull Requests before human review.

### 3. The Target Audience
Engineering teams, Open Source maintainers, and individual developers wanting a second set of "AI eyes" on their code.

### 4. Core Feature Set
- **Diff Analysis:** Automatically pulls Git diffs and feeds them into an LLM context.
- **Rules Engine:** Reads a local `.mergeguard.yml` file to strictly enforce custom project formatting rules.
- **Actionable Output:** Provides line-by-line feedback directly in the terminal or via GitHub Actions.

### 5. Technical Stack Recommendation
TypeScript / Node.js - Ideal for CLI tools that heavily utilize asynchronous API calls (OpenAI) and file system interactions.
