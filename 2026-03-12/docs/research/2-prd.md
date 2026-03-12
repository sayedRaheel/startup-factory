# Product Requirements Document (PRD)

## 1. Product Name
**Forma**

## 2. One-sentence Pitch
A lightweight CLI and Domain-Specific Language (DSL) that compiles strictly typed, code-centric constraints into deterministic, production-ready LLM prompts and structured API calls.

## 3. Core Feature Set
1. **Strongly Typed DSL:** A concise, declarative syntax (similar to TypeScript interfaces or Protocol Buffers) for defining LLM instructions, contextual constraints, and exact output schemas, eliminating the need for verbose English prompt engineering.
2. **Deterministic Compiler & Linter:** A built-in CLI compiler that translates `.forma` files into optimized, model-specific API payloads (e.g., OpenAI, Anthropic). It includes a static linter that validates schema definitions and catches logical ambiguities *before* any API calls are made.
3. **Testable Prompt Assertions:** First-class testing primitives that allow developers to write unit tests for their LLM interactions. It verifies that the model's output strictly adheres to the defined schema and passes deterministic assertions, making prompts safe for CI/CD pipelines.

## 4. Technical Stack Recommendation
* **Core Language / Environment:** Node.js & TypeScript. (Chosen for its robust parsing libraries, massive developer ecosystem, and natural affinity for defining JSON-like schemas).
* **CLI Framework:** Commander.js or Oclif for building the command-line interface.
* **APIs Required:** OpenAI API, Anthropic API, Google Gemini API (for routing and testing compiled prompts against various models).
* **Database:** None. Forma operates entirely locally, treating `.forma` files as standard source code managed via Git.

## 5. User Flow
* **Step 1: Define:** The developer creates a `generate_api.forma` file, using the formal DSL to specify the system objective, input parameters (e.g., `user_query: string`), and the strict output structure (e.g., returning a specific JSON object or a typed code snippet).
* **Step 2: Compile & Lint:** The developer runs `forma build`. The CLI statically analyzes the `.forma` file for ambiguities, validates the schema, and compiles it into an optimized TypeScript function or raw JSON payload ready for integration.
* **Step 3: Execute & Assert:** The developer runs `forma test`. The CLI executes the compiled prompt against the chosen LLM, automatically parsing the output, validating it against the requested schema, and reporting pass/fail metrics just like a standard test runner.
