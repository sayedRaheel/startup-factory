# portkill

A tiny, dependency-free CLI to find and kill whatever process is holding a TCP port.

## The problem

Every developer knows this one: you go to start your dev server and get
`Error: listen EADDRINUSE: address already in use :::3000` — a previous run
crashed, or some stray process is squatting on the port. Fixing it means
remembering the right `lsof` / `netstat` incantation for your OS, copying out a
PID, and running `kill`. It's a small, constant papercut that shows up
repeatedly across r/webdev, r/learnprogramming, and r/commandline (and has
spawned a dozen near-identical "kill my port" snippets on dev.to).

`portkill` collapses that into one command:

```
portkill 3000
```

## Usage

```
portkill <port>          # show what's on the port, ask, then kill it
portkill -l 3000         # just list, don't kill
portkill -y 3000         # skip the confirmation prompt
portkill -f 3000         # force kill (SIGKILL / taskkill /F)
portkill -h              # help
```

Example:

```
$ portkill 3000
Port 3000 is held by:
  PID 4821  (node)
Kill 1 process(es)? [y/N] y
  killed 4821
Port 3000 is free.
```

## Install

No dependencies — Python 3 standard library only. Works on macOS, Linux, and
Windows (uses `lsof` on Unix, `netstat`/`taskkill` on Windows).

```
chmod +x portkill.py
./portkill.py 3000
# or drop it on your PATH as `portkill`
```

## Notes

Tested on Linux against a live listener: lists, kills, and confirms the port is
freed. The Windows path uses `netstat -ano` + `taskkill` and follows the same
logic but was not exercised on a Windows host in this build.

---
*Built automatically by a daily Cowork "mini tool builder" task.*
*Idea sourced from the recurring EADDRINUSE / "port already in use" discussions
in the web-dev community (e.g. https://dev.to/osalumense/how-to-kill-a-process-occupying-a-port-on-windows-macos-and-linux-gj8).*
