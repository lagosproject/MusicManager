from typing import Dict, List, Set

from spotipy.exceptions import SpotifyException

from music_manager.core.spotify_client import SpotifyClient


class FakeSpotifyApi:
    """In-memory stand-in for spotipy.Spotify: only the playlist calls the merges use."""

    def __init__(self, playlists: Dict[str, List[str]]):
        self.playlists = {pid: list(uris) for pid, uris in playlists.items()}
        self.read_calls: List[str] = []
        self.add_calls: List[tuple] = []
        self.fail_writes: Set[str] = set()
        self.fail_reads: Set[str] = set()
        self.rate_limited = False
        self.snapshot_n = 0
        self.foreign: Set[str] = set()  # playlists owned by somebody else
        self.remove_calls: List[list] = []   # URIs of each remove-all-occurrences request
        self.insert_failures: Set[str] = set()  # URIs whose re-insertion at a position fails
        self.stale_reads = 0                 # how many playlist reads still show the state before the last write
        self._before_write: Dict[str, list] = {}
        self.track_info: Dict[str, dict] = {}  # uri -> full track dict, to give tracks names and artists
        self.saved: Set[str] = set()
        self.saved_page_reads = 0
        self.saved_add_batches: List[List[str]] = []
        self.contains_batches: List[int] = []
        self.fail_saving = False

    def current_user_saved_tracks(self, limit=20, offset=0):
        self.saved_page_reads += 1
        uris = sorted(self.saved)
        items = [{"track": self.track_info.get(u) or {"uri": u, "name": u, "artists": []}} for u in uris[offset:offset + limit]]
        return {"items": items, "total": len(uris)}

    def current_user_saved_tracks_contains(self, tracks):
        if len(tracks) > 40:
            raise SpotifyException(400, -1, "Too many uris requested")  # measured limit of /me/library/contains
        self.contains_batches.append(len(tracks))
        return [t in self.saved for t in tracks]

    def current_user_saved_tracks_add(self, tracks):
        if self.fail_saving:
            raise SpotifyException(403, -1, "Forbidden")
        if len(tracks) > 40:
            raise SpotifyException(400, -1, "Too many uris requested")
        self.saved_add_batches.append(list(tracks))
        self.saved.update(tracks)

    def _check_rate_limit(self):
        if self.rate_limited:  # what Spotify did to the playlist endpoints: 429 asking for ~22 hours
            raise SpotifyException(429, -1, "rate limit", headers={"Retry-After": "78994"})

    def current_user_playlists(self, limit=50, offset=0):
        self._check_rate_limit()
        items = [
            {"id": p, "name": f"Lista {p[:4]}", "collaborative": False,
             "owner": {"id": "otra-persona" if p in self.foreign else "test"}}
            for p in self.playlists
        ]
        return {"items": items[offset:offset + limit], "total": len(items)}

    def playlist(self, playlist_id, fields=None):
        self._check_rate_limit()
        return {"name": f"Lista {playlist_id[:4]}", "images": [], "external_urls": {},
                "snapshot_id": f"snap{self.snapshot_n}"}

    def playlist_items(self, playlist_id, offset=0, limit=100, additional_types=None):
        self._check_rate_limit()
        if playlist_id in self.fail_reads:
            raise SpotifyException(404, -1, "Not found")
        self.read_calls.append(playlist_id)
        uris = self.playlists[playlist_id]
        if self.stale_reads > 0 and playlist_id in self._before_write and offset == 0:
            self.stale_reads -= 1
            uris = self._before_write[playlist_id]
        page = uris[offset:offset + limit]
        # None stands for an unavailable entry: it still takes a position in the playlist
        items = [{"item": None} if u is None else {"item": self.track_info.get(u) or {"uri": u, "name": u, "artists": []}}
                 for u in page]
        return {"items": items, "total": len(uris)}

    def playlist_remove_all_occurrences_of_items(self, playlist_id, items, snapshot_id=None):
        if playlist_id in self.fail_writes:
            raise SpotifyException(403, -1, "Forbidden")
        self.remove_calls.append(list(items))
        self._before_write[playlist_id] = list(self.playlists[playlist_id])
        gone = set(items)
        self.playlists[playlist_id] = [u for u in self.playlists[playlist_id] if u not in gone]
        self.snapshot_n += 1
        return {"snapshot_id": f"snap{self.snapshot_n}"}

    def playlist_add_items(self, playlist_id, uris, position=None):
        if playlist_id in self.fail_writes:
            raise SpotifyException(403, -1, "Forbidden")
        if position is not None and any(u in self.insert_failures for u in uris):
            raise SpotifyException(500, -1, "Server error")
        self._before_write[playlist_id] = list(self.playlists[playlist_id])
        self.add_calls.append((playlist_id, list(uris)))
        current = self.playlists[playlist_id]
        if position is None:
            current.extend(uris)
        else:
            if position > len(current):
                raise SpotifyException(400, -1, "Index out of range")
            current[position:position] = uris


def make_client(playlists: Dict[str, List[str]]) -> SpotifyClient:
    client = SpotifyClient.__new__(SpotifyClient)  # skip __init__: no OAuth, no network
    client.sp = FakeSpotifyApi(playlists)
    return client


def pid(letter: str) -> str:
    """A 22-character playlist ID built from one letter."""
    return letter * 22


def uri(n) -> str:
    return f"spotify:track:{n}"
