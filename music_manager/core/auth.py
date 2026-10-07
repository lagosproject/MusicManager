"""Re-export from music_core to maintain backward compatibility."""
from music_core.core.auth import explain_login_error, clear_saved_token

__all__ = ["explain_login_error", "clear_saved_token"]
