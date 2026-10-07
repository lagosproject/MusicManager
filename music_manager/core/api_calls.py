"""Re-export from music_core to maintain backward compatibility."""
from music_core.core.api_calls import (
    MAX_WAIT_SECONDS,
    make_session,
    humanize_seconds,
    retry_after_seconds,
    call_with_retry,
    describe_api_error,
)

__all__ = [
    "MAX_WAIT_SECONDS",
    "make_session",
    "humanize_seconds",
    "retry_after_seconds",
    "call_with_retry",
    "describe_api_error",
]
