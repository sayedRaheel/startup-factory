import fs from 'fs';
import path from 'path';
import { detectStack } from '../detector/stack.js';

export function initCommand() {
  const stack = detectStack();
  console.log(`🔍 Detected Stack: ${stack}`);

  const agentrcContent = `# Tether Agent Configuration
stack: ${stack}
strict_mode: true
context_file: .agent-context.md
rules:
  - Do not hallucinate dependencies.
  - Read .agent-context.md before touching any files.
  - Follow existing architectural patterns.
`;

  fs.writeFileSync('.agentrc', agentrcContent, 'utf-8');
  console.log('✅ Created .agentrc');

  fs.mkdirSync('.github', { recursive: true });

  const skillsContent = `# Agent Skills

This file defines the rigid boundaries for AI execution in this repository.
1. Context constraint: Always review \`.agent-context.md\`.
2. Execution limits: Only modify files related to the specific user prompt.
`;

  if (!fs.existsSync('.github/SKILLS.md')) {
    fs.writeFileSync('.github/SKILLS.md', skillsContent, 'utf-8');
    console.log('✅ Created .github/SKILLS.md');
  }
}
