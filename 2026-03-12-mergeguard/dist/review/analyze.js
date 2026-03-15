import { getStagedDiff } from '../git/diff.js';
import { buildVibeCheckPrompt } from '../llm/prompt.js';
import { analyzeWithLLM } from '../llm/client.js';
import ora from 'ora';
import chalk from 'chalk';
export async function runVibeCheck() {
    const spinner = ora('Extracting git diff...').start();
    try {
        const diff = await getStagedDiff();
        // MVP: Empty context. V2 will populate this via src/git/context.ts
        const context = "Assume standard modern conventions.";
        spinner.text = 'Running Semantic Vibe Check via LLM...';
        const prompt = buildVibeCheckPrompt(diff, context);
        const result = await analyzeWithLLM(prompt);
        spinner.stop();
        if (result.status === 'APPROVED') {
            console.log(chalk.green.bold('✅ Semantic Pass: APPROVED'));
            console.log(chalk.gray(result.reason));
            process.exit(0);
        }
        else {
            console.log(chalk.red.bold('❌ Vibe Check Failed: REJECTED'));
            console.log(chalk.yellow(`Reason: ${result.reason}\n`));
            console.log(chalk.white.bold('Agent Refactoring Instructions:'));
            result.actionable_feedback.forEach((feedback, index) => {
                console.log(chalk.white(`  ${index + 1}. ${feedback}`));
            });
            process.exit(1);
        }
    }
    catch (error) {
        spinner.fail('Error during MergeGuard execution');
        console.error(chalk.red(error.message));
        process.exit(1);
    }
}
