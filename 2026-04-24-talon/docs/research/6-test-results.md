Starting rigorous testing...
Running Squelch tests...
Squelch MCP Server initialized.
--- Test Output ---
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"squelch","version":"1.0.0"}}}
{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"squelched_shell","description":"Execute a shell command with smart truncation and secret redaction.","inputSchema":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}]}}
{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"STDOUT:\nTesting secret: [REDACTED_SECRET] and short: 123\n\nSTDERR:\n"}]}}
-------------------
TEST PASSED: Long secret successfully redacted.
TEST PASSED: Short text (< 6 chars) was preserved as expected.
All tests completed successfully. Zero vaporware confirmed.
