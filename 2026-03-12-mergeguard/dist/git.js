import { simpleGit } from 'simple-git';
const git = simpleGit();
export async function getRecentCommitMessages(count = 50) {
    const log = await git.log({ maxCount: count });
    return log.all.map(commit => commit.message);
}
export async function getTrackedFiles() {
    const result = await git.raw(['ls-tree', '-r', 'HEAD', '--name-only']);
    return result.split('\n').filter(Boolean);
}
