import { Octokit } from '@octokit/rest';
import { env } from './config.js';

const octokit = new Octokit({ auth: env.GITHUB_TOKEN });

export async function getPRDiff(owner: string, repo: string, pullNumber: number): Promise<string> {
  const { data } = await octokit.pulls.get({
    owner,
    repo,
    pull_number: pullNumber,
    mediaType: { format: 'diff' }
  });
  return data as unknown as string;
}

export async function postReviewComment(owner: string, repo: string, pullNumber: number, body: string) {
  await octokit.issues.createComment({
    owner,
    repo,
    issue_number: pullNumber,
    body
  });
}
