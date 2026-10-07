import json

import pytest

from music_manager.core.cache_store import atomic_write_json, slim_cache, slim_item, slim_items, slim_track
from music_manager.core.tracks import extract_track


def fat_item(n=1):
    """Shaped like a real playlist item from the API (many unused fields)."""
    return {
        "added_at": "2026-04-30T21:00:00Z",
        "added_by": {"id": "u", "external_urls": {"spotify": "https://x"}, "href": "h", "type": "user", "uri": "u"},
        "is_local": False,
        "primary_color": None,
        "video_thumbnail": {"url": None},
        "item": {
            "id": f"id{n}", "uri": f"spotify:track:{n}", "name": f"Cancion {n}", "duration_ms": 200000,
            "explicit": False, "is_playable": True, "disc_number": 1, "track_number": 3, "type": "track",
            "href": "https://api", "external_ids": {"isrc": "X"}, "external_urls": {"spotify": "https://x"},
            "artists": [{"id": "a1", "name": "Artista", "href": "h", "type": "artist", "uri": "u", "external_urls": {}}],
            "album": {"name": "Album", "release_date": "2020", "total_tracks": 12,
                      "images": [{"url": "big", "height": 640}, {"url": "med", "height": 300}, {"url": "small", "height": 64}]},
        },
    }


def test_slim_item_keeps_only_what_the_app_uses():
    slim = slim_item(fat_item(1))

    assert set(slim) == {"item", "added_at"}
    assert slim["item"] == {
        "id": "id1", "uri": "spotify:track:1", "name": "Cancion 1", "duration_ms": 200000,
        "explicit": False,
        "artists": [{"id": "a1", "name": "Artista"}],
        "album": {"name": "Album", "release_date": "2020", "images": [{"url": "big"}]},
    }


def test_slim_item_is_still_readable_by_extract_track():
    assert extract_track(slim_item(fat_item(1)))["uri"] == "spotify:track:1"


def test_slimming_twice_changes_nothing():
    once = slim_item(fat_item(1))
    assert slim_item(once) == once


def test_old_track_key_and_bare_tracks_are_normalised_to_item():
    track = fat_item(2)["item"]
    assert slim_item({"track": track})["item"]["uri"] == "spotify:track:2"
    assert slim_item(track)["item"]["uri"] == "spotify:track:2"


def test_unusable_entries_are_dropped():
    assert slim_item({"added_at": "x", "item": None}) is None
    assert slim_items([fat_item(1), {"item": None}, None, "x"]) == [slim_item(fat_item(1))]


def test_tracks_without_album_or_artists_do_not_break():
    slim = slim_track({"uri": "spotify:local:a:b:c:1", "name": "Local"})
    assert slim["artists"] == [] and "album" not in slim


def test_slimmed_cache_is_much_smaller():
    cache = {"pl": [fat_item(i) for i in range(200)]}

    before = len(json.dumps(cache))
    after = len(json.dumps(slim_cache(cache)))

    assert after < before * 0.4  # this sample is leaner than a real item; the real cache shrinks more


def test_atomic_write_roundtrip_and_no_temp_file_left(tmp_path):
    path = tmp_path / "cache.json"

    atomic_write_json(path, {"é": [1, 2]}, compact=True)

    assert json.loads(path.read_text(encoding="utf-8")) == {"é": [1, 2]}
    assert path.read_text(encoding="utf-8") == '{"é":[1,2]}'
    assert list(tmp_path.iterdir()) == [path]


def test_a_failed_write_keeps_the_previous_file_intact(tmp_path):
    path = tmp_path / "cache.json"
    atomic_write_json(path, {"ok": True})

    with pytest.raises(TypeError):
        atomic_write_json(path, {"bad": object()})

    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}
    assert list(tmp_path.iterdir()) == [path]
