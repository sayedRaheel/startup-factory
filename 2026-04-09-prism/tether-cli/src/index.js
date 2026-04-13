#!/usr/bin/env node
import { program } from 'commander';
import { initCommand } from './commands/init.js';
import { mapCommand } from './commands/map.js';

program
  .name('tether')
  .description('A lightning-fast CLI to scaffold context boundaries for local AI agents')
  .version('1.0.0');

program
  .command('init')
  .description('Scans the repository and generates standardized .agentrc and SKILLS.md')
  .action(() => {
    try {
      initCommand();
    } catch (e) {
      console.error(`Fatal error: ${e.message}`);
      process.exit(1);
    }
  });

program
  .command('map')
  .description('Generates a lightweight, token-optimized architecture graph (.agent-context.md)')
  .action(() => {
    try {
      mapCommand();
    } catch (e) {
      console.error(`Fatal error: ${e.message}`);
      process.exit(1);
    }
  });

program.parse();
