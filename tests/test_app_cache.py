import json

from music_manager.core.tracks import extract_track


def legacy_item(n):
    """A playlist item as the old app stored it: the whole Spotify payload."""
    return {
        "added_at": "2026-04-30T21:00:00Z",
        "added_by": {"id": "u", "href": "h", "type": "user", "uri": "u", "external_urls": {"spotify": "x"}},
        "is_local": False, "primary_color": None, "video_thumbnail": {"url": None},
        "item": {
            "id": f"id{n}", "uri": f"spotify:track:{n}", "name": f"Cancion {n}", "duration_ms": 1000,
            "explicit": False, "external_ids": {"isrc": "X"}, "external_urls": {"spotify": "x"}, "href": "h",
            "artists": [{"id": "a", "name": "Artista", "href": "h", "type": "artist", "uri": "u"}],
            "album": {"name": "A", "images": [{"url": "big", "height": 640}, {"url": "small", "height": 64}]},
        },
    }


def test_an_old_full_cache_is_slimmed_once_and_the_app_still_works(new_app, data_dir):
    path = data_dir / "tracks_cache.json"
    path.write_text(json.dumps({"PL": [legacy_item(i) for i in range(300)], "__saved_tracks__": []}), encoding="utf-8")
    size_before = path.stat().st_size

    at = new_app().run()

    assert not at.exception, [e.value for e in at.exception]
    assert path.stat().st_size < size_before / 2
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert [extract_track(i)["uri"] for i in saved["PL"]] == [f"spotify:track:{i}" for i in range(300)]
    assert "primary_color" not in saved["PL"][0] and "added_by" not in saved["PL"][0]
    assert saved["PL"][0]["added_at"] == "2026-04-30T21:00:00Z"
    assert list(data_dir.glob("*.tmp")) == []


def test_an_already_slim_cache_is_not_rewritten(new_app, data_dir):
    path = data_dir / "tracks_cache.json"
    new_app().run()  # nothing to load
    path.write_text(json.dumps({"PL": [{"item": {"id": "i", "uri": "spotify:track:1", "name": "N",
                                                  "duration_ms": 1, "artists": []}}]}), encoding="utf-8")
    before = path.stat().st_mtime_ns

    at = new_app().run()

    assert not at.exception, [e.value for e in at.exception]
    assert path.stat().st_mtime_ns == before
