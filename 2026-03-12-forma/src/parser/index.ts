import { readFileSync } from 'fs';
import { FormaAST } from './types';

export function parseFormaFile(filePath: string): FormaAST {
  const content = readFileSync(filePath, 'utf-8');
  
  // MVP Regex-based parser for block extraction
  const systemMatch = content.match(/system:\s*"([^"]+)"/);
  const modelMatch = content.match(/model:\s*"([^"]+)"/);
  
  // In a real implementation, use a proper parser like Peggy or YAML.
  // For this boilerplate, we'll mock the parsed output based on the expected structure.
  if (!systemMatch) throw new Error("Syntax Error: Missing 'system' directive.");

  return {
    system: systemMatch[1],
    model: modelMatch ? modelMatch[1] : 'gpt-4o',
    input: { user_query: 'string' }, // Mocked for MVP
    output: { endpoint: 'string', method: 'string' } // Mocked for MVP
  };
}
