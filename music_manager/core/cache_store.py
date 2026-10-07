"""Re-export from music_core to maintain backward compatibility."""
from music_core.core.cache_store import (
    slim_track,
    slim_item,
    slim_items,
    slim_cache,
    atomic_write_json,
)

__all__ = [
    "slim_track",
    "slim_item",
    "slim_items",
    "slim_cache",
    "atomic_write_json",
]
