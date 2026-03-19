#!/usr/bin/env python3
import sys
import os

# Ensure absolute imports work smoothly in local environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cli import get_parser
from src.daemon import start as daemon_start, PID_FILE
from src.dump import generate_dump

def main():
    parser = get_parser()
    args = parser.parse_args()
    
    if args.command == "start":
        print("Starting Engram daemon... It will now run invisibly.")
        daemon_start()
    elif args.command == "stop":
        print("Stopping Engram daemon...")
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid_str = f.read().strip()
            if pid_str.isdigit():
                pid = int(pid_str)
                try:
                    import signal
                    os.kill(pid, signal.SIGTERM)
                    print(f"Killed process {pid}")
                except ProcessLookupError:
                    print("Process not found. Cleaning up PID file.")
            os.remove(PID_FILE)
        else:
            print("Daemon not running.")
    elif args.command == "dump":
        generate_dump(args.out)

if __name__ == "__main__":
    main()
