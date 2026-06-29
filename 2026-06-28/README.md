# todotrack

Scattered `TODO`, `FIXME`, and `HACK` comments pile up across a codebase and quietly become forgotten tech debt. **todotrack** walks a project, collects every annotation comment, and prints a clean report — as text, markdown, JSON, or CSV — with a `--fail-on` switch so CI can block merges that introduce, say, a new `FIXME`.

Inspiration: this is a recurring developer annoyance discussed in threads and tooling like the [r/learnprogramming TODO/FIXME management discussion](https://www.reddit.com/r/learnprogramming/) and ecosystem tools such as [ianlewis/todos](https://github.com/ianlewis/todos) and [todocheck](https://github.com/presmihaylov/todocheck). todotrack is a tiny, dependency-free take on the same idea.

## Requirements

Python 3.8+ — **standard library only, no third-party dependencies.**

## Install / run

It's a single file. Drop `todotrack.py` anywhere and run it:

```bash
python3 todotrack.py .
```

Optionally make it executable and put it on your PATH:

```bash
chmod +x todotrack.py
cp todotrack.py ~/.local/bin/todotrack
todotrack .
```

## Usage

```
todotrack [path] [options]

  path                 file or directory to scan (default: current dir)
  -t, --tags TAGS      comma-separated tags (default: FIXME,BUG,XXX,HACK,TODO,OPTIMIZE,NOTE)
  -f, --format FMT     text | markdown | json | csv   (default: text)
  -e, --exclude GLOB   skip files matching GLOB; repeatable (e.g. -e '*.min.js')
      --fail-on TAGS   exit 1 if any of these tags are found (for CI gates)
      --no-color       disable ANSI color in text output
      --follow-symlinks  follow symlinked directories
      --no-summary     hide the trailing summary line (text format)
  -o, --output FILE    write report to FILE instead of stdout
  -V, --version        show version
  -h, --help           show help
```

Common directories like `.git`, `node_modules`, `__pycache__`, `dist`, and `build` are skipped automatically, and binary files are ignored.

## Examples

```bash
# Plain report of the current project
python3 todotrack.py

# Markdown table for a code-review comment
python3 todotrack.py src/ --format markdown

# Only the urgent stuff, as JSON
python3 todotrack.py . --tags FIXME,BUG --format json

# Skip minified assets
python3 todotrack.py . -e '*.min.js' -e '*.bundle.js'

# CI gate: fail the build if a FIXME or BUG was left behind
python3 todotrack.py . --fail-on FIXME,BUG
```

### How matching works

A tag only counts when a comment leader (`#`, `//`, `/*`, `*`, `<!--`, `--`, `;`, `%`) appears just before it, so the word `TODO` inside a normal string or identifier (`todos = []`, `"TODO later"`) is **not** flagged. Tags are matched case-insensitively, and an optional `(author)` and `:` separator are parsed out:

```
# TODO(sayed): refactor   ->  tag=TODO  author=sayed  message=refactor
```

## Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | Ran successfully |
| 1 | A `--fail-on` tag was found |
| 2 | Usage error (bad path, no tags, write failure) |

## Tests

```bash
python3 test_todotrack.py
```

15 unit tests cover pattern matching, directory walking/skip rules, output, and exit codes. A `demo.sh` runs the tool against the bundled `sample_project/`.

## Source / motivation

Built as part of a daily "mini tool builder" exercise. The pain point — losing track of `TODO`/`FIXME` comments — is widely discussed; see for example the [r/learnprogramming](https://www.reddit.com/r/learnprogramming/) community and related tools linked above.
