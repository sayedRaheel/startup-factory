import fs from 'fs';
import path from 'path';

const PERSONA_DIR = path.join(process.cwd(), '.mergemate');
const PERSONA_FILE = path.join(PERSONA_DIR, 'persona.json');

export function savePersona(personaData: any) {
  if (!fs.existsSync(PERSONA_DIR)) {
    fs.mkdirSync(PERSONA_DIR);
  }
  fs.writeFileSync(PERSONA_FILE, JSON.stringify(personaData, null, 2));
}

export function loadPersona(): any {
  if (!fs.existsSync(PERSONA_FILE)) return null;
  return JSON.parse(fs.readFileSync(PERSONA_FILE, 'utf-8'));
}
