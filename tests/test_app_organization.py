import json

from fakes import make_client, pid, uri

MACRO, FAMILY, LEAF_A, LEAF_B, OTHER = (pid(c) for c in "MFABO")
NAME = {MACRO: "Lista MMMM", FAMILY: "Lista FFFF", LEAF_A: "Lista AAAA", LEAF_B: "Lista BBBB", OTHER: "Lista OOOO"}


def artist(name):
    return [{"id": f"id-{name}", "name": name}]


def write_tree(data_dir):
    jobs = [
        {"name": "Macro", "target_id": MACRO, "source_ids": [FAMILY, OTHER], "description": ""},
        {"name": "Family", "target_id": FAMILY, "source_ids": [LEAF_A, LEAF_B], "description": ""},
    ]
    (data_dir / "merges.json").write_text(json.dumps(jobs), encoding="utf-8")


def build_client():
    """Macro holds t1..t4. t1 is already in a leaf; t2 and t3 (artist Celia) and t4 (unknown) are not."""
    client = make_client({
        MACRO: [uri(1), uri(2), uri(3), uri(4)],
        FAMILY: [uri(1)],
        LEAF_A: [uri(1), uri(10)],   # Celia has songs here
        LEAF_B: [uri(20)],
        OTHER: [],
    })
    client.sp.track_info = {
        uri(1): {"uri": uri(1), "name": "Uno", "artists": artist("Celia")},
        uri(2): {"uri": uri(2), "name": "Dos", "artists": artist("Celia")},
        uri(3): {"uri": uri(3), "name": "Tres - Salsa Version", "artists": artist("Nadie")},
        uri(4): {"uri": uri(4), "name": "Cuatro", "artists": artist("Nadie")},
        uri(10): {"uri": uri(10), "name": "Diez", "artists": artist("Celia")},
        uri(20): {"uri": uri(20), "name": "Veinte", "artists": artist("Bad Bunny")},
    }
    return client


def open_audit(new_app, client):
    at = new_app()
    at.session_state["spotify"] = client
    at.run()
    at.sidebar.selectbox[0].set_value("Auditoría de Organización").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_lists_only_tracks_missing_from_every_playlist_below(new_app, data_dir):
    write_tree(data_dir)

    at = open_audit(new_app, build_client())

    assert any("Hay 3 canciones sin colocar" in w.value for w in at.warning)  # t2, t3, t4 (t1 is in a leaf)


def test_switching_between_merges_works_for_every_merge(new_app, data_dir):
    write_tree(data_dir)
    at = open_audit(new_app, build_client())

    for name in at.selectbox(key="audit_job").options:
        at.selectbox(key="audit_job").set_value(name).run()
        assert not at.exception, f"{name}: {[e.value for e in at.exception]}"


def test_liked_songs_do_not_count_as_placed(new_app, data_dir):
    write_tree(data_dir)
    client = build_client()
    client.sp.saved = {uri(2), uri(3), uri(4)}  # all liked: they still need a home

    at = open_audit(new_app, client)

    assert any("Hay 3 canciones sin colocar" in w.value for w in at.warning)


def test_destinations_are_the_leaf_playlists_not_the_intermediate_merge(new_app, data_dir):
    write_tree(data_dir)

    at = open_audit(new_app, build_client())

    assert set(at.selectbox(key=f"audit_pick_{uri(2)}").options) == {NAME[LEAF_A], NAME[LEAF_B], NAME[OTHER]}


def test_the_playlist_with_the_same_artist_is_preselected(new_app, data_dir):
    write_tree(data_dir)

    at = open_audit(new_app, build_client())

    assert at.selectbox(key=f"audit_pick_{uri(2)}").value == LEAF_A
    assert any("Celia: 2 canciones ahí" in c.value for c in at.caption)


def test_an_unknown_artist_gets_no_preselection_and_add_is_blocked(new_app, data_dir):
    write_tree(data_dir)

    at = open_audit(new_app, build_client())

    assert at.selectbox(key=f"audit_pick_{uri(4)}").value is None      # unknown artist: nothing suggested
    assert at.button(key=f"audit_add_{uri(4)}").disabled               # cannot add without choosing


def test_adding_places_the_track_in_the_leaf_and_it_leaves_the_list(new_app, data_dir):
    write_tree(data_dir)
    client = build_client()
    at = open_audit(new_app, client)

    at.button(key=f"audit_add_{uri(2)}").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert uri(2) in client.sp.playlists[LEAF_A]
    assert any("Hay 2 canciones sin colocar" in w.value for w in at.warning)


def test_the_user_can_pick_another_destination(new_app, data_dir):
    write_tree(data_dir)
    client = build_client()
    at = open_audit(new_app, client)

    at.selectbox(key=f"audit_pick_{uri(4)}").set_value(LEAF_B).run()
    at.button(key=f"audit_add_{uri(4)}").click().run()

    assert uri(4) in client.sp.playlists[LEAF_B]


def test_removing_takes_the_track_out_of_the_merge_target_only(new_app, data_dir):
    write_tree(data_dir)
    client = build_client()
    at = open_audit(new_app, client)

    at.button(key=f"audit_remove_{uri(2)}").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert uri(2) not in client.sp.playlists[MACRO]
    assert uri(1) in client.sp.playlists[MACRO]  # the others stay
    assert any("Hay 2 canciones sin colocar" in w.value for w in at.warning)


def test_a_spotify_error_is_shown_instead_of_crashing(new_app, data_dir):
    write_tree(data_dir)
    client = build_client()
    client.sp.fail_writes.add(LEAF_A)
    at = open_audit(new_app, client)

    at.button(key=f"audit_add_{uri(2)}").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("403" in e.value for e in at.error)
    assert uri(2) not in client.sp.playlists[LEAF_A]


def test_everything_placed_says_so(new_app, data_dir):
    write_tree(data_dir)
    client = make_client({MACRO: [uri(1)], FAMILY: [uri(1)], LEAF_A: [uri(1)], LEAF_B: [], OTHER: []})

    at = open_audit(new_app, client)

    assert any("Todo está colocado" in s.value for s in at.success)
