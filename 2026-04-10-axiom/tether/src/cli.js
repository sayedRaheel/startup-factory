#!/usr/bin/env node
import { program } from 'commander';
import fs from 'fs';
import { spawn } from 'child_process';
import { compileContext } from './compiler.js';
import { startProxy } from './harness/proxy.js';
import { loadConfig } from './config.js';

program
  .name('tether')
  .description('Zero-trust sandbox for AI coding agents')
  .version('1.0.0');

program.command('init')
  .description('Initialize a .tether context rule file in the current directory')
  .action(() => {
      fs.writeFileSync('.tetherrules', 'strict_mode = true\n');
      console.log('Tether initialized. Context compiler rules generated.');
  });

program.command('run')
  .description('Run an AI agent within the Tether sandbox')
  .argument('<agent_command>', 'The command to start the agent')
  .argument('[args...]', 'Arguments to pass to the agent')
  .action(async (agentCommand, args) => {
      console.log("Loading config...");
      const config = loadConfig();
      
      console.log("Compiling strict context...");
      const compiledContext = compileContext();
      const proxyPort = 8765;

      const state = {
          isProven: false,
          compiledContext,
          realApiBase: process.env.OPENAI_BASE_URL || 'https://api.openai.com'
      };

      startProxy(state, proxyPort);

      // Let proxy boot
      await new Promise(resolve => setTimeout(resolve, 500));

      console.log("Spawning agent inside Tether Sandbox...");

      const env = Object.assign({}, process.env, {
          OPENAI_BASE_URL: `http://127.0.0.1:${proxyPort}`
      });

      const child = spawn(agentCommand, args, { stdio: 'inherit', env, shell: true });

      child.on('close', (code) => {
          console.log(`Agent exited with status: ${code}`);
          process.exit(code || 0);
      });
      
      child.on('error', (err) => {
          console.error(`Failed to start agent process: ${err.message}`);
          process.exit(1);
      });
  });

program.parse(process.argv);
