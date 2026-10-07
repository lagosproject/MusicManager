import json

from streamlit.testing.v1 import AppTest


def visit_every_page(at: AppTest):
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    for option in at.sidebar.selectbox[0].options:
        at.sidebar.selectbox[0].set_value(option).run()
        assert not at.exception, f"{option}: {[e.value for e in at.exception]}"


def test_every_page_renders_with_no_merges_and_no_playlists(new_app):
    visit_every_page(new_app())


def test_every_page_renders_with_a_merge_without_sources(new_app, data_dir):
    (data_dir / "merges.json").write_text(
        json.dumps([{"name": "Vacío", "target_id": "t1", "source_ids": [], "description": ""}]),
        encoding="utf-8",
    )
    visit_every_page(new_app())


def test_corrupt_cache_file_does_not_crash_the_app(new_app, data_dir):
    (data_dir / "tracks_cache.json").write_text("{esto no es json", encoding="utf-8")
    (data_dir / "artist_cache.json").write_text("", encoding="utf-8")
    at = new_app().run()
    assert not at.exception, [e.value for e in at.exception]
