**Root Cause Analysis:**
The test execution failed because the original builder script generated `test.sh` inside the `squelch/` subdirectory instead of the root workspace directory. The automated testing environment expects `test.sh` to exist at `./test.sh` to begin validation. Since the file was hidden in a subdirectory, the runner returned a "not found" error. The fix ensures that `test.sh` is generated at the root level, navigates to the proper directory, securely installs dependencies without user prompts, and performs rigorous end-to-end testing by compiling/running the underlying code.

**Fixed Builder Script:**
```bash
#!/usr/bin/env bash
set -e

echo "Building Squelch MCP project files..."

# Create project structure
mkdir -p squelch/src

# Generate package.json
cat << 'EOF' > squelch/package.json
{
  "name": "squelch",
  "version": "1.0.0",
  "description": "An MCP server that sanitizes text and shell outputs.",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "dependencies": {
    "dotenv": "^16.4.5"
  }
}
EOF

# Generate src/index.js
cat << 'EOF' > squelch/src/index.js
const readline = require('readline');
const { exec } = require('child_process');
const { Vault } = require('./vault.js');
const { Engine } = require('./engine.js');
const { createResponse } = require('./mcp.js');

// Squelch operates via stdin/stdout. Stderr is safe for debugging.
process.stderr.write("Squelch MCP Server initialized.\n");

const vault = new Vault();
const engine = new Engine();

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

rl.on('line', (line) => {
    if (!line.trim()) return;

    let req;
    try {
        req = JSON.parse(line);
    } catch (e) {
        process.stderr.write(`Parse error: ${e.message}\n`);
        return;
    }

    const id = req.id !== undefined ? req.id : null;

    if (req.method === 'initialize') {
        const res = createResponse(id, {
            protocolVersion: "2024-11-05",
            capabilities: { tools: {} },
            serverInfo: { name: "squelch", version: "1.0.0" }
        });
        process.stdout.write(JSON.stringify(res) + '\n');
    } else if (req.method === 'tools/list') {
        const res = createResponse(id, {
            tools: [{
                name: "squelched_shell",
                description: "Execute a shell command with smart truncation and secret redaction.",
                inputSchema: {
                    type: "object",
                    properties: {
                        command: { type: "string" }
                    },
                    required: ["command"]
                }
            }]
        });
        process.stdout.write(JSON.stringify(res) + '\n');
    } else if (req.method === 'tools/call') {
        const params = req.params;
        if (params && params.name === 'squelched_shell') {
            const cmdStr = (params.arguments && params.arguments.command) ? params.arguments.command : "";
            
            // Execute command securely
            exec(cmdStr, (error, stdout, stderr) => {
                const rawOut = stdout || '';
                const rawErr = stderr || '';
                const combined = `STDOUT:\n${rawOut}\nSTDERR:\n${rawErr}`;

                // 1. Truncate (keep max 100 lines)
                const processed = engine.process(combined, 100);
                // 2. Redact Secrets
                const sanitized = vault.redact(processed);

                const res = createResponse(id, {
                    content: [{
                        type: "text",
                        text: sanitized
                    }]
                });
                
                // Reply strictly on stdout
                process.stdout.write(JSON.stringify(res) + '\n');
            });
        } else {
            const res = createResponse(id, null, { code: -32601, message: "Method not found" });
            process.stdout.write(JSON.stringify(res) + '\n');
        }
    } else {
        const res = createResponse(id, null, { code: -32601, message: "Method not found" });
        process.stdout.write(JSON.stringify(res) + '\n');
    }
});
EOF

# Generate src/engine.js
cat << 'EOF' > squelch/src/engine.js
class Engine {
    constructor() {
        // Standard regex to strip terminal colors and formatting
        this.ansiRegex = /\x1b\[[0-9;]*m/g;
    }

    process(raw, maxLines) {
        const clean = raw.replace(this.ansiRegex, '');
        const lines = clean.split('\n');

        if (lines.length <= maxLines) {
            return clean;
        }

        // Keep 20% at the top, 80% at the bottom (errors are usually at the bottom)
        const topCount = Math.floor(maxLines * 0.2);
        const bottomCount = maxLines - topCount;
        const omitted = lines.length - maxLines;

        const topLines = lines.slice(0, topCount).join('\n');
        const bottomLines = lines.slice(lines.length - bottomCount).join('\n');

        return `${topLines}\n\n... [SQUELCHED ${omitted} LINES] ...\n\n${bottomLines}`;
    }
}

module.exports = { Engine };
EOF

# Generate src/vault.js
cat << 'EOF' > squelch/src/vault.js
const dotenv = require('dotenv');
const fs = require('fs');

class Vault {
    constructor() {
        const secrets = new Set();
        
        // 1. Harvest from current .env
        if (fs.existsSync('.env')) {
            const envConfig = dotenv.parse(fs.readFileSync('.env'));
            for (const val of Object.values(envConfig)) {
                const trimmed = val.trim();
                // Trade-off: Do not redact short strings to avoid corrupting standard text
                if (trimmed.length >= 6) {
                    // Escape literal regex characters
                    secrets.add(trimmed.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
                }
            }
        }
        
        // 2. Add standard entropy patterns (AWS keys, JWTs, NPM tokens)
        secrets.add('AKIA[0-9A-Z]{16}');
        secrets.add('eyJh[a-zA-Z0-9\\-_]+\\.[a-zA-Z0-9\\-_]+\\.[a-zA-Z0-9\\-_]+');
        secrets.add('npm_[a-zA-Z0-9]{36}');
        
        if (secrets.size === 0) {
            this.redactionRegex = null;
        } else {
            const pattern = Array.from(secrets).join('|');
            this.redactionRegex = new RegExp(`(${pattern})`, 'g');
        }
    }
    
    redact(input) {
        if (this.redactionRegex) {
            return input.replace(this.redactionRegex, '[REDACTED_SECRET]');
        }
        return input;
    }
}

module.exports = { Vault };
EOF

# Generate src/mcp.js
cat << 'EOF' > squelch/src/mcp.js
function createResponse(id, result = null, error = null) {
    const res = { jsonrpc: "2.0", id: id !== undefined ? id : null };
    if (error) {
        res.error = error;
    } else if (result !== null) {
        res.result = result;
    }
    return res;
}

module.exports = { createResponse };
EOF

# Create the master test.sh in the ROOT directory
cat << 'EOF' > test.sh
#!/usr/bin/env bash
set -e

echo "Starting rigorous testing..."

# Navigate to the project directory
cd squelch

# 1. Install dependencies (Requires internet / NPM)
npm install --silent

# 2. Setup environment with mocked secrets to test redaction
echo "SUPER_SECRET_KEY=1234567890abcdef" > .env
echo "SHORT=123" >> .env

# 3. Create test input imitating MCP JSON-RPC messages
cat << 'JSON' > test_input.jsonl
{"jsonrpc": "2.0", "id": 1, "method": "initialize"}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "squelched_shell", "arguments": {"command": "echo 'Testing secret: 1234567890abcdef and short: 123'"}}}
JSON

echo "Running Squelch tests..."

# 4. Attempt to run the execution code
node src/index.js < test_input.jsonl > test_output.jsonl || {
    echo "ERROR: Failed to run Squelch MCP Server."
    exit 1
}

echo "--- Test Output ---"
cat test_output.jsonl
echo "-------------------"

# 5. Ensure that there was no Vaporware output
if grep -q "1234567890abcdef" test_output.jsonl; then
    echo "TEST FAILED: Secret was exposed in the output!"
    exit 1
fi

if grep -q "\[REDACTED_SECRET\]" test_output.jsonl; then
    echo "TEST PASSED: Long secret successfully redacted."
else
    echo "TEST FAILED: Redaction placeholder not found!"
    exit 1
fi

if grep -q "short: 123" test_output.jsonl; then
    echo "TEST PASSED: Short text (< 6 chars) was preserved as expected."
else
    echo "TEST FAILED: Short text was improperly redacted."
    exit 1
fi

echo "All tests completed successfully. Zero vaporware confirmed."
exit 0
EOF

# Make test script executable
chmod +x test.sh

echo "Build complete. test.sh has been written to the root directory."
```
