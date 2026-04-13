const axios = require('axios');

/**
 * Distills extensive conversational history using local Ollama instance
 * to prevent context bloat and excessive LLM token expenditure.
 */
async function distillHistory(payload) {
    if (!payload || !Array.isArray(payload.messages) || payload.messages.length <= 10) {
        return payload;
    }
    
    const msgs = payload.messages;
    const toSummarize = msgs.slice(1, msgs.length - 2);
    const contextStr = toSummarize.map(m => `${m.role}: ${m.content}`).join('\n');
    
    try {
        // Attempt local distillation
        const response = await axios.post('http://127.0.0.1:11434/api/generate', {
            model: 'llama3',
            prompt: `Summarize this conversation concisely retaining exact facts and code logic:\n\n${contextStr}`,
            stream: false
        }, { timeout: 3000 });
        
        const summary = response.data.response;
        
        payload.messages = [
            msgs[0],
            { role: 'system', content: `[TokenWall Compressed History]: ${summary}` },
            msgs[msgs.length - 2],
            msgs[msgs.length - 1]
        ];
    } catch (err) {
        // Graceful fallback if Ollama is unreachable - pure deterministic truncation
        payload.messages = [
            msgs[0],
            { role: 'system', content: `[TokenWall History Truncated]: ${toSummarize.length} older messages omitted to preserve context window.` },
            msgs[msgs.length - 2],
            msgs[msgs.length - 1]
        ];
    }
    return payload;
}

module.exports = { distillHistory };
