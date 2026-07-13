# mdlinks

**The problem:** You reorganize a docs folder or rename a file, and half the
relative links in your Markdown quietly break. Nobody notices until a reader
hits a dead `guide.md` link or a `#heading` anchor that no longer exists.
Existing answers are heavyweight (link-checker services, npm packages, static
site builds) for what should be a 5-second local check.

**Source:** This recurring pain point shows up across developer forums —
e.g. this Obsidian forum thread on links breaking when files move
(<https://forum.obsidian.md/t/broken-links-in-relative-path-mode-on-move-rename/4386>)
and github/markup issue #926 on relative links breaking
(<https://github.com/github/markup/issues/926>).
*Note: this run could not fetch Reddit directly from the sandbox (crawler
blocked), so the cited sources are equivalent forum/issue threads rather than
a specific Reddit post.*

**mdlinks** is a single-file, stdlib-only Python CLI that scans Markdown files
**offline** and reports:

- relative file links whose target doesn't exist (`[x](missing.md)`, images too)
- broken heading anchors, same-file (`#gone`) or cross-file (`guide.md#nope`),
  using GitHub's slug rules (duplicate headings become `-1`, `-2`, …; setext
  headings and `<a name=…>` HTML anchors are recognized)

External `http(s)://` links are skipped — no network, no flakiness. Links inside
fenced code blocks and inline code spans are ignored. `%20`-encoded paths and
`<angle bracket>` targets work. Absolute links (`/docs/x.md`) resolve against
`--root`.

## Install / Run

No dependencies. Python 3.8+.

```sh
python3 mdlinks.py [paths ...] [options]
# or
chmod +x mdlinks.py && ./mdlinks.py docs/
```

## Usage

```sh
mdlinks.py                      # check all .md under the current directory
mdlinks.py docs/ README.md      # mix of dirs and files
mdlinks.py --format json docs/  # machine-readable output
mdlinks.py -q docs/             # quiet on success — ideal for CI / pre-commit
mdlinks.py --exclude drafts docs/
```

Exit codes: `0` all links OK · `1` broken links found · `2` usage error.

### Example

```text
$ python3 mdlinks.py examples/docs
examples/docs/index.md:5: BROKEN missing.md (target does not exist)
examples/docs/index.md:6: BROKEN guide.md#nope (anchor '#nope' not found in target)
mdlinks: 2 file(s), 7 link(s) checked, 1 external skipped, 2 broken
```

The `examples/docs/` folder in this directory contains those two intentional
breaks so you can try the tool immediately.

### CI usage

```yaml
- run: python3 mdlinks.py -q docs/ README.md
```

## Tests

```sh
python3 test_mdlinks.py   # 15 unit tests, stdlib unittest
```

## Limitations

- Slugging approximates GitHub's algorithm; exotic Unicode headings may differ.
- Reference-style link *usages* aren't matched to definitions (the definition
  targets themselves are checked).
- HTML `<a href>` links inside Markdown are not scanned.
