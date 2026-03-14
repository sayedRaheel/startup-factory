import { simpleGit, SimpleGit } from 'simple-git';

const git: SimpleGit = simpleGit();

export async function getRecentCommitMessages(count: number = 50): Promise<string[]> {
  const log = await git.log({ maxCount: count });
  return log.all.map(commit => commit.message);
}

export async function getTrackedFiles(): Promise<string[]> {
  const result = await git.raw(['ls-tree', '-r', 'HEAD', '--name-only']);
  return result.split('\n').filter(Boolean);
}
