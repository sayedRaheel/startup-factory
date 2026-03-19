class EngramError(Exception):
    """Base error class for Engram"""
    pass

class ConfigError(EngramError):
    """Configuration related errors"""
    pass

class DaemonError(EngramError):
    """Daemon lifecycle errors"""
    pass
