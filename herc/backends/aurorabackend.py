
class BackendInitException(Exception):
    """Backend failed to initialize for some reason. Caller should either bail or fall back
    to a different backend."""
    pass
