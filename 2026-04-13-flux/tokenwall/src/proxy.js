const { isUnderBudget, recordUsage } = require('./firewall');
const { processSemanticCache } = require('./cache');
const { distillHistory } = require('./compress');
const axios = require('axios');
const { getEncoding } = require('js-tiktoken');

/**
 * Calculates exact token counts using cl100k_base (OpenAI default)
 * Multiplier averages $0.002 per 1k tokens for combined IO cost modeling.
 */
function estimateCost(text) {
    try {
        const enc = getEncoding("cl100k_base");
        const tokens = enc.encode(text).length;
        return (tokens / 1000) * 0.002;
    } catch (e) {
        // Fallback length heuristic
        return (text.split(/\s+/).length * 1.3 / 1000) * 0.002;
    }
}

/**
 * Core middleware: validates budget, intercepts body, caches, compresses, and forwards.
 */
async function handleProxyRequest(req, res) {
    if (!isUnderBudget()) {
        console.error("[TokenWall] FIREWALL KILLED REQUEST: Daily budget exceeded.");
        return res.status(402).json({ error: "Payment Required: Daily budget exceeded" });
    }

    let payload = req.body;
    
    // 1. Semantic Caching
    payload = await processSemanticCache(payload);
    
    // 2. History Compression
    payload = await distillHistory(payload);

    // 3. Extrapolate Target (Defaulting to OpenAI for V1)
    const targetUrl = `https://api.openai.com${req.originalUrl}`;
    const headers = { ...req.headers };
    
    // Strip headers that interfere with proper forwarding
    delete headers['host'];
    delete headers['content-length'];

    try {
        // Pre-compute inbound cost
        const reqString = JSON.stringify(payload);
        const reqCost = estimateCost(reqString);
        recordUsage(reqCost);

        const response = await axios({
            method: req.method,
            url: targetUrl,
            headers: headers,
            data: payload,
            responseType: 'stream',
            validateStatus: () => true
        });

        // Forward status and headers
        res.status(response.status);
        for (const [key, value] of Object.entries(response.headers)) {
            res.setHeader(key, value);
        }

        // Intercept SSE Stream to calculate exact outbound response token cost
        let resData = '';
        response.data.on('data', (chunk) => {
            resData += chunk.toString();
        });
        
        response.data.on('end', () => {
            const resCost = estimateCost(resData);
            recordUsage(resCost);
        });

        // Stream response natively back to client
        response.data.pipe(res);
        
    } catch (error) {
        console.error("[TokenWall] Proxy forwarding error:", error.message);
        res.status(502).json({ error: "Bad Gateway" });
    }
}

module.exports = { handleProxyRequest };
