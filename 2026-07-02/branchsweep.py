#!/usr/bin/env python3
"""branchsweep — find and clean up stale local git branches.

Lists (and optionally deletes) local branches that are:
  * merged into the base branch, and/or
  * tracking a remote branch that no longer exists ("[gone]"), and/or
  * untouched for more than N days (--stale-days)

Dry-run by default. Nothing is deleted unless you pass --delete.

Standard library only. Requires git on PATH.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

DEFAULT_PROTECTED = {"main", "master", "develop", "trunk"}

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NOT_A_REPO = 2


def run_git(args, cwd=None):
    """Run a git command, return (exit_code, stdout)."""
    try:
        proc = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
    except FileNotFoundError:
        print("error: git not found on PATH", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def ensure_repo(cwd):
    code, out, _ = run_git(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
    if code != 0 or out != "true":
        print("error: not inside a git repository", file=sys.stderr)
        sys.exit(EXIT_NOT_A_REPO)


def current_branch(cwd):
    _, out, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return out


def detect_base_branch(cwd):
    """Prefer main, then master, then the current branch."""
    for candidate in ("main", "master"):
        code, _, _ = run_git(
            ["show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"],
            cwd=cwd,
        )
        if code == 0:
            return candidate
    return current_branch(cwd)


def list_branches(cwd):
    """Return list of dicts with name, upstream_gone, last_commit_ts, subject."""
    fmt = "%(refname:short)\t%(upstream:track)\t%(committerdate:unix)\t%(subject)"
    code, out, err = run_git(
        ["for-each-ref", "refs/heads/", f"--format={fmt}"], cwd=cwd
    )
    if code != 0:
        print(f"error: git for-each-ref failed: {err}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    branches = []
    for line in out.splitlines():
        parts = line.split("\t", 3)
        if len(parts) < 4:
            continue
        name, track, ts, subject = parts
        branches.append(
            {
                "name": name,
                "upstream_gone": track == "[gone]",
                "last_commit_ts": int(ts) if ts.isdigit() else 0,
                "subject": subject,
            }
        )
    return branches


def merged_branches(cwd, base):
    code, out, err = run_git(["branch", "--merged", base, "--format=%(refname:short)"], cwd=cwd)
    if code != 0:
        print(f"error: git branch --merged failed: {err}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    return {b.strip() for b in out.splitlines() if b.strip()}


def age_days(unix_ts):
    if not unix_ts:
        return None
    delta = datetime.now(timezone.utc) - datetime.fromtimestamp(unix_ts, timezone.utc)
    return delta.days


def collect_candidates(cwd, base, protected, stale_days):
    """Return branch dicts annotated with the reasons they are sweepable."""
    cur = current_branch(cwd)
    merged = merged_branches(cwd, base)
    candidates = []
    for br in list_branches(cwd):
        name = br["name"]
        if name == base or name == cur or name in protected:
            continue
        reasons = []
        if name in merged:
            reasons.append("merged")
        if br["upstream_gone"]:
            reasons.append("gone-upstream")
        days = age_days(br["last_commit_ts"])
        if stale_days is not None and days is not None and days >= stale_days:
            reasons.append(f"stale({days}d)")
        if reasons:
            br["reasons"] = reasons
            br["age_days"] = days
            candidates.append(br)
    return candidates


def delete_branches(cwd, candidates, force):
    """Delete candidate branches. Returns (deleted, failed) name lists."""
    deleted, failed = [], []
    for br in candidates:
        # Only force-delete when the user explicitly asked for it or the
        # branch is provably merged; -d refuses unmerged work by design.
        flag = "-D" if (force or "merged" in br["reasons"]) else "-d"
        code, _, err = run_git(["branch", flag, br["name"]], cwd=cwd)
        if code == 0:
            deleted.append(br["name"])
        else:
            failed.append(br["name"])
            print(f"  ! could not delete {br['name']}: {err.splitlines()[-1] if err else 'unknown error'}", file=sys.stderr)
    return deleted, failed


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="branchsweep",
        description="Find (and optionally delete) stale local git branches: "
        "merged into base, tracking a deleted remote, or older than N days.",
        epilog="Dry-run by default; pass --delete to actually remove branches.",
    )
    parser.add_argument("-C", "--repo", default=".", metavar="PATH",
                        help="path to the git repository (default: current directory)")
    parser.add_argument("-b", "--base", default=None, metavar="BRANCH",
                        help="base branch to check merges against (default: auto-detect main/master)")
    parser.add_argument("--stale-days", type=int, default=None, metavar="N",
                        help="also flag branches with no commits in the last N days")
    parser.add_argument("--protect", action="append", default=[], metavar="BRANCH",
                        help="extra branch name to never touch (repeatable)")
    parser.add_argument("--delete", action="store_true",
                        help="actually delete the listed branches (default is dry-run)")
    parser.add_argument("--force", action="store_true",
                        help="use git branch -D for unmerged gone/stale branches")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    ensure_repo(args.repo)
    base = args.base or detect_base_branch(args.repo)
    protected = DEFAULT_PROTECTED | set(args.protect)

    candidates = collect_candidates(args.repo, base, protected, args.stale_days)

    if args.as_json:
        payload = {
            "base": base,
            "dry_run": not args.delete,
            "candidates": [
                {
                    "name": c["name"],
                    "reasons": c["reasons"],
                    "age_days": c["age_days"],
                    "subject": c["subject"],
                }
                for c in candidates
            ],
        }
    else:
        if not candidates:
            print(f"branchsweep: nothing to sweep (base: {base})")
            return EXIT_OK
        mode = "would delete" if not args.delete else "deleting"
        print(f"branchsweep: base={base}  {mode} {len(candidates)} branch(es):\n")
        for c in candidates:
            age = f"{c['age_days']}d" if c["age_days"] is not None else "?"
            print(f"  {c['name']:<32} {', '.join(c['reasons']):<28} last commit {age} ago")
        print()

    if args.delete and candidates:
        deleted, failed = delete_branches(args.repo, candidates, args.force)
        if args.as_json:
            payload["deleted"] = deleted
            payload["failed"] = failed
            print(json.dumps(payload, indent=2))
        else:
            suffix = f", {len(failed)} failed" if failed else ""
            print(f"deleted {len(deleted)} branch(es){suffix}")
        return EXIT_OK if not failed else EXIT_ERROR

    if args.as_json:
        print(json.dumps(payload, indent=2))
    elif candidates:
        print("dry-run: pass --delete to remove these branches")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
