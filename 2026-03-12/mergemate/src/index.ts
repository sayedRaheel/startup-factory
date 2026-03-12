import { Command } from 'commander';
import { initCommand } from './commands/init';
import { reviewCommand } from './commands/review';
import { fixCommand } from './commands/fix';

const program = new Command();

program
  .name('mergemate')
  .description('AI-powered idiomatic code refactoring CLI')
  .version('1.0.0');

program
  .command('init')
  .description('Contextualize and build a localized Project Persona')
  .action(initCommand);

program
  .command('review')
  .description('Analyze current diffs against the Project Persona')
  .action(reviewCommand);

program
  .command('fix')
  .description('Generate and apply idiomatic refactoring to the code')
  .action(fixCommand);

program.parse(process.argv);
