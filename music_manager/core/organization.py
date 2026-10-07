import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence
from .genres import detect_genre_from_title
from .tracks import extract_track

# A suggestion this strong (the artist's songs are mostly in that playlist) is safe to preselect
SAFE_SUGGESTION_SCORE = 0.6

# artist key -> {playlist id -> number of tracks by that artist in the playlist}
ArtistIndex = Dict[str, Dict[str, int]]

@dataclass
class Suggestion:
    playlist_id: str
    score: float
    reason: str

def _normalize(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()

def artist_key(artist: Dict[str, Any]) -> str:
    """Stable key for an artist: its Spotify ID, or the normalised name when there is none."""
    if artist.get("id"):
        return artist["id"]
    name = _normalize(artist.get("name") or "")
    return f"name:{name}" if name else ""

def _track_artists(track: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [a for a in track.get("artists") or [] if isinstance(a, dict) and artist_key(a)]

def find_uncategorized(target_items: Sequence[Any], below_items: Iterable[Sequence[Any]]) -> List[Dict[str, Any]]:
    """Tracks of the target playlist that are in none of the playlists below it in the merge tree."""
    known = {
        t["uri"]
        for items in below_items
        for t in (extract_track(i) for i in items)
        if t and t.get("uri")
    }
    result = []
    for item in target_items:
        track = extract_track(item)
        if track and track.get("uri") and track["uri"] not in known:
            known.add(track["uri"])  # a track repeated in the target is listed once
            result.append(track)
    return result

def find_unplaced(saved_items: Sequence[Any], playlists_items: Iterable[Sequence[Any]]) -> List[Dict[str, Any]]:
    """
    Saved tracks that are in none of the given playlists, in the order Spotify lists them (most recently
    saved first). Each result carries "liked_at". Local files and episodes cannot be placed and are skipped.
    """
    placed = {
        t["uri"]
        for items in playlists_items
        for t in (extract_track(i) for i in items)
        if t and t.get("uri")
    }
    result = []
    for item in saved_items:
        track = extract_track(item)
        uri = (track or {}).get("uri")
        if not uri or not uri.startswith("spotify:track:") or uri in placed:
            continue
        placed.add(uri)  # a track saved twice is listed once
        result.append({**track, "liked_at": (item.get("added_at") or "") if isinstance(item, dict) else ""})
    return result

def group_by_destination(choices: Dict[str, str]) -> Dict[str, List[str]]:
    """{track uri: playlist id} -> {playlist id: [track uris]}, keeping the order."""
    groups: Dict[str, List[str]] = defaultdict(list)
    for uri, playlist_id in choices.items():
        groups[playlist_id].append(uri)
    return dict(groups)

def build_artist_index(playlists: Dict[str, Sequence[Any]]) -> ArtistIndex:
    """Counts, per artist, how many of their tracks each playlist holds. Built once, used for every track."""
    index: ArtistIndex = defaultdict(lambda: defaultdict(int))
    for playlist_id, items in playlists.items():
        for item in items:
            track = extract_track(item)
            for artist in _track_artists(track or {}):
                index[artist_key(artist)][playlist_id] += 1
    return {key: dict(counts) for key, counts in index.items()}

def suggest(track: Dict[str, Any], index: ArtistIndex, playlist_names: Dict[str, str]) -> List[Suggestion]:
    """
    Playlists where the track probably belongs, best first. Each artist of the track splits one
    point among the playlists that already hold their songs, so a big playlist does not win just
    for being big. A genre named in the title ("Salsa Version") adds a point to the matching playlist.
    """
    scores: Dict[str, float] = defaultdict(float)
    reasons: Dict[str, List[str]] = defaultdict(list)

    for artist in _track_artists(track):
        counts = {pid: n for pid, n in index.get(artist_key(artist), {}).items() if pid in playlist_names}
        total = sum(counts.values())
        for pid, n in counts.items():
            scores[pid] += n / total
            reasons[pid].append(f"{artist.get('name') or 'el artista'}: {n} canciones ahí")

    title_genre = detect_genre_from_title(track.get("name") or "")
    if title_genre:
        for pid, name in playlist_names.items():
            if title_genre.lower() in name.lower():
                scores[pid] += 1.0
                reasons[pid].append(f"el título dice «{title_genre}»")

    ranked = sorted(scores.items(), key=lambda pair: (-pair[1], playlist_names[pair[0]].lower()))
    return [Suggestion(pid, round(score, 3), "; ".join(reasons[pid])) for pid, score in ranked if score > 0]
