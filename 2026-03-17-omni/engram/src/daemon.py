import os
import sys
import time
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.db import DB
from src.compressor import compress_code
import pathspec

PID_FILE = ".engram.pid"
DB_PATH = ".engram/engram.db"

def daemonize():
    if os.name != 'posix':
        print("Daemonize only supported on POSIX")
        return
    
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.exit(1)
        
    os.setsid()
    os.umask(0)
    
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.exit(1)
        
    sys.stdout.flush()
    sys.stderr.flush()
    
    with open('/dev/null', 'r') as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open('.engram.out', 'a+') as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
    with open('.engram.err', 'a+') as f:
        os.dup2(f.fileno(), sys.stderr.fileno())
        
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

class WatcherHandler(FileSystemEventHandler):
    def __init__(self, db, ignore_spec):
        self.db = db
        self.ignore_spec = ignore_spec

    def should_ignore(self, path):
        rel_path = os.path.relpath(path, start='.')
        if rel_path.startswith('.git') or '.engram' in rel_path or rel_path.startswith('venv') or '__pycache__' in rel_path:
            return True
        if self.ignore_spec and self.ignore_spec.match_file(rel_path):
            return True
        return False

    def process(self, event):
        if event.is_directory:
            return
        if self.should_ignore(event.src_path):
            return
        
        event_type = event.event_type
        path = event.src_path
        
        hash_val = ""
        compressed = ""
        if event_type in ('created', 'modified'):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    hash_val = hashlib.sha256(content.encode('utf-8')).hexdigest()
                    compressed = compress_code(content)
            except Exception:
                return # Ignore binary files or unreadable targets
                
        self.db.log_event(path, event_type, hash_val, compressed)

    def on_created(self, event): self.process(event)
    def on_modified(self, event): self.process(event)
    def on_deleted(self, event): self.process(event)

def load_ignore_spec():
    lines = []
    for ignore_file in ['.gitignore', '.engramignore']:
        if os.path.exists(ignore_file):
            with open(ignore_file, 'r') as f:
                lines.extend(f.readlines())
    if not lines:
        return None
    return pathspec.PathSpec.from_lines('gitwildmatch', lines)

def start():
    daemonize()
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = DB(DB_PATH)
    ignore_spec = load_ignore_spec()
    
    event_handler = WatcherHandler(db, ignore_spec)
    observer = Observer()
    observer.schedule(event_handler, '.', recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
