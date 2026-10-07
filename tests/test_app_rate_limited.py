from fakes import uri
from test_app_merges import real_tree_client, write_real_tree


def limited_client():
    client = real_tree_client()
    client.sp.rate_limited = True
    return client


def messages(at):
    return [e.value for e in at.error] + [w.value for w in at.warning]


def test_every_page_opens_without_crashing_while_spotify_limits_the_playlists(new_app, data_dir):
    write_real_tree(data_dir)
    at = new_app()
    at.session_state["spotify"] = limited_client()
    at.run()
    assert not at.exception, [e.value for e in at.exception]

    for option in at.sidebar.selectbox[0].options:
        at.sidebar.selectbox[0].set_value(option).run()
        assert not at.exception, f"{option}: {[e.value for e in at.exception]}"


def test_the_pages_that_need_playlists_say_why_and_for_how_long(new_app, data_dir):
    write_real_tree(data_dir)
    at = new_app()
    at.session_state["spotify"] = limited_client()
    at.run()

    for option in ("Dashboard", "Auditoría de Organización", "Organizador por Géneros", "Auditoría: Duplicados"):
        at.sidebar.selectbox[0].set_value(option).run()
        assert any("limitando" in m and "21,9 horas" in m for m in messages(at)), option


def test_previewing_while_limited_shows_the_reason_and_writes_nothing(new_app, data_dir):
    write_real_tree(data_dir)
    client = limited_client()
    at = new_app()
    at.session_state["spotify"] = client
    at.run()
    at.sidebar.selectbox[0].set_value("Ejecución de Merges").run()

    at.button(key="preview_Sync Family Friendly").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("21,9 horas" in m for m in messages(at))
    assert client.sp.add_calls == []


def test_a_merge_run_while_limited_is_reported_per_merge_not_as_a_crash(new_app, data_dir):
    write_real_tree(data_dir)
    client = limited_client()
    at = new_app()
    at.session_state["spotify"] = client
    at.run()
    at.sidebar.selectbox[0].set_value("Ejecución de Merges").run()

    at.button(key="run_Sync Family Friendly").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("limitando" in m for m in messages(at)) or at.dataframe  # the result table carries the reason
