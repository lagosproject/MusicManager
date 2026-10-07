from fakes import make_client, pid, uri
from music_manager.core import spotify_client
from music_manager.core.job_manager import JobManager
from music_manager.core.models import MergeJob
from test_app_merges import open_run_page, real_tree_client, write_real_tree

LEAF, MID, ROOT = pid("A"), pid("B"), pid("C")


def manager_and_client(tmp_path):
    m = JobManager(config_path=str(tmp_path / "merges.json"))
    m.add_job(MergeJob(name="Raíz", target_id=ROOT, source_ids=[MID]))
    m.add_job(MergeJob(name="Intermedia", target_id=MID, source_ids=[LEAF]))
    return m, make_client({LEAF: [uri(1), uri(2)], MID: [uri(1)], ROOT: []})


def test_with_the_saved_list_at_hand_no_request_is_made_to_check_it():
    client = make_client({})

    unsaved = client.filter_unsaved([uri(1), uri(2), uri(3)], saved_uris={uri(2)})

    assert unsaved == [uri(1), uri(3)]
    assert client.sp.contains_batches == [] and client.sp.saved_page_reads == 0


def test_a_big_batch_is_compared_against_the_saved_list_instead_of_asked_40_at_a_time(monkeypatch):
    monkeypatch.setattr(spotify_client, "FULL_SAVED_READ_THRESHOLD", 5)
    client = make_client({})
    client.sp.saved = {uri(i) for i in range(0, 10, 2)}

    unsaved = client.filter_unsaved([uri(i) for i in range(10)])

    assert unsaved == [uri(i) for i in range(1, 10, 2)]
    assert client.sp.contains_batches == [] and client.sp.saved_page_reads >= 1


def test_a_small_batch_is_asked_directly(monkeypatch):
    client = make_client({})
    client.sp.saved = {uri(1)}

    assert client.filter_unsaved([uri(1), uri(2)]) == [uri(2)]
    assert client.sp.contains_batches == [2] and client.sp.saved_page_reads == 0


def test_a_preview_with_recent_data_reads_no_playlist_and_gives_the_same_answer(tmp_path):
    manager, client = manager_and_client(tmp_path)
    live = manager.preview_tree(client, saved_uris=set())
    seed = {k: v for k, v in live.read.items()}
    client.sp.read_calls.clear()

    reused = manager.preview_tree(client, saved_uris=set(), seed=seed)

    assert client.sp.read_calls == []
    assert [(j.name, [t["uri"] for t in j.to_add]) for j in reused.jobs] == \
           [(j.name, [t["uri"] for t in j.to_add]) for j in live.jobs]


def test_what_a_preview_reads_is_returned_as_spotify_has_it_not_as_simulated(tmp_path):
    manager, client = manager_and_client(tmp_path)

    preview = manager.preview_tree(client, sync_saved=False)

    assert [t["uri"] for t in preview.read[MID]] == [uri(1)]   # not the merged result
    assert preview.read[ROOT] == []


def test_the_second_preview_in_the_app_does_not_read_the_playlists_again_but_rereading_does(new_app, data_dir):
    write_real_tree(data_dir)
    client = real_tree_client()
    at = open_run_page(new_app, client)

    at.button(key="preview_Sync Family Friendly").click().run()
    reads_after_first = len(client.sp.read_calls)
    assert reads_after_first > 0

    at.button(key="preview_Sync Family Friendly").click().run()
    assert len(client.sp.read_calls) == reads_after_first          # reused

    at.button(key="preview_reread").click().run()
    assert len(client.sp.read_calls) > reads_after_first           # asked for fresh data
