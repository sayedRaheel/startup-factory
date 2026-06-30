# jsondiff

Compare two JSON files by **meaning, not text**. A plain `diff` / `git diff`
treats JSON as lines, so it screams about changes when keys are merely reordered
or one side is minified while the other is pretty-printed. `jsondiff` parses both
sides first and reports only the real differences — added keys, removed keys, and
changed values — each with a JSON path so you can jump straight to it.

Single file, **zero third-party dependencies** (Python standard library only).

## The problem

Diffing JSON with a line-based tool is famously noisy: reorder the keys or change
the indentation and the whole file lights up even though the data is identical.
This is a recurring complaint among developers, which is why so many online
"semantic JSON diff" tools exist — but those need a browser and often want you to
paste potentially sensitive data into a website. `jsondiff` does the same job
offline, in your terminal.

Source / inspiration: the well-documented "text diff makes JSON comparison
painful" annoyance, e.g. the [JSON diff tutorial on Jsonic](https://jsonic.io/guides/json-diff-tutorial)
and the [comparative review of JSON diff tools (Offline Tools)](https://offlinetools.org/a/json-formatter/diff-tools-in-json-formatters-comparative-review),
both of which describe how key reordering and formatting create meaningless diff
noise that semantic comparison removes.

## Install / run

No install needed — it's one file and uses only the standard library
(Python 3.7+):

```bash
python3 jsondiff.py before.json after.json
```

Optionally drop it on your PATH:

```bash
chmod +x jsondiff.py
mv jsondiff.py ~/.local/bin/jsondiff
jsondiff before.json after.json
```

## Usage

```
jsondiff LEFT RIGHT [options]

  LEFT, RIGHT            JSON files to compare (use '-' for one of them to read stdin)
  --ignore-array-order   treat arrays as unordered (compare membership, not position)
  -f, --format {text,json}   output format (default: text)
  --no-color             disable ANSI colors in text output
  -q, --quiet            print nothing; communicate via exit code only
  -V, --version          show version
  -h, --help             show help
```

### Exit codes

| Code | Meaning                |
|------|------------------------|
| 0    | inputs are identical   |
| 1    | inputs differ          |
| 2    | error (bad args / unreadable / invalid JSON) |

This mirrors `diff`, so you can gate CI on it:

```bash
jsondiff expected.json actual.json --quiet || echo "config drift detected"
```

## Examples

Even though `after.json` below is minified and has its keys in a different order,
jsondiff only reports what actually changed:

```
$ jsondiff before.json after.json
- root.debug = true
~ root.limits.memory: "256Mi" -> "512Mi"
+ root.region = "us-east-1"
~ root.replicas: 2 -> 4
~ root.version: "1.4.0" -> "1.5.0"

5 difference(s): 1 added, 1 removed, 3 changed
```

Legend: `+` added, `-` removed, `~` changed (colorized when writing to a TTY).

Compare an API response against a saved fixture, ignoring array order:

```bash
curl -s https://api.example.com/config | jsondiff - expected.json --ignore-array-order
```

Machine-readable output for scripts:

```bash
jsondiff a.json b.json --format json
```

```json
[
  { "op": "changed", "path": "root.replicas", "old": 2, "new": 4 },
  { "op": "added",   "path": "root.region",   "new": "us-east-1" }
]
```

## Behavior notes

- **Key order and whitespace are ignored** — that's the whole point.
- **Numbers**: `1` and `1.0` are treated as equal; `true` is *not* equal to `1`.
- **Arrays** are compared by position by default. Use `--ignore-array-order` to
  compare them as multisets (membership only); reordered elements then vanish and
  you only see genuinely added/removed items (reported at path `…[*]`).
- **Paths** use `root.a.b[0]` notation; non-identifier keys are quoted, e.g.
  `root["content-type"]`.

## Tests

```bash
python3 -m unittest test_jsondiff -v   # 22 tests, standard library only
```

## Files

- `jsondiff.py` — the tool
- `test_jsondiff.py` — unit tests
- `before.json`, `after.json` — sample inputs
- `demo.sh` — runnable walkthrough
- `CHANGELOG.md`
