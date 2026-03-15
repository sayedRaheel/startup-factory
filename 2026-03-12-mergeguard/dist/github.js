import { Octokit } from '@octokit/rest';
import { env } from './config.js';
const octokit = new Octokit({ auth: env.GITHUB_TOKEN });
export async function getPRDiff(owner, repo, pullNumber) {
    const { data } = await octokit.pulls.get({
        owner,
        repo,
        pull_number: pullNumber,
        mediaType: { format: 'diff' }
    });
    return data;
}
export async function postReviewComment(owner, repo, pullNumber, body) {
    await octokit.issues.createComment({
        owner,
        repo,
        issue_number: pullNumber,
        body
    });
}
