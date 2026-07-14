# ghostchars

**The problem:** You copy code from a website, PDF, Word doc, Slack, or Zoom chat, and it refuses to run with a baffling error — `SyntaxError: invalid character '“'`, `invalid non-printable character U+200B`, `Invalid or unexpected token` — even though the code *looks identical* to the original. The culprits are invisible characters (zero-width spaces, BOM, bidi controls) and ASCII look-alikes (smart quotes, en/em dashes, non-breaking spaces) that editors silently hide. This bites beginners constantly and is a recurring complaint in programming communities like r/learnprogramming.

**Sources documenting the pain point** (Reddit itself is not crawlable from this build environment, so closest citable write-ups are used):

- https://dev.to/lavary/how-to-fix-syntaxerror-invalid-non-printable-character-4f58
- https://trackjs.com/javascript-errors/invalid-or-unexpected-token/
- https://github.com/rstudio/learnr/issues/639 (curly quotes from copy/paste breaking learners' code)
- Bonus: the bidi-control detection also covers the "Trojan Source" attack (CVE-2021-42574)

## What it does

`ghostchars` scans files (or stdin) for 44 invisible or confusable Unicode characters, reports each one with `file:line:col`, the Unicode name, and a caret pointing at the exact spot — and can repair the file in place.

## Install / run

Single file, Python 3.8+, standard library only.

```
curl -O https://raw.githubusercontent.com/sayedRaheel/startup-factory/main/2026-07-14/ghostchars.py
python3 ghostchars.py --help
```

## Usage

```
python3 ghostchars.py app.py                 # report offenders with context
python3 ghostchars.py src/*.py --json        # machine-readable output
python3 ghostchars.py app.py --fix           # repair in place (keeps app.py.bak)
python3 ghostchars.py app.py --fix --no-backup
cat snippet.py | python3 ghostchars.py -     # scan stdin
pbpaste | python3 ghostchars.py - --fix      # clean code on your clipboard (macOS)
```

Exit codes: `0` clean, `1` offenders found (CI-friendly), `2` usage/IO error.

## Example

```
$ python3 ghostchars.py examples/pasted_from_blog.py
examples/pasted_from_blog.py:2:9: U+200B ZERO WIDTH SPACE  [strip]
    greeting␀ = “Hello, world”
            ^
examples/pasted_from_blog.py:2:13: U+201C LEFT DOUBLE QUOTATION MARK  [replace with '"']
...
$ python3 examples/pasted_from_blog.py        # fails with SyntaxError
$ python3 ghostchars.py examples/pasted_from_blog.py --fix
$ python3 examples/pasted_from_blog.py
Hello, world 7
```

## What it catches

Invisible (stripped): zero-width space/joiner/non-joiner, word joiner, BOM (U+FEFF), soft hyphen, and all 11 bidirectional control characters. Confusable (replaced with ASCII): curly single/double quotes, primes, en/em dashes, minus sign, non-breaking and 8 other exotic spaces, ideographic space, ellipsis, line/paragraph separators.

## Tests

```
python3 test_ghostchars.py    # 13 tests, all passing at commit time
```

Built and tested in a Linux sandbox on 2026-07-14 (Python 3.10). Not experimental — tested clean.
