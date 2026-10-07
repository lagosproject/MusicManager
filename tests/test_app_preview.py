from fakes import uri
from test_app_merges import FAMILY, MACRO, LEAF_A, LEAF_B, OTHER, open_run_page, real_tree_client, write_real_tree


def snapshot(client):
    return ({k: list(v) for k, v in client.sp.playlists.items()}, set(client.sp.saved))


def preview_of_leaf_merge(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    at = open_run_page(new_app, client)
    at.button(key="preview_Sync Family Friendly").click().run()
    return at, client


def test_previewing_writes_nothing(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    at = open_run_page(new_app, client)
    before = snapshot(client)

    at.button(key="preview_Sync Family Friendly").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert snapshot(client) == before
    assert client.sp.add_calls == [] and client.sp.saved_add_batches == []


def test_the_preview_shows_each_merge_and_what_would_be_saved(new_app, data_dir):
    at, client = preview_of_leaf_merge(new_app, data_dir)

    assert any("Vista previa" in s.value for s in at.subheader)
    assert any("«Sync Family Friendly» y los merges que dependen de él" in s.value for s in at.subheader)
    assert any("se guardarían **3**" in m.value for m in at.markdown)  # uri 1, 2 and 9 are not liked yet
    assert len(at.dataframe) >= 1


def test_the_whole_tree_can_be_previewed(new_app, data_dir):
    write_real_tree(data_dir)
    at = open_run_page(new_app, real_tree_client())

    at.button(key="preview_tree").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("todo el árbol" in s.value for s in at.subheader)


def test_running_from_the_preview_does_what_it_showed(new_app, data_dir):
    at, client = preview_of_leaf_merge(new_app, data_dir)

    at.button(key="preview_run").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert sorted(client.sp.playlists[FAMILY]) == [uri(1), uri(2)]
    assert sorted(client.sp.playlists[MACRO]) == sorted([uri(1), uri(2), uri(9)])
    assert client.sp.saved == {uri(1), uri(2), uri(9)}
    assert at.success
    assert not any("Vista previa" in s.value for s in at.subheader)  # the preview is out of date now


def test_discarding_removes_the_preview_and_writes_nothing(new_app, data_dir):
    at, client = preview_of_leaf_merge(new_app, data_dir)
    before = snapshot(client)

    at.button(key="preview_discard").click().run()

    assert not any("Vista previa" in s.value for s in at.subheader)
    assert snapshot(client) == before


def test_a_run_started_elsewhere_makes_the_old_preview_disappear(new_app, data_dir):
    at, client = preview_of_leaf_merge(new_app, data_dir)

    at.button(key="run_Sync Macro").click().run()

    assert not any("Vista previa" in s.value for s in at.subheader)


def test_when_everything_is_up_to_date_the_preview_says_so_and_cannot_run(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    at = open_run_page(new_app, client)
    at.button(key="run_Sync Family Friendly").click().run()  # bring everything up to date first

    at.button(key="preview_Sync Family Friendly").click().run()

    assert any("No hay nada que añadir" in s.value for s in at.success)
    assert at.button(key="preview_run").disabled


def test_turning_the_liked_songs_switch_off_is_reflected_and_discards_an_old_preview(new_app, data_dir):
    at, client = preview_of_leaf_merge(new_app, data_dir)

    at.toggle(key="sync_saved").set_value(False).run()

    assert not any("Vista previa" in s.value for s in at.subheader)  # it was calculated with the other setting

    at.button(key="preview_Sync Family Friendly").click().run()
    assert any("no se tocará" in m.value for m in at.markdown)


def test_a_read_error_is_shown_not_a_crash(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    client.sp.fail_reads.add(LEAF_A)
    at = open_run_page(new_app, client)

    at.button(key="preview_Sync Family Friendly").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("404" in e.value for e in at.error)
    assert not any("Vista previa" in s.value for s in at.subheader)
