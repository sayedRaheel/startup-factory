#!/usr/bin/env python3
"""
portkill - find and kill the process holding a TCP port.

Solves the everyday "address already in use" / EADDRINUSE frustration:
your dev server crashed or a stray process is squatting on port 3000 and
you can't restart. Instead of remembering the lsof/netstat + kill dance for
each OS, just run:  portkill 3000

Cross-platform (macOS, Linux, Windows). Standard library only.
"""

import argparse
import os
import re
import signal
import subprocess
import sys


def _run(cmd):
    """Run a command, return stdout as text ('' on failure)."""
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )
        return out.stdout or ""
    except (OSError, FileNotFoundError):
        return ""


def find_pids_unix(port):
    """Return a set of PIDs listening on `port` using lsof (macOS/Linux)."""
    pids = set()
    # -t: terse (pids only)  -i: internet address  -sTCP:LISTEN: only listeners
    out = _run(["lsof", f"-ti", f"tcp:{port}", "-sTCP:LISTEN"])
    for line in out.split():
        line = line.strip()
        if line.isdigit():
            pids.add(int(line))
    if not pids:
        # Fallback: some lsof builds dislike the combined flags above.
        out = _run(["lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n"])
        for line in out.splitlines():
            if f":{port} " in line or line.rstrip().endswith(f":{port}"):
                parts = line.split()
                if len(parts) > 1 and parts[1].isdigit():
                    pids.add(int(parts[1]))
    return pids


def find_pids_windows(port):
    """Return a set of PIDs listening on `port` using netstat (Windows)."""
    pids = set()
    out = _run(["netstat", "-ano", "-p", "TCP"])
    pat = re.compile(r":%d\b" % port)
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        cols = line.split()
        # cols: Proto  Local-Address  Foreign-Address  State  PID
        if len(cols) >= 5 and pat.search(cols[1]):
            if cols[-1].isdigit():
                pids.add(int(cols[-1]))
    return pids


def find_pids(port):
    if os.name == "nt":
        return find_pids_windows(port)
    return find_pids_unix(port)


def proc_name(pid):
    """Best-effort human-readable name for a pid."""
    if os.name == "nt":
        out = _run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
        m = re.match(r'"([^"]+)"', out.strip())
        return m.group(1) if m else "?"
    out = _run(["ps", "-p", str(pid), "-o", "comm="])
    return out.strip() or "?"


def kill(pid, force=False):
    """Terminate a pid. Returns True on apparent success."""
    try:
        if os.name == "nt":
            cmd = ["taskkill", "/PID", str(pid)]
            if force:
                cmd.append("/F")
            res = subprocess.run(cmd, capture_output=True, text=True)
            return res.returncode == 0
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
        return True
    except (ProcessLookupError, PermissionError, OSError) as e:
        print(f"  could not kill {pid}: {e}", file=sys.stderr)
        return False


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="portkill",
        description="Find and kill the process listening on a TCP port.",
    )
    p.add_argument("port", type=int, help="TCP port number (e.g. 3000)")
    p.add_argument(
        "-l", "--list", action="store_true",
        help="only list the process(es) on the port, don't kill",
    )
    p.add_argument(
        "-f", "--force", action="store_true",
        help="force kill (SIGKILL / taskkill /F)",
    )
    p.add_argument(
        "-y", "--yes", action="store_true",
        help="skip the confirmation prompt",
    )
    args = p.parse_args(argv)

    if not (0 < args.port < 65536):
        p.error("port must be between 1 and 65535")

    pids = find_pids(args.port)
    if not pids:
        print(f"Nothing is listening on port {args.port}.")
        return 0

    print(f"Port {args.port} is held by:")
    for pid in sorted(pids):
        print(f"  PID {pid}  ({proc_name(pid)})")

    if args.list:
        return 0

    if not args.yes:
        try:
            ans = input(f"Kill {len(pids)} process(es)? [y/N] ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y", "yes"):
            print("Aborted.")
            return 1

    killed = 0
    for pid in sorted(pids):
        if kill(pid, force=args.force):
            killed += 1
            print(f"  killed {pid}")
    remaining = len(pids) - killed
    if remaining:
        print(
            f"Freed {killed} of {len(pids)}. "
            f"Try again with --force if {remaining} won't die.",
            file=sys.stderr,
        )
        return 1
    print(f"Port {args.port} is free.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
