# branchsweep

Find — and optionally delete — stale local git branches, in one command instead of the usual `git branch --merged | grep -v ... | xargs git branch -d` pipeline plus a separate `[gone]`-upstream dance.

## The problem

Local branches pile up after every merged PR. Cleaning them means chaining several commands (`git branch --merged`, `git fetch --prune`, parsing `git branch -vv` for `[gone]`), and one wrong `xargs git branch -D` can nuke unmerged work. It's a perennial developer annoyance; see write-ups of the same multi-step ritual like [Pull Panda's branch clean-up strategies](https://pullpanda.io/blog/deleting-feature-branches-cleanup-strategies) and [Nicky Meuleman's "Clean up old git branches"](https://nickymeuleman.netlify.app/blog/delete-git-branches/) — a recurring topic on r/git and r/webdev. (Note: sourced from these articles surfaced while scanning recent dev discussions; no single canonical Reddit thread was cited.)

`branchsweep` folds the whole ritual into a single, safe, dependency-free script.

## What it flags

- **merged** — branches already merged into the base branch (auto-detects `main`/`master`)
- **gone-upstream** — branches whose tracked remote branch was deleted (`[gone]`)
- **stale(Nd)** — optionally, branches with no commits in the last N days (`--stale-days N`)

The current branch, the base branch, and `main`/`master`/`develop`/`trunk` (plus anything passed via `--protect`) are never touched. Dry-run is the default.

## Install / run

Python 3.8+, standard library only. Requires `git` on PATH.

```sh
python3 branchsweep.py              # dry-run in the current repo
python3 branchsweep.py --delete     # actually delete
```

Or make it a command: `chmod +x branchsweep.py && mv branchsweep.py ~/bin/branchsweep`

## Usage

```
branchsweep [-C PATH] [-b BRANCH] [--stale-days N] [--protect BRANCH]
            [--delete] [--force] [--json]
```

Examples:

```sh
branchsweep                          # list sweepable branches (dry-run)
branchsweep --delete                 # delete merged + gone-upstream branches
branchsweep --stale-days 90          # also flag branches idle for 90+ days
branchsweep --stale-days 90 --delete --force   # -D unmerged stale ones too
branchsweep -b develop --protect release       # custom base + protected branch
branchsweep --json                   # machine-readable output
```

Safety model: merged branches are deleted with `-d`; unmerged (gone/stale-only) branches are only force-deleted if you pass `--force`, otherwise git refuses and branchsweep reports it and exits 1.

Exit codes: `0` success, `1` some deletions failed / error, `2` not a git repository.

## Tests

```sh
bash test_branchsweep.sh   # builds a throwaway repo and asserts all modes
```

Tested clean on Linux with git 2.x and Python 3.10.
