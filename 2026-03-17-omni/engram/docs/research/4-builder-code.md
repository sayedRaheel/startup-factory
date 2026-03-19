# Builder Code
The implementation handles detached POSIX lifecycle. `src/daemon.py` routes changes into `src/compressor.py` before strictly locking the SQL transactions in `src/db.py`.
