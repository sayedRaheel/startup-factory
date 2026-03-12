Here is the Technical Specification and Implementation Plan for the **Forma** CLI and DSL compiler, designed for immediate execution by a developer.

### 1. Technical Stack & Libraries

*   **Runtime:** Node.js (v20+)
*   **Language:** TypeScript
*   **CLI Framework:** `commander` (Lightweight, standard for Node.js CLIs)
*   **Validation & Typing:** `zod` (For internal schema validation and generating JSON Schemas for LLM structured outputs)
*   **LLM SDKs:** `openai`, `@anthropic-ai/sdk`, `@google/genai`
*   **Build Tool:** `tsup` (Zero-config TypeScript bundler for Node.js)
*   **Testing:** `vitest` (Fast, native TypeScript testing framework)
*   **Environment Variables:** `dotenv`

### 2. File Structure

```text
forma/
├── package.json
├── tsconfig.json
├── tsup.config.ts
├── bin/
│   └── forma.js             # Executable entry point
├── src/
│   ├── cli.ts               # Commander.js CLI definitions
│   ├── parser/
│   │   ├── index.ts         # Parses .forma files into an AST/Object
│   │   └── types.ts         # TypeScript interfaces for the DSL
│   ├── compiler/
│   │   └── index.ts         # Transforms parsed DSL into LLM payloads (JSON Schema, Prompts)
│   ├── runner/
│   │   └── index.ts         # Executes the compiled payload against LLM APIs
│   └── utils/
│       └── logger.ts        # CLI console output formatting
├── examples/
│   └── generate_api.forma   # Example DSL file
└── tests/
    └── parser.test.ts       # Unit tests for the compiler
```

### 3. Step-by-Step Initialization Commands

Run these commands sequentially in your terminal to scaffold the project:

```bash
# 1. Initialize project
mkdir forma && cd forma
npm init -y

# 2. Install production dependencies
npm install commander zod dotenv openai @anthropic-ai/sdk @google/genai

# 3. Install development dependencies
npm install -D typescript @types/node tsx tsup vitest

# 4. Scaffold TypeScript config
npx tsc --init

# 5. Create directory structure
mkdir -p bin src/parser src/compiler src/runner src/utils examples tests

# 6. Create core files
touch bin/forma.js src/cli.ts src/parser/index.ts src/parser/types.ts src/compiler/index.ts src/runner/index.ts src/utils/logger.ts examples/generate_api.forma tsup.config.ts

# 7. Make the CLI executable
chmod +x bin/forma.js
```

### 4. Core Logic & Boilerplate Code

#### `package.json` (Updates)
Add the `bin` field and build scripts to your `package.json`:
```json
{
  "name": "forma",
  "version": "1.0.0",
  "main": "dist/cli.js",
  "bin": {
    "forma": "./bin/forma.js"
  },
  "scripts": {
    "build": "tsup src/cli.ts --format cjs --clean",
    "dev": "tsx src/cli.ts",
    "test": "vitest"
  }
}
```

#### `tsup.config.ts`
```typescript
import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/cli.ts'],
  format: ['cjs'],
  target: 'node20',
  clean: true,
});
```

#### `bin/forma.js`
```javascript
#!/usr/bin/env node
require('../dist/cli.js');
```

#### `src/parser/types.ts`
```typescript
export interface FormaAST {
  system: string;
  model?: string;
  input: Record<string, string>;
  output: Record<string, string>;
}
```

#### `src/parser/index.ts`
*(A simplified naive parser for MVP. Assumes a YAML-like or strict block structure for the `.forma` file).*
```typescript
import { readFileSync } from 'fs';
import { FormaAST } from './types';

export function parseFormaFile(filePath: string): FormaAST {
  const content = readFileSync(filePath, 'utf-8');
  
  // MVP Regex-based parser for block extraction
  const systemMatch = content.match(/system:\s*"([^"]+)"/);
  const modelMatch = content.match(/model:\s*"([^"]+)"/);
  
  // In a real implementation, use a proper parser like Peggy or YAML.
  // For this boilerplate, we'll mock the parsed output based on the expected structure.
  if (!systemMatch) throw new Error("Syntax Error: Missing 'system' directive.");

  return {
    system: systemMatch[1],
    model: modelMatch ? modelMatch[1] : 'gpt-4o',
    input: { user_query: 'string' }, // Mocked for MVP
    output: { endpoint: 'string', method: 'string' } // Mocked for MVP
  };
}
```

#### `src/compiler/index.ts`
```typescript
import { FormaAST } from '../parser/types';

export interface CompiledPayload {
  model: string;
  messages: { role: string; content: string }[];
  response_format: object;
}

export function compileToPayload(ast: FormaAST): CompiledPayload {
  // Convert AST output schema to JSON Schema for LLM Structured Outputs
  const properties: Record<string, any> = {};
  for (const [key, type] of Object.entries(ast.output)) {
    properties[key] = { type: type === 'string' ? 'string' : 'object' };
  }

  const jsonSchema = {
    type: "json_schema",
    json_schema: {
      name: "forma_output",
      schema: {
        type: "object",
        properties,
        required: Object.keys(ast.output),
        additionalProperties: false
      },
      strict: true
    }
  };

  return {
    model: ast.model || 'gpt-4o',
    messages: [
      { role: 'system', content: ast.system },
      // User prompt injection point
    ],
    response_format: jsonSchema
  };
}
```

#### `src/cli.ts`
```typescript
import { Command } from 'commander';
import { parseFormaFile } from './parser';
import { compileToPayload } from './compiler';
import { writeFileSync } from 'fs';

const program = new Command();

program
  .name('forma')
  .description('Forma CLI - Compile strongly typed LLM prompts')
  .version('1.0.0');

program
  .command('build')
  .description('Compile a .forma file into an API payload')
  .argument('<file>', 'Path to the .forma file')
  .action((file) => {
    try {
      console.log(`Analyzing ${file}...`);
      const ast = parseFormaFile(file);
      const payload = compileToPayload(ast);
      
      const outFile = file.replace('.forma', '.json');
      writeFileSync(outFile, JSON.stringify(payload, null, 2));
      
      console.log(`✅ Successfully compiled to ${outFile}`);
    } catch (error: any) {
      console.error(`❌ Build failed: ${error.message}`);
      process.exit(1);
    }
  });

program
  .command('test')
  .description('Execute a .forma file against an LLM and assert outputs')
  .argument('<file>', 'Path to the .forma file')
  .action((file) => {
    console.log(`Executing ${file}... (Runner implementation pending)`);
    // 1. Parse -> 2. Compile -> 3. Inject mock input -> 4. Call OpenAI API -> 5. Validate JSON response
  });

program.parse();
```

#### `examples/generate_api.forma`
```text
system: "You are an expert API designer. Generate API endpoints based on user requirements."
model: "gpt-4o"

input:
  user_query: string

output:
  endpoint: string
  method: string
```
