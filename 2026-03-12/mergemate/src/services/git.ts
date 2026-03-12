import simpleGit from 'simple-git';

const git = simpleGit();

export async function getDiff(): Promise<string> {
  // Gets unstaged and staged diffs
  return await git.diff(); 
}

export async function applyPatch(patch: string): Promise<void> {
  // MVP: Instruct user or use fs to overwrite files based on LLM output.
  // For production, parse the patch or write the LLM's full file output to disk.
}
