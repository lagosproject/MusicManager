from music_manager.core.tracks import extract_track

TRACK = {"uri": "spotify:track:1", "name": "Gasolina", "artists": [{"name": "Daddy Yankee"}]}


def test_item_key_current_api():
    assert extract_track({"added_at": "x", "item": TRACK}) is TRACK


def test_track_key_older_responses_and_cache():
    assert extract_track({"added_at": "x", "track": TRACK}) is TRACK


def test_bare_track():
    assert extract_track(TRACK) is TRACK


def test_removed_or_unavailable_entries_give_none():
    assert extract_track({"added_at": "x", "item": None}) is None
    assert extract_track({"added_at": "x", "track": None}) is None


def test_boolean_track_value_is_ignored():
    # Some payloads carry "track": True/False next to the real "item"
    assert extract_track({"track": True, "item": TRACK}) is TRACK


def test_not_a_dict():
    assert extract_track(None) is None
    assert extract_track("spotify:track:1") is None
    assert extract_track([TRACK]) is None
