# diskhog

A tiny, zero-dependency CLI that tells you **what is eating your disk space** —
and, with `--reclaim`, totals up the regenerable build/cache directories
(`node_modules`, `.venv`, `target`, `__pycache__`, `dist`, `.next`, …) you can
safely delete to get it back.

## The problem

Developers accumulate gigabytes of regenerable junk without noticing — the
classic case is `node_modules`, which can hold hundreds of thousands of files
and quietly eat ~10 GB across a handful of projects. Cleaning it up means
remembering an OS-specific `du | sort` incantation, or installing a separate
disk-usage app, just to answer "what's big and what's safe to nuke?" `diskhog`
does both in one command, offline, with only the Python standard library.

## Source / inspiration

This addresses the recurring "regenerable folders are eating my disk" pain,
most concretely the widely-shared write-up
[*I reclaimed 10GB of disk space from node_modules* by Mike Bifulco](https://mikebifulco.com/posts/reclaimed-10gb-of-disk-space-from-node-modules),
which surfaces from r/webdev / r/learnprogramming disk-cleanup threads. (Reddit
itself is not reachable from the build sandbox, so the cited link is the
community write-up the discussion centers on.)

## Install / run

No installation and no dependencies — just Python 3.8+ (standard library only).

```bash
python3 diskhog.py ~/projects
# or put it on your PATH:
chmod +x diskhog.py && mv diskhog.py ~/.local/bin/diskhog
```

## Usage

```
diskhog [PATH] [-n N] [--files-only | --dirs-only] [--reclaim]
        [--min SIZE] [-L] [--json]
```

| Flag | Meaning |
| --- | --- |
| `PATH` | directory to scan (default: `.`) |
| `-n, --top N` | show the N largest entries (default 20) |
| `--files-only` | rank individual files only |
| `--dirs-only` | rank directories only |
| `--reclaim` | list regenerable build/cache dirs and total reclaimable space |
| `--min SIZE` | ignore entries smaller than SIZE (e.g. `100M`, `1.5G`) |
| `-L, --follow-symlinks` | follow symlinked directories (off by default) |
| `--json` | machine-readable JSON output |
| `--version` | print version |

### Examples

Find the 15 biggest things in your projects folder:

```bash
diskhog ~/projects -n 15
```
```
Total under '~/projects': 12.4 GB
Top 15 entries:
       4.1 GB  [d] ~/projects/web/node_modules/
       3.2 GB  [d] ~/projects/ml/.venv/
       900.0 MB  [f] ~/projects/data/dump.sql
       ...
```

See how much you could reclaim, safely:

```bash
diskhog ~/projects --reclaim
```
```
Reclaimable build/cache directories under '~/projects':
       4.1 GB   ~/projects/web/node_modules/
       3.2 GB   ~/projects/ml/.venv/
       210.0 MB  ~/projects/api/__pycache__/

Total reclaimable: 7.5 GB
```

Pipe the JSON into your own cleanup (review first!):

```bash
diskhog ~/projects --reclaim --json \
  | python3 -c "import sys,json;[print(i['path']) for i in json.load(sys.stdin)['items']]" \
  | xargs rm -rf
```

## Notes

- Directory sizes are **recursive totals** (everything underneath), computed in
  a single bottom-up walk.
- `--reclaim` reports only the **outermost** match on each path, so a
  `node_modules` nested inside another `node_modules` isn't double-counted.
- Symlinks are not followed by default and file sizes use `lstat`, so symlinked
  trees aren't counted twice. Unreadable entries are skipped with a warning.
- Exit codes: `0` success, `1` bad/missing path, `2` bad argument value.

## Testing

```bash
python3 -m unittest test_diskhog.py
```

Tested clean: 8/8 unit tests pass (size formatting/parsing, recursive directory
sizing, reclaimable detection, and CLI exit codes), plus manual end-to-end runs
of the ranking, `--reclaim`, and `--json` modes.
