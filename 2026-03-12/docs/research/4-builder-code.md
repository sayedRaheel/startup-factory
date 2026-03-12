```bash
#!/usr/bin/env bash
set -e

echo "🚀 Scaffolding Forma CLI project..."

# 1. Initialize project
mkdir -p forma
cd forma
npm init -y

# 2. Install production dependencies
npm install commander zod dotenv openai @anthropic-ai/sdk @google/genai

# 3. Install development dependencies
npm install -D typescript @types/node tsx tsup vitest

# 4. Scaffold TypeScript config
npx tsc --init

# 5. Create directory structure
mkdir -p bin src/parser src/compiler src/runner src/utils examples tests

# 6. Update package.json configuration
npm pkg set bin.forma="./bin/forma.js"
npm pkg set main="dist/cli.js"
npm pkg set scripts.build="tsup src/cli.ts --format cjs --clean"
npm pkg set scripts.dev="tsx src/cli.ts"
npm pkg set scripts.test="vitest"

# 7. Create core files

cat << 'EOF' > tsup.config.ts
import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/cli.ts'],
  format: ['cjs'],
  target: 'node20',
  clean: true,
});
EOF

cat << 'EOF' > bin/forma.js
#!/usr/bin/env node
require('../dist/cli.js');
EOF

cat << 'EOF' > src/parser/types.ts
export interface FormaAST {
  system: string;
  model?: string;
  input: Record<string, string>;
  output: Record<string, string>;
}
EOF

cat << 'EOF' > src/parser/index.ts
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
EOF

cat << 'EOF' > src/compiler/index.ts
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
EOF

cat << 'EOF' > src/cli.ts
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
EOF

cat << 'EOF' > examples/generate_api.forma
system: "You are an expert API designer. Generate API endpoints based on user requirements."
model: "gpt-4o"

input:
  user_query: string

output:
  endpoint: string
  method: string
EOF

# Create remaining empty placeholders
touch src/runner/index.ts src/utils/logger.ts tests/parser.test.ts

# 8. Make the CLI executable
chmod +x bin/forma.js

echo "✅ Forma initialization complete!"
echo "➡️  Next steps:"
echo "   cd forma"
echo "   npm run build"
echo "   node bin/forma.js build examples/generate_api.forma"
```
