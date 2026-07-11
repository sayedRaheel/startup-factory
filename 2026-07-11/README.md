# csvpeek

**The problem:** Someone hands you a CSV that's too big for Excel (or Excel mangles it), and all you want to know is: what columns does it have, how many rows, and what does the data roughly look like? The usual answers are "install csvkit/xsv" or "load it into pandas" — heavyweight for a 30-second question.

**Source:** This is a perennial complaint in r/learnprogramming and r/datasets ("huge CSV won't open in Excel"). A recent survey of the workaround landscape — 20+ tools people install just to peek at a CSV — is here: <https://dadroit.com/blog/open-big-csv/>. csvpeek is the zero-install version of that 30-second peek. *(Note: this run couldn't retrieve a single canonical Reddit thread URL via search, so the survey article is cited as the source instead.)*

**csvpeek** is a single-file, standard-library-only Python CLI that **streams** the file — constant memory, so a 10 GB CSV works fine.

## Install / run

No dependencies. Python 3.8+.

```bash
python3 csvpeek.py data.csv
# or: chmod +x csvpeek.py && ./csvpeek.py data.csv
```

## What it does

- Auto-detects the delimiter (`,` `;` tab `|`) and whether row 1 is a header
- Prints a summary (delimiter, columns, exact row count, ragged-row count) plus the first N rows as an aligned table
- `--cols` — just list column names with their index
- `--stats` — full streaming scan: per-column inferred type (int/float/str/mixed), non-null %, distinct count, min/max/mean for numeric columns
- Reads stdin with `-`, handles quoted fields, embedded commas/newlines, and non-UTF-8 bytes gracefully

## Example

```bash
$ python3 csvpeek.py sample.csv --stats -n 3
file:      sample.csv
delimiter: comma
header:    yes
columns:   5
rows:      5,000

id  name    city      score  joined
--  ------  --------  -----  ----------
1   user_1            12.21  2026-03-11
2   user_2  Berlin    94.63  2026-04-12
3   user_3  New York  63.05  2026-07-13
… 4,997 more rows

column  type   non-null  distinct  min  max    mean
------  -----  --------  --------  ---  -----  -----
id      int    100%      5000      1    5000   2500
name    str    100%      5000
city    str    80%       4
score   float  100%      3953      0.0  99.95  49.56
joined  str    100%      70
```

## Flags

| Flag | Meaning |
|---|---|
| `-n, --head N` | rows to preview (default 10) |
| `-d, --delimiter X` | override delimiter detection |
| `--no-header` | first row is data; columns named col0..colN |
| `--cols` | list columns and exit |
| `--stats` | per-column type/stats scan (reads whole file, still streaming) |

Exit codes: `0` ok, `1` file/parse error, `2` usage error.

## Tests

```bash
python3 test_csvpeek.py   # 8 tests, stdlib unittest
```

Tested clean in a Linux sandbox (Python 3.10): unit tests pass; manually verified on a 5,000-row fixture, semicolon files, stdin, and error paths.
