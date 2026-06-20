# dupefind

Find duplicate files by **content** (not name), so you can reclaim disk space
and clean up messy backup/photo folders. A single, dependency-free Python
script.

## The problem

Duplicate files pile up everywhere — repeated downloads, copy-pasted backup
folders, the same photo saved three times. Filename-based tools miss copies
that were renamed, and "just hash everything" scripts are slow on large trees.
Finding true byte-for-byte duplicates from the terminal is a perennial request
in communities like r/commandline and r/datahoarder.

Source / inspiration (recurring "find duplicate files by content hash" requests
and the many one-off scripts that result):
https://www.reddit.com/r/commandline/search/?q=find%20duplicate%20files

## Why it's fast

`dupefind` does as little I/O as possible, in three passes:

1. **Group by size** — pure `stat`, no file reads. Unique sizes can't be dupes.
2. **Partial hash** — hash only the first 64 KB of same-size files.
3. **Full hash** — only same-partial-hash files are read in full to confirm.

Large unique files are never read end-to-end.

## Requirements

Python 3.7+ (standard library only — no `pip install` needed).

## Install / run

```sh
python3 dupefind.py [PATHS...]      # or: chmod +x dupefind.py && ./dupefind.py
```

## Usage

```
dupefind [-h] [-m BYTES] [-H] [-L] [--json] [-q] [--version] [paths ...]
```

| Option | Description |
| --- | --- |
| `paths` | Directories or files to scan (default: current directory). |
| `-m`, `--min-size BYTES` | Ignore files smaller than BYTES (default: 1). |
| `-H`, `--hidden` | Include hidden files and directories. |
| `-L`, `--follow-symlinks` | Follow symlinks (off by default). |
| `--json` | Emit results as JSON. |
| `-q`, `--quiet` | Print only the summary line. |
| `--version` | Print version. |

**Exit codes:** `0` no duplicates, `1` duplicates found, `2` usage error.
(The non-zero exit on "found" makes it easy to use in scripts/CI.)

## Examples

```sh
# Scan a folder
python3 dupefind.py ~/Downloads

# Ignore tiny files, machine-readable output
python3 dupefind.py -m 1024 --json ~/Pictures

# Quick try on the bundled fixtures
sh examples/demo.sh
```

Example output:

```
# 2 files, 195.3 KB each (195.3 KB reclaimable)
  /data/backup/big_a_dup.bin
  /data/photos/big_a.bin

Found 1 duplicate group(s); 195.3 KB reclaimable.
```

## Notes

- Read-only: `dupefind` never deletes or modifies anything. It reports groups;
  you decide what to remove.
- Tested: run `python3 test_dupefind.py` (9 unit tests, standard library
  `unittest`).
