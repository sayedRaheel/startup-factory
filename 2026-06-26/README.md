# mdtable

Align GitHub-Flavored Markdown tables from the command line, so the pipes line
up without you re-padding every cell by hand every time you add a row.

## The problem

Hand-aligning Markdown tables is tedious and easy to get wrong: add one row or
widen one cell and you have to re-space every `|` in the block to keep it
readable in source. The table still *renders* fine when it's ragged, but ragged
source is annoying to diff and edit. This is a commonly griped-about chore — see
e.g. ["aligning Markdown tables in Helix"](https://bytes.zone/posts/aligning-markdown-tables-in-helix/),
which opens by calling hand-alignment "tedious and annoying to work with."

(The build sandbox cannot reach reddit.com directly, so the cited write-up is a
developer-community post describing the exact same annoyance.)

## What it does

`mdtable` scans a Markdown document, finds every GFM table (a header line with
`|`, followed by a `---` delimiter row), and re-pads the columns so they align.
It honors per-column alignment markers — `:---` (left), `:---:` (center),
`---:` (right) — and leaves all non-table text exactly as it was.

- Pure Python 3, **standard library only** — no `pip install`.
- Reads stdin or files; prints to stdout, or rewrites files with `-i`.
- `--check` mode for CI / pre-commit: exits non-zero if anything isn't aligned.
- Handles ragged rows (pads short rows), escaped pipes (`\|`), and wide
  CJK characters (counted as 2 columns so East-Asian tables still line up).

## Requirements

Python 3.6+ (standard library only).

## Install / run

It's a single file. Drop it on your `PATH` (or run with `python3`):

```sh
chmod +x mdtable.py
./mdtable.py --help
```

## Usage

```sh
mdtable README.md                 # print the aligned version to stdout
mdtable -i README.md docs/*.md    # rewrite files in place
cat notes.md | mdtable            # use it as a pipe filter
mdtable --check README.md         # exit 2 if not already aligned (CI)
```

### Example

Input:

```text
| Name | Role | Score |
|:-|:-:|-:|
| Alice | admin | 100 |
| Bob | user | 7 |
```

Output:

```text
| Name  |  Role |   Score |
| :---- | :---: | ------: |
| Alice | admin |     100 |
| Bob   |  user |       7 |
```

## Exit codes

| Code | Meaning                                            |
| ---- | -------------------------------------------------- |
| 0    | Success (or, in `--check`, everything was aligned) |
| 1    | An error (missing file, unreadable, bad UTF-8)     |
| 2    | `--check` only: at least one input needs aligning  |

## Tests

```sh
python3 test_mdtable.py
```

16 unit tests cover row splitting, delimiter detection, alignment parsing,
ragged rows, escaped pipes, idempotency, and CJK width. Tested clean in the
build sandbox.

## Notes / limitations

- Operates on GFM pipe tables only. Indented code blocks and fenced code blocks
  that happen to contain `|` are not specially excluded, so don't run it over a
  file whose code samples contain pipe-table-shaped lines without checking the
  diff. (A practical workflow: review with `mdtable file.md | diff file.md -`
  before using `-i`.)
- Column width uses monospace display width; proportional-font editors may still
  look slightly off, but the rendered HTML is identical regardless.
