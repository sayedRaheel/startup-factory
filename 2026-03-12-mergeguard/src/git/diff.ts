import simpleGit, { SimpleGit } from 'simple-git';

const git: SimpleGit = simpleGit();

export async function getStagedDiff(): Promise<string> {
    try {
        // Get diff of staged files
        const diff = await git.diff(['--staged']);
        if (!diff) {
            throw new Error("No staged changes found to analyze.");
        }
        return diff;
    } catch (error: any) {
        throw new Error(`Git Diff Error: ${error.message}`);
    }
}
