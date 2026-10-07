from fakes import make_client, pid, uri
from music_manager.core.duplicates import DedupeResult

MINE, CLEAN, VERSIONS, SOMEONE_ELSES = pid("M"), pid("C"), pid("V"), pid("X")
TITLE_MODE = "Posibles duplicados (mismo artista y título)"


def info(n, name, album, year, ms=192000, artist="Daddy Yankee"):
    return {"uri": uri(n), "name": name, "artists": [{"name": artist}], "duration_ms": ms,
            "album": {"name": album, "release_date": f"{year}-07-13"}}


def build_client():
    client = make_client({
        MINE: [uri(1), uri(2), uri(1), uri(3), uri(1)],            # uri(1) three times
        CLEAN: [uri(4), uri(5)],
        VERSIONS: [uri(10), uri(11), uri(12)],                     # 10 and 11 are two releases of one song
        SOMEONE_ELSES: [uri(6), uri(6)],
    })
    client.sp.foreign = {SOMEONE_ELSES}
    client.sp.track_info = {
        uri(1): info(1, "Rompe", "Barrio Fino", 2004),
        uri(2): info(2, "Dos", "Album Dos", 2010),
        uri(3): info(3, "Tres", "Album Tres", 2011),
        uri(10): info(10, "Gasolina", "Barrio Fino", 2004),
        uri(11): info(11, "Gasolina - Remastered", "Barrio Fino (Edición Especial)", 2005),
        uri(12): info(12, "Otra", "Otro álbum", 2020),
    }
    return client


def open_page(new_app, client, playlist=None, mode=None):
    at = new_app()
    at.session_state["spotify"] = client
    at.run()
    at.sidebar.selectbox[0].set_value("Auditoría: Duplicados").run()
    assert not at.exception, [e.value for e in at.exception]
    if playlist:
        at.selectbox(key="dup_playlist").set_value(playlist).run()
    if mode:
        at.session_state["dup_mode"] = mode
        at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def button(at, label):
    return next(b for b in at.button if b.label == label)


def same_track_radio(playlist, n):
    return f"dup_choice_{playlist}_uri_{uri(n)}"


# ---------- same track ----------

def test_only_playlists_the_user_can_edit_are_offered(new_app):
    at = open_page(new_app, build_client())

    assert set(at.selectbox(key="dup_playlist").options) == {f"Lista {p[:4]}" for p in (MINE, CLEAN, VERSIONS)}


def test_each_repeated_song_is_a_card_with_every_copy_described(new_app):
    at = open_page(new_app, build_client(), MINE)

    assert any("**Rompe** — Daddy Yankee  ·  3 copias" in m.value for m in at.markdown)
    assert any("Barrio Fino (2004) · 3:12" in c.value for c in at.caption)  # album, year and length are visible


def test_exact_duplicates_default_to_removing_the_extra_copies(new_app):
    at = open_page(new_app, build_client(), MINE)

    assert at.radio(key=same_track_radio(MINE, 1)).value == "remove"
    assert button(at, "Quitar 2 copias").disabled is False


def test_choosing_to_do_nothing_leaves_nothing_to_remove(new_app):
    at = open_page(new_app, build_client(), MINE)

    at.radio(key=same_track_radio(MINE, 1)).set_value("none").run()

    assert button(at, "Quitar 0 copias").disabled


def test_nothing_is_removed_until_the_user_confirms_and_the_list_shows_what_goes(new_app):
    client = build_client()
    at = open_page(new_app, client, MINE)

    button(at, "Quitar 2 copias").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert client.sp.remove_calls == []
    assert any("Se quitarán estas **2** copias" in w.value for w in at.warning)
    assert len(at.dataframe) >= 1  # the exact copies that would go


def test_confirming_removes_the_extra_copies_and_reports_it(new_app):
    client = build_client()
    at = open_page(new_app, client, MINE)
    button(at, "Quitar 2 copias").click().run()

    at.button(key="dup_confirm").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert client.sp.playlists[MINE] == [uri(1), uri(2), uri(3)]
    assert any("se han quitado 2 copias" in s.value for s in at.success)


def test_the_date_warning_appears_only_for_exact_duplicates(new_app):
    at = open_page(new_app, build_client(), MINE)
    button(at, "Quitar 2 copias").click().run()
    assert any("fecha de añadido la de hoy" in c.value for c in at.caption)

    at = open_page(new_app, build_client(), VERSIONS, TITLE_MODE)
    at.radio(key=title_radio(VERSIONS)).set_value(uri(11)).run()
    button(at, "Quitar 1 copias").click().run()
    assert not any("fecha de añadido la de hoy" in c.value for c in at.caption)


def test_cancelling_removes_nothing(new_app):
    client = build_client()
    at = open_page(new_app, client, MINE)
    button(at, "Quitar 2 copias").click().run()

    at.button(key="dup_cancel").click().run()

    assert client.sp.playlists[MINE] == [uri(1), uri(2), uri(1), uri(3), uri(1)]
    assert not any(b.key == "dup_confirm" for b in at.button)


def test_changing_a_choice_after_asking_drops_the_pending_confirmation(new_app):
    at = open_page(new_app, build_client(), MINE)
    button(at, "Quitar 2 copias").click().run()

    at.radio(key=same_track_radio(MINE, 1)).set_value("none").run()

    assert not any(b.key == "dup_confirm" for b in at.button)


def test_a_playlist_without_duplicates_says_so(new_app):
    at = open_page(new_app, build_client(), CLEAN)

    assert any("No hay duplicados" in s.value for s in at.success)


# ---------- possible duplicates: choose the version to keep ----------

def title_radio(playlist):
    return f"dup_choice_{playlist}_title_daddy yankee|gasolina"


def test_possible_duplicates_show_each_version_with_its_album_and_year(new_app):
    at = open_page(new_app, build_client(), VERSIONS, TITLE_MODE)

    options = at.radio(key=title_radio(VERSIONS)).options
    assert any("Gasolina · Barrio Fino (2004)" in o for o in options)
    assert any("Gasolina - Remastered · Barrio Fino (Edición Especial) (2005)" in o for o in options)
    assert any("Dejar todas las versiones" in o for o in options)
    assert any("Abrir en Spotify" in c.value for c in at.caption)


def test_possible_duplicates_touch_nothing_by_default(new_app):
    at = open_page(new_app, build_client(), VERSIONS, TITLE_MODE)

    assert at.radio(key=title_radio(VERSIONS)).value == "none"
    assert button(at, "Quitar 0 copias").disabled


def test_the_user_picks_which_version_stays_and_the_other_goes(new_app):
    client = build_client()
    at = open_page(new_app, client, VERSIONS, TITLE_MODE)

    at.radio(key=title_radio(VERSIONS)).set_value(uri(11)).run()  # keep the remaster
    button(at, "Quitar 1 copias").click().run()
    at.button(key="dup_confirm").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert client.sp.playlists[VERSIONS] == [uri(11), uri(12)]


def test_keeping_the_original_removes_the_remaster(new_app):
    client = build_client()
    at = open_page(new_app, client, VERSIONS, TITLE_MODE)

    at.radio(key=title_radio(VERSIONS)).set_value(uri(10)).run()
    button(at, "Quitar 1 copias").click().run()
    at.button(key="dup_confirm").click().run()

    assert client.sp.playlists[VERSIONS] == [uri(10), uri(12)]


# ---------- other ----------

def test_a_cache_without_album_details_is_refreshed_once_without_looping(new_app):
    client = build_client()
    client.sp.track_info = {}  # tracks without album information

    at = open_page(new_app, client, MINE)

    assert not at.exception, [e.value for e in at.exception]


def test_many_duplicates_are_paged(new_app):
    songs = [uri(i) for i in range(100, 130)]
    client = make_client({MINE: songs + songs})
    client.sp.track_info = {u: info(int(u.split(":")[-1]), f"Cancion {u[-3:]}", "Alb", 2000) for u in songs}

    at = open_page(new_app, client, MINE)

    assert any("Mostrando 15 de 30" in c.value for c in at.caption)
    button(at, "Mostrar 15 más").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not any("Mostrando" in c.value for c in at.caption)  # all 30 are shown now


def test_a_result_with_a_restored_track_is_shown_as_a_warning(new_app):
    at = new_app()
    at.session_state["spotify"] = build_client()
    at.session_state["duplicates_result"] = DedupeResult(removed=1, restored=1)
    at.run()

    at.sidebar.selectbox[0].set_value("Auditoría: Duplicados").run()

    assert any("las he vuelto a añadir" in w.value for w in at.warning)
