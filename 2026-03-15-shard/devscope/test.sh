#!/bin/bash
set -eo pipefail # Exit on error, exit if a command in a pipeline fails

echo "--- Running DevScope Integration Tests ---"

# Save current directory and go back to it later
ORIG_DIR=$(pwd)
ROOT_DIR=$(dirname "$0") # Points to devscope/
cd "$ROOT_DIR"

# Create a temporary directory for the test project
TEMP_PROJECT_DIR=$(mktemp -d -t devscope-test-project-XXXX)
echo "Working in temporary project directory: $TEMP_PROJECT_DIR"
cd "$TEMP_PROJECT_DIR"

# Ensure cleanup on exit
cleanup() {
  echo "Cleaning up temporary directories..."
  rm -rf "$TEMP_PROJECT_DIR"
  cd "$ORIG_DIR" # Go back to original directory
}
trap cleanup EXIT

echo "1. Creating devscope.yaml in test project..."
cat << 'EOF_DEV_YAML' > devscope.yaml
tools:
  node:
    version: "18.17.0"
  go:
    version: "1.21.0"
  python:
    version: "3.10.0" # NOTE: Python download is a placeholder in this prototype.
  cli:
    kubectl:
      version: "1.27.0"
      url: "https://dl.k8s.io/release/v{version}/bin/linux/amd64/kubectl"
      binary: "kubectl"
    helm:
      version: "3.12.0"
      url: "https://get.helm.sh/helm-v{version}-linux-amd64.tar.gz"
      binary: "helm"

env:
  PROJECT_NAME: "DevScopeTest"
  TEST_VAR: "test_value"
EOF_DEV_YAML

echo "2. Building devscope binary for testing..."
# Build the devscope binary from the project root.
# Using 'go build -o' to place the binary in the test project's temp dir.
(cd "$ROOT_DIR" && go build -o "$TEMP_PROJECT_DIR/devscope" ./main.go)
chmod +x "$TEMP_PROJECT_DIR/devscope"

export PATH="$TEMP_PROJECT_DIR:$PATH" # Add temp devscope to PATH for easier calling

TEST_FAILED=false

echo "3. Running 'devscope fix' to install tools and set up environment..."
if ! devscope fix; then
    echo "WARNING: 'devscope fix' encountered issues. This might be due to external network failures or unavailable placeholder URLs for Python/CLI tools (e.g., if Python URL is not a real binary distribution). "
    echo "Proceeding with validation, but expect potential failures for uninstalled tools."
    # We will not exit 1 here yet, as some parts might still be testable.
    # For a real CI, this would be an immediate failure.
fi

echo "4. Running 'devscope' (validation command)..."
if devscope; then
    echo "  ✓ DevScope validation successful (after fix attempt)."
else
    echo "  ✗ DevScope validation failed (after fix attempt)."
    TEST_FAILED=true
fi

echo "5. Testing 'devscope shell-hook bash'..."
hook_script=$(devscope shell-hook bash)
if [[ -z "$hook_script" ]]; then
    echo "  ✗ Error: shell-hook script is empty."
    TEST_FAILED=true
else
    echo "  ✓ Shell hook script generated successfully."
    # Execute the hook in a subshell to avoid polluting the main test environment
    # and to simulate how it would be sourced.
    echo "  - Simulating 'cd' event with hook..."
    (
        export PATH="/usr/local/bin:/usr/bin:/bin" # Start with a clean PATH to simulate fresh shell
        export DEVSCOPE_ORIG_PATH=""
        export DEVSCOPE_ACTIVE_PROJECT_ENV_VARS=""

        # Source the generated hook script to define functions and potentially PROMPT_COMMAND
        eval "$hook_script"

        # Manually call the chpwd hook function to simulate changing into a project directory
        _devscope_chpwd_hook

        # Verify PATH update
        if [[ "$PATH" == *".devscope/bin"* ]]; then
            echo "    ✓ PATH updated successfully with .devscope/bin."
        else
            echo "    ✗ PATH not updated correctly with .devscope/bin. Current PATH: '$PATH'"
            TEST_FAILED=true
        fi

        # Verify environment variables
        if [[ "$PROJECT_NAME" == "DevScopeTest" ]]; then
            echo "    ✓ PROJECT_NAME env var set successfully."
        else
            echo "    ✗ PROJECT_NAME env var not set correctly. Got: '$PROJECT_NAME'"
            TEST_FAILED=true
        fi
        if [[ "$TEST_VAR" == "test_value" ]]; then
            echo "    ✓ TEST_VAR env var set successfully."
        else
            echo "    ✗ TEST_VAR env var not set correctly. Got: '$TEST_VAR'"
            TEST_FAILED=true
        fi

        # Simulate cd-ing out of the project to check reset logic
        echo "  - Simulating 'cd' out of project directory..."
        cd /tmp # Move to a directory without devscope.yaml
        _devscope_chpwd_hook # Call the hook again

        # Verify PATH reset
        if [[ "$PATH" != *".devscope/bin"* && "$PATH" == "/usr/local/bin:/usr/bin:/bin" ]]; then
            echo "    ✓ PATH reset correctly after leaving project."
        else
            echo "    ✗ PATH not reset correctly after leaving project. Current PATH: '$PATH'"
            TEST_FAILED=true
        fi
        # Verify environment variables unset
        if [[ -z "$PROJECT_NAME" ]]; then
            echo "    ✓ PROJECT_NAME env var unset correctly."
        else
            echo "    ✗ PROJECT_NAME env var not unset correctly. Got: '$PROJECT_NAME'"
            TEST_FAILED=true
        fi
        if [[ -z "$TEST_VAR" ]]; then
            echo "    ✓ TEST_VAR env var unset correctly."
        else
            echo "    ✗ TEST_VAR env var not unset correctly. Got: '$TEST_VAR'"
            TEST_FAILED=true
        fi
    ) || TEST_FAILED=true # Capture failure from subshell
fi

if [[ "$TEST_FAILED" == "true" ]]; then
    echo "--- DevScope Tests FAILED ---"
    exit 1
else
    echo "--- DevScope Tests PASSED ---"
    exit 0
fi

