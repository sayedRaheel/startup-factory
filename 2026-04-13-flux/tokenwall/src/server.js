const express = require('express');
const { handleProxyRequest } = require('./proxy');

/**
 * Ignites the Express application binding the interceptor router.
 */
function start(port) {
    const app = express();
    
    // Parse JSON streams optimally
    app.use(express.json({ limit: '50mb' }));

    // Catch-all route mechanism
    app.all('*', handleProxyRequest);

    app.listen(port, () => {
        console.log(`[TokenWall] Ignited. Routing on localhost:${port}`);
    });
}

module.exports = { start };
