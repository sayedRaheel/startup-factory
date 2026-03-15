import OpenAI from 'openai';
import { env } from './config.js';
const openai = new OpenAI({ apiKey: env.OPENAI_API_KEY });
export async function generateFingerprint(commitHistory, fileList) {
    const prompt = `Analyze the following commit history and file structure to determine the team's coding conventions, architectural patterns, and naming styles.
  
Files:
${fileList.slice(0, 100).join('\n')}

Commits:
${commitHistory.join('\n')}

Output a concise summary of the repository's stylistic fingerprint.`;
    const response = await openai.chat.completions.create({
        model: 'gpt-4o',
        messages: [{ role: 'user', content: prompt }],
    });
    return response.choices[0].message.content || 'Default fingerprint';
}
export async function reviewDiff(diff, fingerprint) {
    const prompt = `You are a strict code reviewer. Review the following PR diff against the team's historical fingerprint.
  
Team Fingerprint:
${fingerprint}

PR Diff:
${diff}

If the code violates the fingerprint, provide the exact auto-fix code block. Otherwise, reply with "LGTM".`;
    const response = await openai.chat.completions.create({
        model: 'gpt-4o',
        messages: [{ role: 'user', content: prompt }],
    });
    return response.choices[0].message.content || 'LGTM';
}
