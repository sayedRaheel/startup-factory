# jsonshape

**The problem:** You get a giant, unfamiliar JSON blob from an API and just want
to know its *shape* — which keys exist, what types they are, how deep it nests,
how long the arrays are — without dumping the whole thing or hand-writing a `jq`
expression. People routinely resort to custom `jq` schema-profiling snippets for
exactly this ([example](https://gist.github.com/mikehwang/6ed95480579ac0b9fd72bff340d99a18)).

`jsonshape` prints a compact schema skeleton of any JSON document.

Idea sourced from recurring discussion about understanding the structure of
arbitrary/unfamiliar JSON, e.g. <https://blog.oddbit.com/post/2023-07-27-jq-streams/>
and the jq schema-profiling gist linked above.

## Install / run

Pure Python 3.7+ standard library — no dependencies, nothing to install.

```bash
python3 jsonshape.py data.json
# or make it executable and drop it on your PATH
chmod +x jsonshape.py && mv jsonshape.py ~/.local/bin/jsonshape
```

## Usage

```
jsonshape [file] [--ndjson] [--depth N] [--samples] [--json]
```

| Flag         | What it does                                              |
|--------------|----------------------------------------------------------|
| `file`       | JSON file to inspect (default: stdin, or `-`)            |
| `--ndjson`   | Treat input as newline-delimited JSON and merge records  |
| `--depth N`  | Limit output to N levels of nesting                      |
| `--samples`  | Show an example value beside each scalar leaf            |
| `--json`     | Emit the inferred schema as JSON instead of a tree       |
| `--version`  | Print version                                            |

Keys present in only *some* records of an array/NDJSON stream are marked with `?`
and an `(present/total)` count, so you can instantly spot optional fields.

## Examples

Inspect a file:

```
$ jsonshape sample.json
object{8}
├─ id: int
├─ name: str
├─ active: bool
├─ score: float
├─ meta: null
├─ tags: array[3] of str
├─ address: object{2}
│  ├─ city: str
│  └─ zip: str
└─ users: array[3] of object{3}
   ├─ sku: str
   ├─ price: float
   └─ note?: str  (2/3)
```

Pipe a live API response:

```
curl -s https://api.example.com/users | jsonshape -
```

Profile a log of newline-delimited JSON events (great for finding optional fields):

```
$ jsonshape --ndjson events.ndjson
# merged 3 NDJSON record(s)
object{4}
├─ event: str
├─ ts: int
├─ user?: str  (2/3)
└─ extra?: bool  (1/3)
```

Show sample values, capped at 2 levels deep:

```
jsonshape --samples --depth 2 big.json
```

## Exit codes

| Code | Meaning                              |
|------|--------------------------------------|
| 0    | Success                              |
| 1    | Runtime error (bad JSON, missing/empty file) |
| 2    | Usage error (bad arguments)          |

## Tests

```bash
python3 -m unittest -v test_jsonshape
```

16 unit tests cover inference, rendering, optional-key detection, NDJSON merging,
and CLI exit codes.
