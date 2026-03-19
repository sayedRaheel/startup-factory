import argparse

def get_parser():
    parser = argparse.ArgumentParser(
        prog="engram",
        description="Invisible flight recorder for AI context"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("start", help="Spawns the background watcher daemon")
    subparsers.add_parser("stop", help="Stops the background watcher daemon")
    
    dump_p = subparsers.add_parser("dump", help="Dumps the token-compressed context to stdout")
    dump_p.add_argument("-o", "--out", help="Optional: Output to a specific file (e.g., .cursorrules) instead of stdout")
    
    return parser
