#!/usr/bin/env node
import { Command } from 'commander';
import { runVibeCheck } from './review/analyze.js';
const program = new Command();
program
    .name('mergeguard')
    .description('AI-powered semantic gatekeeper for your codebase')
    .version('1.0.0');
program
    .command('check')
    .description('Analyze staged git changes against project vibes')
    .action(async () => {
    await runVibeCheck();
});
program.parse(process.argv);
