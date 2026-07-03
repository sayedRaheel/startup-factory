# renamr

Safe batch file renaming with regex — **dry-run by default**, collision
detection, and an optional undo script.

## The problem

Bulk-renaming files by pattern is a perennial command-line annoyance: `mv`
doesn't do patterns, the Perl `rename` isn't installed everywhere (and has
two incompatible variants), and one bad regex can clobber files with no way
back. Community write-ups on batch renaming consistently flag the same two
gotchas: always dry-run first, and watch for filename collisions where two
originals map to the same target.

**Source note:** this run could not link one specific Reddit thread (Reddit
search indexing was not returning thread URLs); the problem framing above is
based on these write-ups instead:
- https://linuxmind.dev/2025/09/02/batch-rename-files-with-rename/
- https://wafaicloud.com/blog/batch-renaming-files-in-linux-using-the-command-line/

`renamr` bakes both safety lessons in: nothing happens without `--apply`,
collisions abort the whole batch (exit code 2), and `--undo-script` writes a
shell script that reverses the batch.

## Install / run

Python 3.8+, standard library only.

```sh
python3 renamr.py --help
```

## Usage

```sh
# Preview (default — nothing is renamed)
python3 renamr.py 'IMG_(\d+)' 'photo_\1' *.jpg

# Actually rename
python3 renamr.py --apply 'IMG_(\d+)' 'photo_\1' *.jpg

# Spaces -> underscores, with an undo script
python3 renamr.py --apply --undo-script undo.sh ' ' '_' *.txt
sh undo.sh   # to reverse

# Lowercase filenames ('-' means "keep the matched name unchanged")
python3 renamr.py --apply --lower '.*' - *.TXT
```

## Safety behavior

- Dry-run by default; `--apply` required to touch anything.
- Refuses the entire batch if two files would map to the same target, or if
  a target already exists (exit code 2).
- Refuses replacements that introduce path separators (no directory escapes).
- Exit codes: `0` ok, `1` nothing matched, `2` collision, `3` error.

## Tests

```sh
python3 test_renamr.py   # 10 tests, stdlib unittest
```

Tested in a Linux sandbox on 2026-07-03: all tests pass.
