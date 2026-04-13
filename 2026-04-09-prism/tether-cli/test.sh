#!/usr/bin/env bash
set -e

echo "Starting tests for Tether CLI..."

# Test Init Command
node src/index.js init

# Test Map Command
node src/index.js map

echo "Validating artifacts..."
if [ ! -f ".agentrc" ]; then
  echo "❌ Error: .agentrc was not generated."
  exit 1
fi

if [ ! -f ".github/SKILLS.md" ]; then
  echo "❌ Error: .github/SKILLS.md was not generated."
  exit 1
fi

if [ ! -f ".agent-context.md" ]; then
  echo "❌ Error: .agent-context.md was not generated."
  exit 1
fi

echo "✅ All required files were successfully generated."
echo "✅ Tests passed successfully. Tether is fully operational."
