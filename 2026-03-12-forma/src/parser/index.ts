import { readFileSync } from 'fs';
import { FormaAST } from './types';

export function parseFormaFile(filePath: string): FormaAST {
  const content = readFileSync(filePath, 'utf-8');
  
  const systemMatch = content.match(/system:\s*"?([^"\n]+)"?/);
  const modelMatch = content.match(/model:\s*"?([^"\n]+)"?/);
  
  if (!systemMatch) throw new Error("Syntax Error: Missing 'system' directive.");

  const ast: FormaAST = {
    system: systemMatch[1],
    model: modelMatch ? modelMatch[1] : 'gpt-4o',
    input: {},
    output: {}
  };

  // Parse input block
  const inputBlock = content.match(/input\s*{([^}]+)}/);
  if (inputBlock) {
    const lines = inputBlock[1].split('\n');
    for (const line of lines) {
      const match = line.match(/^\s*([a-zA-Z0-9_]+)\s*:\s*([a-zA-Z0-9_]+)/);
      if (match) {
        ast.input[match[1]] = match[2];
      }
    }
  }

  // Parse output block
  const outputBlock = content.match(/output\s*{([^}]+)}/);
  if (outputBlock) {
    const lines = outputBlock[1].split('\n');
    for (const line of lines) {
      const match = line.match(/^\s*([a-zA-Z0-9_]+)\s*:\s*([a-zA-Z0-9_]+)/);
      if (match) {
        ast.output[match[1]] = match[2];
      }
    }
  }

  return ast;
}
