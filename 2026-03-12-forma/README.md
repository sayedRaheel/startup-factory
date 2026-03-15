<div align="center">
  <img src="./banner.png" alt="Forma Banner" width="800">
  <h1>Forma</h1>
  <p>A lightweight CLI compiler that transforms strict JSON schemas into deterministic, production-ready LLM structured outputs.</p>
</div>

---

## What is Forma?

Forma solves the unpredictability of natural language prompt engineering by treating LLM interactions as strongly typed infrastructure. 

With Forma, you define instructions and exact output schemas using a concise JSON specification (`.forma.json`). The CLI sends this directly to OpenAI using guaranteed **Structured Outputs**, ensuring the LLM response is perfectly typed and immediately usable in your code.

## Key Features

- **Strict Schema Enforcement:** Never write regex to parse LLM outputs again. Define your schema in JSON, and the LLM is physically forced to adhere to it.
- **Deterministic Compiler:** The `forma` CLI calls OpenAI's native JSON Schema validation to guarantee 100% adherence.
- **Local-First, No Dependencies:** Written in vanilla Node.js 18+. No `node_modules` bloated dependencies.

---

## Getting Started

### Prerequisites
- Node.js (v18+)
- `OPENAI_API_KEY` set in your environment.

### Installation

```bash
export OPENAI_API_KEY="sk-..."
npx forma-cli test example.forma.json
```

*(Or clone and link globally:)*
```bash
git clone https://github.com/sayedRaheel/startup-factory.git
cd startup-factory/2026-03-12-forma
npm link
forma run my_prompt.forma.json
```

---

## Example Usage

**1. Create a `users.forma.json` file:**
```json
{
    "model": "gpt-4o-2024-08-06",
    "prompt": "Generate 3 fake user profiles.",
    "schema": {
        "type": "object",
        "properties": {
            "users": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": { "type": "string" },
                        "age": { "type": "number" },
                        "email": { "type": "string" }
                    },
                    "required": ["name", "age", "email"],
                    "additionalProperties": false
                }
            }
        },
        "required": ["users"],
        "additionalProperties": false
    }
}
```

**2. Execute it:**
```bash
forma run users.forma.json
```

**3. Guaranteed Output:**
```json
{
  "users": [
    { "name": "Alice Smith", "age": 28, "email": "alice@example.com" },
    { "name": "Bob Jones", "age": 34, "email": "bob@example.com" },
    { "name": "Charlie Brown", "age": 41, "email": "charlie@example.com" }
  ]
}
```
