#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');

async function run() {
    const API_KEY = process.env.OPENAI_API_KEY;
    
    if (!API_KEY) {
        console.error("\x1b[31m[MergeGuard] Error:\x1b[0m OPENAI_API_KEY environment variable is required.");
        process.exit(1);
    }

    let config = {
        model: "gpt-4o",
        instructions: "You are MergeGuard, an expert code reviewer. Analyze this diff. Look for obvious bugs, security issues, and style violations. Format as Markdown. Be extremely concise. If the code is dangerously broken, output exactly: 'MERGE_BLOCKED'."
    };

    if (fs.existsSync('.mergeguard.json')) {
        try {
            const fileConf = JSON.parse(fs.readFileSync('.mergeguard.json', 'utf8'));
            config = { ...config, ...fileConf };
        } catch (e) {
            console.warn("\x1b[33m[MergeGuard] Warning:\x1b[0m Could not parse .mergeguard.json, using defaults.");
        }
    }

    try {
        console.log("\x1b[36m[MergeGuard]\x1b[0m Extracting git diff...");
        
        let diff = '';
        try {
            diff = execSync('git diff --cached', { encoding: 'utf8' }).trim();
            if (!diff) {
                diff = execSync('git diff HEAD', { encoding: 'utf8' }).trim();
            }
        } catch(e) {
            console.error("\x1b[31m[MergeGuard] Error:\x1b[0m Failed to execute git diff.");
            process.exit(1);
        }

        if (!diff) {
            console.log("\x1b[32m[MergeGuard] No changes detected. Looking good!\x1b[0m");
            process.exit(0);
        }

        if (diff.length > 30000) {
            diff = diff.substring(0, 30000) + "\n... [TRUNCATED DUE TO SIZE]";
            console.warn("\x1b[33m[MergeGuard] Warning:\x1b[0m Diff is very large, truncating for review.");
        }

        console.log("\x1b[36m[MergeGuard]\x1b[0m Asking LLM for review...");
        
        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: config.model,
                messages: [
                    { role: "system", content: config.instructions },
                    { role: "user", content: `Please review the following git diff:\n\n\`\`\`diff\n${diff}\n\`\`\`` }
                ],
                temperature: 0.1
            })
        });

        const data = await response.json();

        if (data.error) {
            console.error("\x1b[31m[MergeGuard] API Error:\x1b[0m", data.error.message);
            process.exit(1);
        }

        const review = data.choices[0].message.content;
        
        console.log("\n\x1b[1m================ MERGEGUARD REVIEW ================\x1b[0m\n");
        console.log(review);
        console.log("\n\x1b[1m===================================================\x1b[0m\n");
        
        if (review.includes("MERGE_BLOCKED")) {
            console.error("\x1b[31m[MergeGuard] ⛔ Commit BLOCKED due to critical issues.\x1b[0m");
            process.exit(1);
        } else {
            console.log("\x1b[32m[MergeGuard] ✅ Code passed pre-review.\x1b[0m");
        }

    } catch (e) {
        console.error("\x1b[31m[MergeGuard] Runtime Error:\x1b[0m", e.message);
        process.exit(1);
    }
}

run();
