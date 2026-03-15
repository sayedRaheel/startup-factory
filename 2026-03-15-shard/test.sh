#!/bin/bash

# Ralph's Zero Vaporware Test Suite for the project.
echo "--- Running Project Test Suite ---"

TEST_FAILED=0

# Test 1: Check if the 'devscope' directory exists.
echo "Test 1: Verifying 'devscope' directory..."
if [ -d "./devscope" ]; then
    echo "SUCCESS: 'devscope' directory found."
else
    echo "FAILED: 'devscope' directory not found."
    TEST_FAILED=1
fi

# Test 2: Check if 'devscope/main.sh' exists and is executable.
echo "Test 2: Verifying 'devscope/main.sh' file..."
if [ -f "./devscope/main.sh" ] && [ -x "./devscope/main.sh" ]; then
    echo "SUCCESS: 'devscope/main.sh' exists and is executable."
else
    echo "FAILED: 'devscope/main.sh' is missing or not executable."
    TEST_FAILED=1
fi

# Test 3: Run 'devscope/main.sh' and check its output. (Smoke test)
echo "Test 3: Executing 'devscope/main.sh' and checking output..."
if [ "$TEST_FAILED" -eq 0 ]; then # Only run if prior tests passed to avoid cascading errors
    MAIN_OUTPUT=$(./devscope/main.sh)
    EXPECTED_OUTPUT="Hello from DevScope! (Version: 1.0)"
    if [ "$MAIN_OUTPUT" == "$EXPECTED_OUTPUT" ]; then
        echo "SUCCESS: 'devscope/main.sh' ran with expected output: '$MAIN_OUTPUT'."
    else
        echo "FAILED: 'devscope/main.sh' output mismatch. Expected: '$EXPECTED_OUTPUT', Got: '$MAIN_OUTPUT'."
        TEST_FAILED=1
    fi
else
    echo "Skipping Test 3 due to previous failures."
fi

# Final Verdict
if [ "$TEST_FAILED" -eq 0 ]; then
    echo "--- All Project Tests PASSED ---"
    exit 0
else
    echo "--- Project Test Suite FAILED ---"
    exit 1
fi
