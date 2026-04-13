```bash
#!/usr/bin/env bash
set -e

echo "🔨 Forge is building the Grip CLI prototype..."

# 1. Create project directories
mkdir -p grip/src
mkdir -p grip/docs/research
cd grip

# 2. Initialize Node.js project and dependencies
npm init -y > /dev/null
npm install toml > /dev/null
npm pkg set bin.grip="./src/main.js" > /dev/null

# 3. Generate source files

cat << 'EOF' > src/models.js
class GripConfig {
    constructor(context = null, rules = [], bannedPatterns = []) {
        this.context = context;
        this.rules = rules;
        this.bannedPatterns = bannedPatterns;
    }

    merge(child) {
        if (child.context) {
            this.context = child.context;
        }
        this.rules = this.rules.concat(child.rules);
        this.bannedPatterns = this.bannedPatterns.concat(child.bannedPatterns);
        return this;
    }
}

module.exports = { GripConfig };
EOF

cat << 'EOF' > src/cli.js
function parseCli() {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.error("Usage: grip <init|pipe|validate>");
        process.exit(1);
    }
    return args[0];
}

module.exports = { parseCli };
EOF

cat << 'EOF' > src/context.js
const fs = require('fs');
const path = require('path');
const toml = require('toml');
const { GripConfig } = require('./models');

function compileContext() {
    let currentDir = process.cwd();
    const configs = [];

    while (true) {
        const gripPath = path.join(currentDir, '.grip.toml');
        if (fs.existsSync(gripPath)) {
            const content = fs.readFileSync(gripPath, 'utf8');
            try {
                const parsed = toml.parse(content);
                const config = new GripConfig(
                    parsed.context || null,
                    parsed.rules || [],
                    parsed.banned_patterns || []
                );
                configs.push(config);
            } catch (err) {
                console.error(`Error parsing ${gripPath}:`, err.message);
                process.exit(1);
            }
        }

        const gitPath = path.join(currentDir, '.git');
        const parentDir = path.dirname(currentDir);
        // Break if we hit a git repo or system root
        if (fs.existsSync(gitPath) || currentDir === parentDir) {
            break;
        }
        currentDir = parentDir;
    }

    // Reverse to merge from root down to deepest child
    configs.reverse();

    let finalConfig = new GripConfig();
    for (const c of configs) {
        finalConfig = finalConfig.merge(c);
    }

    return finalConfig;
}

function generatePrompt(config) {
    let prompt = "### SYSTEM CONTEXT ###\n";
    if (config.context && config.context.domain) {
        prompt += `Domain: ${config.context.domain}\n`;
    }
    prompt += "\n### RULES ###\n";
    for (const rule of config.rules) {
        prompt += `- ${rule}\n`;
    }
    return prompt;
}

module.exports = { compileContext, generatePrompt };
EOF

cat << 'EOF' > src/git.js
const { execSync } = require('child_process');

function getStagedDiff() {
    try {
        return execSync('git diff --cached', { encoding: 'utf8' });
    } catch (err) {
        console.error("Failed to execute git diff");
        process.exit(1);
    }
}

module.exports = { getStagedDiff };
EOF

cat << 'EOF' > src/linter.js
const { getStagedDiff } = require('./git');

function validateDiff(config) {
    const diff = getStagedDiff();
    
    // Extract only added lines from the diff
    const addedLines = diff.split('\n')
        .filter(line => line.startsWith('+') && !line.startsWith('+++'));

    const violations = [];

    for (const pattern of config.bannedPatterns) {
        try {
            const regex = new RegExp(pattern);
            for (const line of addedLines) {
                if (regex.test(line)) {
                    violations.push(`Matched banned pattern '${pattern}' in line: ${line}`);
                }
            }
        } catch (err) {
            console.error(`Invalid regex pattern: ${pattern}`);
            process.exit(1);
        }
    }

    if (violations.length > 0) {
        for (const v of violations) {
            console.error(`❌ LINT ERROR: ${v}`);
        }
        console.error(`Grip validation failed with ${violations.length} violations.`);
        process.exit(1);
    }
}

module.exports = { validateDiff };
EOF

cat << 'EOF' > src/main.js
#!/usr/bin/env node

const fs = require('fs');
const { parseCli } = require('./cli');
const { compileContext, generatePrompt } = require('./context');
const { validateDiff } = require('./linter');

function main() {
    const command = parseCli();

    if (command === 'init') {
        const defaultToml = `[context]
domain = "core"
description = "Auto-generated grip boundary"

rules = [
    "Use React Router v6"
]

banned_patterns = [
    "lodash"
]
`;
        fs.writeFileSync('.grip.toml', defaultToml.trim() + '\n', 'utf8');
        console.log("✅ Initialized .grip.toml");
    } else if (command === 'pipe') {
        const config = compileContext();
        const prompt = generatePrompt(config);
        process.stdout.write(prompt + '\n');
    } else if (command === 'validate') {
        const config = compileContext();
        validateDiff(config);
        console.log("✅ Grip validation passed. No hallucinatory dependencies found.");
    } else {
        console.error(`Unknown command: ${command}`);
        process.exit(1);
    }
}

main();
EOF

chmod +x src/main.js

# 4. Generate README and Documentation placeholders
cat << 'EOF' > README.md
# Grip CLI

### Problem Statement
Monolithic `CLAUDE.md` files fail to scale across large repositories. AI context becomes bloated, leading to hallucinations and token waste. We need a hyper-fast, localized CLI tool to dynamically route context based on the current file path and architectural boundaries.

### Solution
`grip` uses distributed `.grip.toml` files scattered across the file tree. It walks up the directory structure, merges configurations, and generates a tailored prompt. It also hooks into Git to validate staged diffs against boundary-specific banned patterns.

### Usage
- `npx grip init`: Initialize a `.grip.toml` in the current directory.
- `npx grip pipe`: Generate and print the merged context prompt.
- `npx grip validate`: Lint staged git changes against banned patterns.

### Research & Architecture
- [Scout Analysis](./docs/research/1-scout-analysis.md)
- [PRD](./docs/research/2-prd.md)
- [Tech Spec](./docs/research/3-tech-spec.md)
- [Builder Code](./docs/research/4-builder-code.md)
EOF

cat << 'EOF' > docs/research/1-scout-analysis.md
# Scout Analysis
Context routing mechanism local git state analysis.
EOF

cat << 'EOF' > docs/research/2-prd.md
# PRD
Dynamic context routing for AI Product Requirements Document.
EOF

cat << 'EOF' > docs/research/3-tech-spec.md
# Tech Spec
Architectural boundaries mapped to TOML configs.
EOF

cat << 'EOF' > docs/research/4-builder-code.md
# Builder Code
Implementation artifacts, structural logs, and testing guidelines.
EOF

# 5. Generate Test Execution Script
cat << 'EOF' > test.sh
#!/usr/bin/env bash
set -e

echo "🚀 Running Grip test suite..."

# Setup an isolated dummy git repo
rm -rf .git
git init > /dev/null
git config user.email "test-forge@example.com"
git config user.name "Forge"
echo "init" > init.txt
git add init.txt
git commit -m "Initial commit" > /dev/null

# 1. Test init
node src/main.js init
if [ ! -f ".grip.toml" ]; then
    echo "❌ Test Failed: .grip.toml not created."
    exit 1
fi

# Override .grip.toml with specific test assertions
cat << 'INNER_EOF' > .grip.toml
[context]
domain = "AuthDomain"
description = "Test description"

rules = [
    "Always validate tokens"
]

banned_patterns = [
    "banned_function_call"
]
INNER_EOF

# 2. Test pipe
OUTPUT=$(node src/main.js pipe)
if [[ "$OUTPUT" != *"Domain: AuthDomain"* ]] || [[ "$OUTPUT" != *"- Always validate tokens"* ]]; then
    echo "❌ Test Failed: Pipe output missing expected context."
    echo "Got: $OUTPUT"
    exit 1
fi
echo "✅ Pipe output verified."

# 3. Test validate (Failure case)
echo "banned_function_call()" > bad_code.js
git add bad_code.js

# We expect this to fail, so temporarily disable exit-on-error
set +e
node src/main.js validate > /dev/null 2>&1
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 0 ]; then
    echo "❌ Test Failed: Validation should have failed on banned pattern."
    exit 1
fi
echo "✅ Linter correctly caught banned pattern."

# 4. Test validate (Success case)
git reset HEAD bad_code.js > /dev/null
rm bad_code.js
echo "allowed_function_call()" > good_code.js
git add good_code.js
node src/main.js validate > /dev/null

echo "✅ All tests passed successfully!"
EOF

chmod +x test.sh

# Execute the test script immediately to prove correctness
./test.sh
```
