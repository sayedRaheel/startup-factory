# Forma

**A lightweight CLI and Domain-Specific Language (DSL) that compiles strictly typed, code-centric constraints into deterministic, production-ready LLM prompts and structured API calls.**

---

## What is Forma?

Forma solves the unpredictability of natural language prompt engineering by treating LLM interactions as strongly typed infrastructure. With Forma, you define instructions, contextual constraints, and exact output schemas using a concise, declarative syntax—similar to TypeScript interfaces or Protocol Buffers. 

The built-in compiler and static linter catch logical ambiguities and schema errors *before* any API calls are made, transforming your `.forma` files into optimized, model-specific API payloads.

## Key Features

- **Strongly Typed DSL:** Replace verbose English prompt engineering with a declarative syntax. Explicitly define system objectives, input parameters (e.g., `user_query: string`), and strict output structures (like specific JSON schemas or typed code snippets).
- **Deterministic Compiler & Linter:** The `forma` CLI statically analyzes your `.forma` files to catch logical flaws and validate schemas. It compiles valid DSL into optimized TypeScript functions or raw JSON payloads compatible with OpenAI, Anthropic, and Google Gemini.
- **Testable Prompt Assertions:** Bring CI/CD rigor to your LLM interactions. Forma includes first-class testing primitives that allow you to write unit tests for your prompts. Verify that the model's output strictly adheres to your defined schema and passes deterministic assertions.
- **Local-First, No Database:** Forma operates entirely locally. Treat your `.forma` files as standard source code managed via Git—no external databases required.

## Tech Stack

Forma is built for robust performance and seamless integration into modern toolchains:
- **Core Environment:** Node.js & TypeScript
- **CLI Routing:** Commander.js
- **Schema Validation:** Zod
- **API Clients:** Official OpenAI, Anthropic, and Google GenAI SDKs

---

## Getting Started

### Prerequisites
- Node.js (v18 or higher recommended)
- API keys for your preferred LLM providers (OpenAI, Anthropic, or Google Gemini) set in your environment (e.g., via `.env`).

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/your-org/forma.git
cd forma
npm install
npm run build
```

*(You can also use Forma's CLI during development via `npm run dev` or by linking the local binary).*

---

## User Flow

### 1. Define (`generate_api.forma`)

Create a `.forma` file using the formal DSL to specify your goal. Define the input variables and the exact structure of the data the LLM must return.

### 2. Compile & Lint

Run the `build` command to analyze and compile your prompt:

```bash
forma build <path/to/generate_api.forma>
```
The CLI statically checks your file for ambiguities and compiles it into an optimized TypeScript module or JSON payload, ensuring it's production-ready.

### 3. Execute & Assert

Test your compiled prompt against your chosen LLM and validate the outputs:

```bash
forma test <path/to/generate_api.forma>
```
Forma acts as a test runner, executing the prompt, automatically parsing the output against the defined schema, and reporting pass/fail metrics.

---

## License

This project is licensed under the **ISC License**.
