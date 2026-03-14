import { Command } from 'commander';
import { parseFormaFile } from './parser';
import { compileToPayload } from './compiler';
import { runTest } from './runner';
import { writeFileSync } from 'fs';

const program = new Command();

program
  .name('forma')
  .description('Forma CLI - Compile strongly typed LLM prompts')
  .version('1.0.0');

program
  .command('build')
  .description('Compile a .forma file into an API payload')
  .argument('<file>', 'Path to the .forma file')
  .action((file) => {
    try {
      console.log(`Analyzing ${file}...`);
      const ast = parseFormaFile(file);
      const payload = compileToPayload(ast);
      
      const outFile = file.replace('.forma', '.json');
      writeFileSync(outFile, JSON.stringify(payload, null, 2));
      
      console.log(`✅ Successfully compiled to ${outFile}`);
    } catch (error: any) {
      console.error(`❌ Build failed: ${error.message}`);
      process.exit(1);
    }
  });

program
  .command('test')
  .description('Execute a .forma file against an LLM and assert outputs')
  .argument('<file>', 'Path to the .forma file')
  .argument('<input>', 'Mock input string to feed to the LLM')
  .action(async (file, input) => {
    try {
      console.log(`Executing ${file} with input: "${input}"...`);
      const result = await runTest(file, input);
      console.log(`✅ Execution Success:\n${result}`);
    } catch (error: any) {
      console.error(`❌ Execution failed: ${error.message}`);
      process.exit(1);
    }
  });

program.parse();
