from music_manager.core.genres import detect_genre_from_title
from music_manager.core.organization import artist_key, build_artist_index, find_uncategorized, suggest


def tr(n, artist="Artista", artist_id=None, name=None):
    return {"item": {"uri": f"spotify:track:{n}", "name": name or f"Cancion {n}",
                     "artists": [{"id": artist_id or f"id-{artist}", "name": artist}]}}


def plain(item):
    return item["item"]


NAMES = {"SAL": "Salsa clásica", "REG": "Reggaeton", "BAC": "Bachata"}


# ---------- uncategorized ----------

def test_tracks_in_the_target_but_in_nothing_below_are_uncategorized():
    target = [tr(1), tr(2), tr(3)]
    below = [[tr(1)], [tr(2)]]

    assert find_uncategorized(target, below) == [plain(tr(3))]


def test_saved_tracks_are_not_a_source_any_more():
    # A liked song that sits in the target but in no playlist below it still needs a home
    assert find_uncategorized([tr(1)], []) == [plain(tr(1))]


def test_removed_entries_and_tracks_without_uri_are_skipped():
    assert find_uncategorized([{"item": None}, {"item": {"name": "x"}}, tr(1)], [[]]) == [plain(tr(1))]


# ---------- artist index ----------

def test_index_counts_tracks_per_artist_per_playlist():
    index = build_artist_index({"SAL": [tr(1, "Celia"), tr(2, "Celia"), tr(3, "Tito")], "REG": [tr(4, "Celia")]})

    assert index["id-Celia"] == {"SAL": 2, "REG": 1}
    assert index["id-Tito"] == {"SAL": 1}


def test_artist_key_falls_back_to_the_normalised_name():
    assert artist_key({"id": "abc", "name": "X"}) == "abc"
    assert artist_key({"name": "Rauw  Alejandro"}) == artist_key({"name": "rauw alejandro"}) == "name:rauw alejandro"
    assert artist_key({}) == ""


# ---------- suggestions ----------

def test_the_playlist_that_already_holds_the_artist_wins():
    index = build_artist_index({"SAL": [tr(1, "Celia"), tr(2, "Celia")], "REG": [tr(3, "Bad Bunny")]})

    best = suggest(plain(tr(9, "Celia")), index, NAMES)[0]

    assert best.playlist_id == "SAL" and "Celia: 2 canciones" in best.reason


def test_a_big_playlist_does_not_win_only_for_being_big():
    # The artist has 9 tracks in SAL and 1 in REG: SAL still wins, but REG keeps its small share
    index = build_artist_index({"SAL": [tr(i, "Celia") for i in range(9)], "REG": [tr(20, "Celia")]})

    ranked = suggest(plain(tr(99, "Celia")), index, NAMES)

    assert [s.playlist_id for s in ranked] == ["SAL", "REG"]
    assert ranked[0].score == 0.9 and ranked[1].score == 0.1


def test_an_unknown_artist_gets_no_suggestion():
    index = build_artist_index({"SAL": [tr(1, "Celia")]})

    assert suggest(plain(tr(9, "Desconocido")), index, NAMES) == []


def test_playlists_outside_the_allowed_destinations_are_ignored():
    index = build_artist_index({"SAL": [tr(1, "Celia")], "OTRA": [tr(2, "Celia")]})

    assert [s.playlist_id for s in suggest(plain(tr(9, "Celia")), index, NAMES)] == ["SAL"]


def test_a_genre_in_the_title_points_to_the_playlist_with_that_name():
    track = plain(tr(9, "Desconocido", name="Gasolina - Salsa Version"))

    best = suggest(track, {}, NAMES)[0]

    assert best.playlist_id == "SAL" and "Salsa" in best.reason


def test_several_artists_each_split_one_point():
    index = build_artist_index({"SAL": [tr(1, "A")], "REG": [tr(2, "B")]})
    track = {"uri": "u", "name": "Duo", "artists": [{"id": "id-A", "name": "A"}, {"id": "id-B", "name": "B"}]}

    scores = {s.playlist_id: s.score for s in suggest(track, index, NAMES)}

    assert scores == {"SAL": 1.0, "REG": 1.0}


# ---------- genre in title (moved to genres.py) ----------

def test_detect_genre_from_title():
    assert detect_genre_from_title("Gasolina - Salsa Version") == "Salsa"
    assert detect_genre_from_title("Versión Bachata") == "Bachata"
    assert detect_genre_from_title("Gasolina") is None
    assert detect_genre_from_title("") is None
