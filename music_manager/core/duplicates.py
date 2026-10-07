"""Re-export from music_core to maintain backward compatibility."""
from music_core.core.duplicates import (
    MODE_SAME_TRACK,
    MODE_SAME_TITLE,
    DuplicateGroup,
    DedupeResult,
    DedupeOps,
    title_key,
    find_duplicate_groups,
    plan_operations,
    format_duration,
    describe_copy,
    track_url,
    copies_to_remove,
    remove_duplicates,
)

__all__ = [
    "MODE_SAME_TRACK",
    "MODE_SAME_TITLE",
    "DuplicateGroup",
    "DedupeResult",
    "DedupeOps",
    "title_key",
    "find_duplicate_groups",
    "plan_operations",
    "format_duration",
    "describe_copy",
    "track_url",
    "copies_to_remove",
    "remove_duplicates",
]
