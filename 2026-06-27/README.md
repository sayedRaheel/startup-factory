# curl2code

Convert a `cURL` command into runnable **Python (requests)**, **JavaScript
(fetch)**, or **HTTPie** code — entirely offline, standard library only.

## The problem

You hit "Copy as cURL" in your browser's DevTools (or grab a curl example from
some API's docs) and now you need it as actual code in your project. Doing it by
hand — mapping every `-H` to a header dict, figuring out where the body goes,
decoding `-u user:pass` — is fiddly and easy to get wrong. The popular fix,
[curlconverter.com](https://curlconverter.com/), means pasting commands that
often contain live auth tokens and cookies into a third-party website.

`curl2code` does the same conversion locally from your terminal, so nothing
leaves your machine.

## Source / motivation

This is a recurring ask among developers — "how do I turn this curl command into
`requests`/`fetch` code?" comes up constantly on r/learnpython and r/webdev, and
the existence and popularity of the web tool below is the clearest signal of the
demand:

- curlconverter (the de-facto web tool people reach for): https://curlconverter.com/

(Web search surfaced the recurring need and the dominant web tool rather than a
single canonical thread; the citation above is the representative source.)

## Install / run

No installation, no dependencies — just Python 3.8+ (uses only the standard
library):

```bash
python3 curl2code.py --help
```

Optionally drop it on your `PATH`:

```bash
chmod +x curl2code.py
mv curl2code.py ~/.local/bin/curl2code
```

## Usage

```
curl2code [-t {python,fetch,httpie}] '<curl command>'
```

Pass the command as a quoted argument, or pipe it via stdin (handy straight
from the clipboard).

### Examples

Python (default target):

```bash
$ python3 curl2code.py "curl https://api.example.com/users -H 'Accept: application/json'"
import requests

headers = {'Accept': 'application/json'}

response = requests.get("https://api.example.com/users", headers=headers)
print(response.status_code)
print(response.text)
```

POST with a JSON body becomes idiomatic `json=`:

```bash
$ python3 curl2code.py -t python \
  "curl -X POST -H 'Content-Type: application/json' \
   --data-raw '{\"name\":\"Ada\"}' https://api.example.com/users"
import requests

json_data = {'name': 'Ada'}

response = requests.post("https://api.example.com/users", json=json_data)
print(response.status_code)
print(response.text)
```

JavaScript `fetch`:

```bash
$ python3 curl2code.py -t fetch "curl -X POST -d 'x=1' https://x.com"
const response = await fetch("https://x.com", {
  "method": "POST",
  "body": "x=1"
});
const text = await response.text();
console.log(response.status, text);
```

HTTPie:

```bash
$ python3 curl2code.py -t httpie "curl -G -d q=cli -u me:secret https://api.example.com/search"
http GET 'https://api.example.com/search?q=cli' -a me:secret
```

From stdin:

```bash
$ pbpaste | python3 curl2code.py        # macOS clipboard -> Python
$ cat sample_curl.txt | python3 curl2code.py -t fetch
```

Run `bash demo.sh` for a guided tour.

## What it understands

- Method: `-X/--request` (defaults to GET, or POST when a body is present)
- Headers: `-H/--header`, plus `-b/--cookie`, `-A/--user-agent`, `-e/--referer`
- Body: `-d/--data`, `--data-raw`, `--data-binary`, `--data-urlencode`
  (multiple `-d` flags are joined with `&`)
- JSON bodies are detected and emitted idiomatically (`json=` in Python,
  `field:=value` in HTTPie)
- Basic auth: `-u/--user`
- `-G/--get` moves data into the query string (matching curl's behaviour)
- `--compressed`, `-k/--insecure`, `-L`, line-continuation backslashes, and
  `--flag=value` syntax
- Unknown flags are skipped rather than crashing the tool

## Limitations

- File uploads (`-F/--form`, `@file` data) are not expanded.
- Designed for the common HTTP-request shapes that DevTools and API docs emit,
  not every exotic curl flag.

## Tests

```bash
python3 test_curl2code.py
```

20 unit tests cover parsing and all three code generators.

## License

Public domain / do whatever you want.
