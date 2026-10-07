"""Re-export from music_core to maintain backward compatibility."""
from music_core.core.merge_tree import (
    normalize_playlist_id,
    is_valid_playlist_id,
    execution_order,
    consumers,
    propagation_plan,
    subtree_playlists,
    leaf_playlists,
    tree_playlist_ids,
    all_leaf_playlists,
    creates_cycle,
    shared_targets,
    tree_lines,
)

__all__ = [
    "normalize_playlist_id",
    "is_valid_playlist_id",
    "execution_order",
    "consumers",
    "propagation_plan",
    "subtree_playlists",
    "leaf_playlists",
    "tree_playlist_ids",
    "all_leaf_playlists",
    "creates_cycle",
    "shared_targets",
    "tree_lines",
]
