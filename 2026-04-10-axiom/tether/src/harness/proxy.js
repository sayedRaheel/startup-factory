import express from 'express';
import axios from 'axios';
import { checkProofInPayload, stripWritePermissions, containsWriteViolation } from '../gateway.js';

export function startProxy(state, port) {
    const app = express();
    app.use(express.json({ limit: '50mb' }));

    app.post('/v1/chat/completions', async (req, res) => {
        let payload = req.body;

        // 1. Inject compiled context into system prompt
        if (payload.messages && Array.isArray(payload.messages)) {
            if (payload.messages.length > 0 && payload.messages[0].role === 'system') {
                const currentContent = payload.messages[0].content || '';
                const injectedContent = `${currentContent} \n\n[TETHER STRICT CONTEXT]\n${state.compiledContext}\n[END TETHER CONTEXT]\n\nYou MUST output a JSON tool call to 'prove_architecture' before writing any files.`;
                payload.messages[0].content = injectedContent;
            }
        }

        // 2. Gatekeeper Logic
        if (!state.isProven) {
            state.isProven = checkProofInPayload(payload);
            if (!state.isProven) {
                console.warn("Agent has not proven architecture. Stripping write access.");
                payload = stripWritePermissions(payload);
            }
        } else {
            // 3. Write-Harness: Intercept write_file tool calls
            if (containsWriteViolation(payload)) {
                return res.status(400).json({
                    error: "Tether Blocked Write: Proposed diff fails local lint/type-check."
                });
            }
        }

        // Forward to real API
        try {
            const response = await axios.post(`${state.realApiBase}/v1/chat/completions`, payload, {
                headers: {
                    'Authorization': req.headers.authorization || '',
                    'Content-Type': 'application/json'
                }
            });
            res.json(response.data);
        } catch (err) {
            if (err.response) {
                // Propagate real API errors (e.g. 401 Unauthorized)
                res.status(err.response.status).json(err.response.data);
            } else {
                res.status(500).json({ error: err.message });
            }
        }
    });

    app.listen(port, () => {
        console.log(`Tether Proxy intercepting on port ${port}`);
    });
}
