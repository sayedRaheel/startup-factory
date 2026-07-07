# devserve

Zero-dependency local dev server that gets out of your way: **CORS headers on
by default**, **no-cache responses**, **SPA fallback**, and a tiny **same-origin
API proxy** — so `fetch("/api/...")` from your static frontend just works
against a local backend, with no CORS ceremony and no stale-cache mysteries.

## The problem

`python -m http.server` (and most quick static servers) send no CORS headers
and let the browser cache aggressively, so local frontend work regularly dies
on `blocked by CORS policy` errors or "why is my old JS still loading?"
moments. CORS-in-local-dev is one of the most persistently complained-about
frictions among web developers — see the roundup of developer/Reddit
workarounds in [this dev-environment CORS guide](https://www.wisp.blog/blog/the-ultimate-guide-to-setting-up-your-dev-environment-for-cors-and-live-apis).
(Reddit blocks automated crawling, so a direct thread link couldn't be
captured this run; the pain point is sourced from that aggregation instead.)

## Install / run

Single file, Python 3.8+, standard library only:

```sh
python3 devserve.py                              # serve . on :8000, CORS *, no-cache
python3 devserve.py -d dist -p 5000 --spa        # SPA build: unknown routes -> index.html
python3 devserve.py --proxy /api=http://localhost:3000
python3 devserve.py --cors http://localhost:5173 # lock CORS to one origin
python3 devserve.py --no-cors --cache            # behave like a plain server
```

## Features

- `--cors ORIGIN` / `--no-cors` — `Access-Control-Allow-Origin` and friends on
  every response, plus proper `204` preflight handling for `OPTIONS`.
- no-cache by default (`--cache` to opt out) — never debug a stale bundle again.
- `--spa` — extension-less unknown paths serve `index.html`; real files and
  missing assets (`/logo.png`) still behave normally (404s stay 404s).
- `--proxy /prefix=http://host:port` (repeatable) — forwards method, body and
  headers; full path is preserved (`/api/users` → `upstream/api/users`), like
  Vite's proxy default. Upstream down returns a clear `502`.
- Sensible exit codes: `2` bad directory, `3` port in use (with a suggestion).

## Example

```sh
$ python3 devserve.py -d dist --spa --proxy /api=http://localhost:3000
devserve 1.0.0 serving /home/you/app/dist
  http://127.0.0.1:8000/  [CORS=*, no-cache, SPA fallback, proxy /api -> http://localhost:3000]
```

## Tests

```sh
python3 test_devserve.py   # 12 tests, spins up real servers on ephemeral ports
```

Tested clean in a Linux sandbox (Python 3.10).
