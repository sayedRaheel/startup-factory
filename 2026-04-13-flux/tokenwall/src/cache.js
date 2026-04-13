const db = require('./db');
const crypto = require('crypto');

/**
 * Parses payload for embedded file markers, hashes them, and checks the local cache.
 * Strips unchanged file content to save token bandwidth.
 */
async function processSemanticCache(payload) {
    if (!payload || !Array.isArray(payload.messages)) {
        return payload;
    }
    
    for (let msg of payload.messages) {
        if (msg.content && typeof msg.content === 'string') {
            // Regex to match <file name="path">...</file>
            const fileRegex = /<file name="([^"]+)">([\s\S]*?)<\/file>/g;
            
            msg.content = msg.content.replace(fileRegex, (match, filepath, content) => {
                const hash = crypto.createHash('sha256').update(content).digest('hex');
                const existing = db.prepare(`SELECT hash FROM file_cache WHERE filepath = ?`).get(filepath);
                
                if (existing && existing.hash === hash) {
                    return `<TokenWall: Context unchanged for ${filepath}. Use cached embedding.>`;
                } else {
                    db.prepare(`
                        INSERT INTO file_cache (filepath, hash) 
                        VALUES (?, ?) 
                        ON CONFLICT(filepath) DO UPDATE SET hash=excluded.hash, last_seen=CURRENT_TIMESTAMP
                    `).run(filepath, hash);
                    return match;
                }
            });
        }
    }
    return payload;
}

module.exports = { processSemanticCache };
