#!/usr/bin/env bash
set -e

echo "Setting up Warden test environment sandbox..."
mkdir -p test_env
cd test_env

# Initialize dummy workspace
git init
git config user.email "test@warden.local"
git config user.name "Warden Test"

cat << 'INNER_EOF' > target.txt
buggy content
INNER_EOF

cat << 'INNER_EOF' > test_target.sh
#!/usr/bin/env bash
if grep -q "fixed content" target.txt; then
    echo "Test passed!"
    exit 0
else
    echo "Test failed: content is still buggy"
    exit 1
fi
INNER_EOF
chmod +x test_target.sh

cat << 'INNER_EOF' > dummy_agent.sh
#!/usr/bin/env bash
PROMPT="${@: -1}"
echo "Agent Received Prompt: $PROMPT"
if [[ "$PROMPT" == *"Your previous attempt failed"* ]]; then
    echo "Agent iteration 2: Fixing the file..."
    echo "fixed content" > target.txt
else
    echo "Agent iteration 1: Simulating hallucination/bug..."
    echo "still buggy content" > target.txt
fi
INNER_EOF
chmod +x dummy_agent.sh

git add target.txt test_target.sh dummy_agent.sh
git commit -m "Initial commit"

echo "Executing Warden firewall over dummy agent..."
../warden/warden run \
    --agent "./dummy_agent.sh" \
    --prompt "Fix the target.txt file" \
    --verify-cmd "./test_target.sh"

echo "Validating git merge integrity..."
if grep -q "fixed content" target.txt; then
    echo "SUCCESS: Agent bug was fixed and securely merged into main."
else
    echo "FAILURE: Fix was not merged."
    exit 1
fi

echo "Validating ledger state..."
if grep -q '"success": true' .warden/ledger.json; then
    echo "SUCCESS: Ledger correctly recorded the successful loop."
else
    echo "FAILURE: Ledger state invalid."
    exit 1
fi

echo "All tests completed with Exit Code 0."
