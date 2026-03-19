# Tech Spec
* **Language**: Python 3 (Satisfies single-script distribution + environmental constraints)
* **Daemon**: Native POSIX double-fork
* **Storage**: SQLite3 with `PRAGMA journal_mode = WAL`
* **File Watcher**: `watchdog` library
* **Ignore Parser**: `pathspec` library
