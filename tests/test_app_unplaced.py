import json

from fakes import make_client, pid, uri
from music_manager.core.merge_tree import all_leaf_playlists, tree_playlist_ids
from music_manager.core.models import MergeJob
from music_manager.core.organization import find_unplaced, group_by_destination

MACRO, FAMILY, LEAF_A, LEAF_B, OTHER = (pid(c) for c in "MFABO")
NAME = {LEAF_A: "Lista AAAA", LEAF_B: "Lista BBBB", OTHER: "Lista OOOO"}


def artist(name):
    return [{"name": name}]


def build_client():
    """Saved: 1..4. 1 is in a leaf, 2 only in the root. 3 (artist Celia) and 4 (unknown) are in no playlist."""
    client = make_client({MACRO: [uri(2)], FAMILY: [uri(1)], LEAF_A: [uri(1), uri(10), uri(11)], LEAF_B: [], OTHER: []})
    client.sp.saved = {uri(1), uri(2), uri(3), uri(4)}
    client.sp.track_info = {
        uri(1): {"uri": uri(1), "name": "Uno", "artists": artist("Celia")},
        uri(2): {"uri": uri(2), "name": "Dos", "artists": artist("Alguien")},
        uri(3): {"uri": uri(3), "name": "Tres", "artists": artist("Celia")},
        uri(4): {"uri": uri(4), "name": "Cuatro", "artists": artist("Nadie")},
        uri(10): {"uri": uri(10), "name": "Diez", "artists": artist("Celia")},
        uri(11): {"uri": uri(11), "name": "Once", "artists": artist("Celia")},
    }
    return client


def write_tree(data_dir):
    jobs = [
        {"name": "Macro", "target_id": MACRO, "source_ids": [FAMILY, OTHER], "description": ""},
        {"name": "Family", "target_id": FAMILY, "source_ids": [LEAF_A, LEAF_B], "description": ""},
    ]
    (data_dir / "merges.json").write_text(json.dumps(jobs), encoding="utf-8")


def open_page(new_app, client):
    at = new_app()
    at.session_state["spotify"] = client
    at.run()
    at.sidebar.selectbox[0].set_value("Guardadas sin playlist").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def pick(uri_, confident=True):
    return f"unplaced_{confident}_{uri_}"


# ---------- pure logic ----------

def test_a_saved_track_counts_as_placed_if_it_is_in_any_playlist_of_the_tree():
    def item(n):
        return {"item": {"uri": uri(n), "name": str(n)}}

    saved = [{"track": {"uri": uri(1)}}, {"track": {"uri": uri(2)}}, {"track": {"uri": uri(3)}, "added_at": "2026-05-01T10:00:00Z"},
             {"track": {"uri": "spotify:local:a:b:c:1"}}, {"track": {"uri": uri(3)}}]

    unplaced = find_unplaced(saved, [[item(1)], [item(2)]])

    assert [t["uri"] for t in unplaced] == [uri(3)]            # local file skipped, repeated track listed once
    assert unplaced[0]["liked_at"] == "2026-05-01T10:00:00Z"


def test_tree_playlists_and_leaves():
    jobs = [MergeJob(name="Macro", target_id=MACRO, source_ids=[FAMILY, OTHER]),
            MergeJob(name="Family", target_id=FAMILY, source_ids=[LEAF_A, LEAF_B])]

    assert tree_playlist_ids(jobs) == [MACRO, FAMILY, OTHER, LEAF_A, LEAF_B]
    assert all_leaf_playlists(jobs) == [OTHER, LEAF_A, LEAF_B]  # FAMILY is a target, so it is not a leaf


def test_group_by_destination():
    assert group_by_destination({uri(1): LEAF_A, uri(2): LEAF_B, uri(3): LEAF_A}) == {LEAF_A: [uri(1), uri(3)], LEAF_B: [uri(2)]}


# ---------- the page ----------

def test_only_saved_tracks_missing_from_the_whole_tree_are_listed(new_app, data_dir):
    write_tree(data_dir)

    at = open_page(new_app, build_client())

    assert any("2 de tus 4 canciones guardadas" in c.value for c in at.caption)  # 3 and 4


def test_a_sure_suggestion_is_preselected_and_an_unknown_artist_is_not(new_app, data_dir):
    write_tree(data_dir)

    at = open_page(new_app, build_client())

    assert at.selectbox(key=pick(uri(3))).value == LEAF_A      # Celia's other songs are all in that playlist
    assert at.selectbox(key=pick(uri(4))).value is None
    assert any("Celia: 3 canciones ahí" in c.value for c in at.caption)


def test_nothing_is_written_until_the_user_confirms(new_app, data_dir):
    write_tree(data_dir)
    client = build_client()
    at = open_page(new_app, client)

    next(b for b in at.button if b.label == "Colocar 1 canciones").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert client.sp.add_calls == []
    assert any("Se añadirán **1** canciones" in w.value for w in at.warning)


def test_confirming_places_the_tracks_and_they_leave_the_list(new_app, data_dir):
    write_tree(data_dir)
    client = build_client()
    at = open_page(new_app, client)
    at.selectbox(key=pick(uri(4))).set_value(LEAF_B).run()            # also place the unknown one, elsewhere
    next(b for b in at.button if b.label == "Colocar 2 canciones").click().run()

    at.button(key="unplaced_confirm").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert uri(3) in client.sp.playlists[LEAF_A] and uri(4) in client.sp.playlists[LEAF_B]
    assert len(client.sp.add_calls) == 2                               # one request per destination
    assert any("Colocadas 2 canciones" in s.value for s in at.success)
    assert any("Todas tus canciones guardadas" in s.value for s in at.success)


def test_cancelling_writes_nothing(new_app, data_dir):
    write_tree(data_dir)
    client = build_client()
    at = open_page(new_app, client)
    next(b for b in at.button if b.label == "Colocar 1 canciones").click().run()

    at.button(key="unplaced_cancel").click().run()

    assert client.sp.add_calls == []
    assert not any(b.key == "unplaced_confirm" for b in at.button)


def test_a_spotify_error_is_shown_and_the_track_stays_in_the_list(new_app, data_dir):
    write_tree(data_dir)
    client = build_client()
    client.sp.fail_writes.add(LEAF_A)
    at = open_page(new_app, client)
    next(b for b in at.button if b.label == "Colocar 1 canciones").click().run()

    at.button(key="unplaced_confirm").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("403" in e.value for e in at.error)
    assert any("2 de tus 4 canciones guardadas" in c.value for c in at.caption)


def test_the_search_filters_the_list(new_app, data_dir):
    write_tree(data_dir)
    at = open_page(new_app, build_client())

    at.text_input(key="unplaced_search").set_value("cuatro").run()

    assert not at.exception, [e.value for e in at.exception]
    keys = [s.key for s in at.selectbox if s.key and s.key.startswith("unplaced_True_")]
    assert keys == [pick(uri(4))]
