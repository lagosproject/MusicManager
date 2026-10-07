import json

from fakes import make_client, uri

MACRO = "2GHIEBMJKaUqkoDVOIxFao"
FAMILY = "5i8jCq2ISdWXwgXBVb5Nys"
OTHER = "3xf4p0pKyfZ0cOpRevLGC0"
LEAF_A = "3HD2idzM5B9mlHI64o7XMn"
LEAF_B = "05OTaAnmlHWcj6Qjc5aaIo"
NEW_A = "1" * 22
NEW_B = "2" * 22


def write_real_tree(data_dir):
    jobs = [
        {"name": "Sync Macro", "target_id": f"http://open.spotify.com/playlist/{MACRO}",
         "source_ids": [f"https://open.spotify.com/playlist/{FAMILY}", f"https://open.spotify.com/playlist/{OTHER}"],
         "description": "La que tiene todo"},
        {"name": "Sync Family Friendly", "target_id": f"https://open.spotify.com/playlist/{FAMILY}",
         "source_ids": [f"https://open.spotify.com/playlist/{LEAF_A}", f"https://open.spotify.com/playlist/{LEAF_B}"],
         "description": "Sync No Hard"},
    ]
    (data_dir / "merges.json").write_text(json.dumps(jobs), encoding="utf-8")


def open_merges_page(new_app):
    at = new_app().run()
    at.sidebar.selectbox[0].set_value("Gestión de Merges").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def submit(at, name, target, sources):
    at.text_input[0].set_value(name)
    at.text_input[1].set_value(target)
    at.text_area[0].set_value(sources)
    next(b for b in at.button if b.label == "Guardar merge").click().run()
    return at


def test_tree_shows_both_merges_nested(new_app, data_dir):
    write_real_tree(data_dir)
    at = open_merges_page(new_app)
    tree = next(m.value for m in at.markdown if "Sync Macro" in m.value and "Sync Family Friendly" in m.value)
    lines = tree.split("\n")
    assert lines[0].startswith("- **Sync Macro**")
    assert lines[1].startswith("  - **Sync Family Friendly**")  # nested under its parent


def test_rejects_unrecognised_playlist(new_app):
    at = submit(open_merges_page(new_app), "Nuevo", "no-es-una-playlist", NEW_A)
    assert any("No reconozco" in e.value for e in at.error)


def test_rejects_duplicate_name(new_app, data_dir):
    write_real_tree(data_dir)
    at = submit(open_merges_page(new_app), "Sync Macro", NEW_A, NEW_B)
    assert any("Ya existe" in e.value for e in at.error)


def test_rejects_target_that_is_also_a_source(new_app):
    at = submit(open_merges_page(new_app), "Nuevo", NEW_A, f"{NEW_A}\n{NEW_B}")
    assert any("destino no puede ser" in e.value for e in at.error)


def test_rejects_a_cycle(new_app, data_dir):
    write_real_tree(data_dir)
    # Macro already consumes Family; making Family consume Macro closes the loop
    at = submit(open_merges_page(new_app), "Bucle", LEAF_A, MACRO)
    assert any("ciclo" in e.value for e in at.error)


def test_saves_a_valid_merge(new_app, data_dir):
    at = submit(open_merges_page(new_app), "Nuevo", NEW_A, NEW_B)
    assert not at.exception, [e.value for e in at.exception]
    saved = json.loads((data_dir / "merges.json").read_text(encoding="utf-8"))
    assert [j["name"] for j in saved] == ["Nuevo"]
    assert saved[0]["source_ids"] == [NEW_B]


def open_run_page(new_app, client):
    at = new_app()
    at.session_state["spotify"] = client
    at.run()
    at.sidebar.selectbox[0].set_value("Ejecución de Merges").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def real_tree_client():
    return make_client({LEAF_A: [uri(1)], LEAF_B: [uri(2)], FAMILY: [], OTHER: [uri(9)], MACRO: []})


def test_running_a_leaf_merge_from_the_ui_also_updates_the_root(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    at = open_run_page(new_app, client)

    at.button(key="run_Sync Family Friendly").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert sorted(client.sp.playlists[FAMILY]) == [uri(1), uri(2)]
    assert sorted(client.sp.playlists[MACRO]) == sorted([uri(1), uri(2), uri(9)])
    assert at.success and not at.error


def test_running_the_whole_tree_from_the_ui(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    at = open_run_page(new_app, client)

    next(b for b in at.button if b.label == "Ejecutar todo el árbol").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert len(client.sp.playlists[MACRO]) == 3
    assert at.success


def test_running_from_the_ui_saves_missing_tracks_to_liked_songs(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    at = open_run_page(new_app, client)

    at.button(key="run_Sync Family Friendly").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert client.sp.saved == {uri(1), uri(2), uri(9)}


def test_the_liked_songs_switch_can_be_turned_off(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    at = open_run_page(new_app, client)

    at.toggle(key="sync_saved").set_value(False).run()
    at.button(key="run_Sync Family Friendly").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert client.sp.saved == set()
    assert len(client.sp.playlists[MACRO]) == 3  # the merges themselves still ran


def test_a_failed_merge_is_reported_and_stops_the_ones_above(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    client.sp.fail_writes.add(FAMILY)
    at = open_run_page(new_app, client)

    at.button(key="run_Sync Family Friendly").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert at.error
    assert client.sp.playlists[MACRO] == []


def test_empty_fields_are_rejected(new_app):
    at = submit(open_merges_page(new_app), "", "", "")
    assert any("obligatorios" in e.value for e in at.error)
