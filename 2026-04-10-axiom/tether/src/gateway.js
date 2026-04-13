export function checkProofInPayload(payload) {
    if (payload.messages && Array.isArray(payload.messages)) {
        for (const msg of payload.messages) {
            if (msg.tool_calls && Array.isArray(msg.tool_calls)) {
                for (const tc of msg.tool_calls) {
                    if (tc.function && tc.function.name === 'prove_architecture') {
                        return true;
                    }
                }
            }
        }
    }
    return false;
}

export function stripWritePermissions(payload) {
    if (payload.tools && Array.isArray(payload.tools)) {
        payload.tools = payload.tools.filter(t => {
            return !(t.type === 'function' && t.function && t.function.name === 'write_file');
        });
    }
    return payload;
}

export function containsWriteViolation(payload) {
    // Simulated structural validation: block any write_file with 'rm -rf' or invalid JSON args
    if (payload.messages && Array.isArray(payload.messages)) {
         for (const msg of payload.messages) {
             if (msg.tool_calls && Array.isArray(msg.tool_calls)) {
                 for (const tc of msg.tool_calls) {
                     if (tc.function && tc.function.name === 'write_file') {
                         try {
                             const args = JSON.parse(tc.function.arguments || '{}');
                             if (args.content && args.content.includes("rm -rf")) {
                                 return true;
                             }
                         } catch (e) {
                             return true; // invalid arguments payload
                         }
                     }
                 }
             }
         }
    }
    return false;
}
