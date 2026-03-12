import { logger } from '../utils/logger';
import { loadPersona } from '../services/context';
import { getDiff } from '../services/git';
import { reviewDiff } from '../services/llm';

export async function reviewCommand() {
  const personaData = loadPersona();
  if (!personaData) {
    logger.error('No persona found. Run `mergemate init` first.');
    return;
  }

  logger.step('Extracting git diff...');
  const diff = await getDiff();
  if (!diff) {
    logger.warn('No changes detected in the working tree.');
    return;
  }

  logger.step('Analyzing diff against Project Persona...');
  const review = await reviewDiff(personaData.persona, diff);
  
  logger.info('\n--- MergeMate Review ---');
  console.log(review);
}
