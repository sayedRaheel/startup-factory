import { simpleGit } from 'simple-git';
const git = simpleGit();
export async function getStagedDiff() {
    try {
        // Get diff of staged files
        const diff = await git.diff(['--staged']);
        if (!diff) {
            throw new Error("No staged changes found to analyze.");
        }
        return diff;
    }
    catch (error) {
        throw new Error(`Git Diff Error: ${error.message}`);
    }
}
