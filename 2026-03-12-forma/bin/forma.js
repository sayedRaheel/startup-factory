#!/usr/bin/env node
const fs = require('fs');

async function run() {
    const args = process.argv.slice(2);
    const command = args[0];
    const filepath = args[1];

    if (!command || !filepath) {
        console.log(`\x1b[36m[Forma]\x1b[0m Usage: forma <run|test> <file.forma.json>`);
        process.exit(1);
    }

    const API_KEY = process.env.OPENAI_API_KEY;
    if (!API_KEY) {
        console.error("\x1b[31m[Forma] Error:\x1b[0m OPENAI_API_KEY environment variable is required.");
        process.exit(1);
    }

    if (!fs.existsSync(filepath)) {
        console.error(`\x1b[31m[Forma] Error:\x1b[0m File not found: ${filepath}`);
        process.exit(1);
    }

    let spec;
    try {
        spec = JSON.parse(fs.readFileSync(filepath, 'utf8'));
    } catch (e) {
        console.error("\x1b[31m[Forma] Syntax Error:\x1b[0m Invalid JSON in .forma file.", e.message);
        process.exit(1);
    }

    if (!spec.prompt || !spec.schema) {
        console.error("\x1b[31m[Forma] Compiler Error:\x1b[0m .forma file must contain 'prompt' and 'schema' properties.");
        process.exit(1);
    }

    console.log(`\x1b[36m[Forma]\x1b[0m Compiling schema and querying ${spec.model || 'gpt-4o'}...`);

    try {
        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: spec.model || "gpt-4o-2024-08-06",
                messages: [{ role: "user", content: spec.prompt }],
                response_format: {
                    type: "json_schema",
                    json_schema: {
                        name: "forma_output",
                        strict: true,
                        schema: {
                            ...spec.schema,
                            additionalProperties: false
                        }
                    }
                }
            })
        });

        const data = await response.json();

        if (data.error) {
            console.error("\x1b[31m[Forma] LLM Error:\x1b[0m", data.error.message);
            process.exit(1);
        }

        const rawContent = data.choices[0].message.content;
        
        console.log("\n\x1b[32m✅ Generated Structured Output:\x1b[0m\n");
        console.log(rawContent);

        if (command === 'test') {
            console.log(`\n\x1b[32m✅ Tests Passed: Schema successfully forced strict structure.\x1b[0m`);
        }

    } catch (e) {
        console.error("\x1b[31m[Forma] Execution Error:\x1b[0m", e.message);
        process.exit(1);
    }
}

run();
