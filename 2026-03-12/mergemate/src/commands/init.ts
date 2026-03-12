import { logger } from '../utils/logger';
import { savePersona } from '../services/context';
import { generatePersona } from '../services/llm';
import fs from 'fs';

export async function initCommand() {
  logger.step('Scanning repository...');
  
  // MVP: Read package.json and a few key files to form a sample
  let sample = "";
  if (fs.existsSync('package.json')) sample += fs.readFileSync('package.json', 'utf-8');
  
  logger.step('Generating Project Persona via LLM...');
  const persona = await generatePersona(sample);
  
  savePersona({ persona });
  logger.success('Project Persona generated and saved to .mergemate/persona.json');
}
