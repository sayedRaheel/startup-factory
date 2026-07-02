#!/usr/bin/env bash
# End-to-end test for branchsweep. Creates a throwaway repo with:
#   * a branch merged into main            -> should be swept
#   * an unmerged WIP branch               -> should be kept
#   * a branch whose upstream is gone      -> should be swept
# Then runs dry-run, JSON, and --delete modes and asserts the results.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TOOL="$HERE/branchsweep.py"
REPO="$(mktemp -d)"
trap 'rm -rf "$REPO"' EXIT

cd "$REPO"
git init -q -b main
git config user.email test@example.com
git config user.name "branchsweep test"

echo a > f && git add f && git commit -qm "init"

# merged branch
git checkout -qb feature/merged
echo b >> f && git commit -qam "feat"
git checkout -q main && git merge -q --no-edit feature/merged

# unmerged WIP branch
git checkout -qb feature/wip
echo c > g && git add g && git commit -qm "wip"
git checkout -q main

# gone-upstream branch (upstream points at a remote ref that doesn't exist)
git checkout -qb feature/gone && git checkout -q main
git config branch.feature/gone.remote origin
git config branch.feature/gone.merge refs/heads/feature/gone
git remote add origin "$REPO/nonexistent-remote.git"

fail() { echo "FAIL: $1" >&2; exit 1; }

# 1. dry-run flags the right branches and deletes nothing
out="$(python3 "$TOOL" -C "$REPO")"
grep -q "feature/merged" <<<"$out" || fail "dry-run should list feature/merged"
grep -q "feature/gone"   <<<"$out" || fail "dry-run should list feature/gone"
grep -q "feature/wip" <<<"$out" && fail "dry-run must not list unmerged feature/wip"
git show-ref --verify -q refs/heads/feature/merged || fail "dry-run must not delete"

# 2. JSON mode is valid JSON with 2 candidates
python3 - "$TOOL" "$REPO" <<'PY'
import json, subprocess, sys
out = subprocess.check_output(["python3", sys.argv[1], "-C", sys.argv[2], "--json"], text=True)
data = json.loads(out)
assert data["dry_run"] is True
names = {c["name"] for c in data["candidates"]}
assert names == {"feature/merged", "feature/gone"}, names
PY

# 3. --delete removes swept branches, keeps WIP
python3 "$TOOL" -C "$REPO" --delete >/dev/null
git show-ref --verify -q refs/heads/feature/merged && fail "feature/merged should be deleted"
git show-ref --verify -q refs/heads/feature/gone && fail "feature/gone should be deleted"
git show-ref --verify -q refs/heads/feature/wip || fail "feature/wip must survive"

# 4. exit code 2 outside a repo
set +e
python3 "$TOOL" -C "$(mktemp -d)" >/dev/null 2>&1
[ $? -eq 2 ] || fail "expected exit code 2 outside a repo"
set -e

echo "all tests passed"
