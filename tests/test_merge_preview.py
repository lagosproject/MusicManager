import pytest

from fakes import make_client, pid, uri
from music_manager.core.job_manager import JobManager
from music_manager.core.models import MergeJob

LEAF_1, LEAF_2, MID, OTHER, ROOT = (pid(c) for c in "ABCDE")


@pytest.fixture
def manager(tmp_path):
    m = JobManager(config_path=str(tmp_path / "merges.json"))
    m.add_job(MergeJob(name="Raíz", target_id=ROOT, source_ids=[MID, OTHER]))
    m.add_job(MergeJob(name="Intermedia", target_id=MID, source_ids=[LEAF_1, LEAF_2]))
    return m


@pytest.fixture
def client():
    c = make_client({LEAF_1: [uri(1), uri(2)], LEAF_2: [uri(3)], MID: [uri(1)], OTHER: [uri(9)], ROOT: []})
    c.sp.saved = {uri(1)}
    return c


def uris(tracks):
    return [t["uri"] for t in tracks]


def test_preview_writes_nothing(manager, client):
    before = {k: list(v) for k, v in client.sp.playlists.items()}
    saved_before = set(client.sp.saved)

    manager.preview_tree(client)

    assert client.sp.playlists == before
    assert client.sp.add_calls == [] and client.sp.saved_add_batches == [] and client.sp.remove_calls == []
    assert client.sp.saved == saved_before


def test_it_lists_what_each_merge_would_add_and_where_it_comes_from(manager, client):
    preview = manager.preview_tree(client)

    by_name = {j.name: j for j in preview.jobs}
    assert uris(by_name["Intermedia"].to_add) == [uri(2), uri(3)]  # uri(1) is already there
    assert [t["from"] for t in by_name["Intermedia"].to_add] == [LEAF_1, LEAF_2]
    assert by_name["Intermedia"].target_id == MID


def test_merges_above_see_what_the_ones_below_would_add(manager, client):
    preview = manager.preview_tree(client)

    root = next(j for j in preview.jobs if j.name == "Raíz")
    assert sorted(uris(root.to_add)) == sorted([uri(1), uri(2), uri(3), uri(9)])
    assert [j.name for j in preview.jobs] == ["Intermedia", "Raíz"]


def test_it_lists_what_would_be_saved_to_liked_songs(manager, client):
    preview = manager.preview_tree(client)

    assert sorted(uris(preview.to_save)) == sorted([uri(2), uri(3), uri(9)])  # uri(1) is already liked


def test_the_switch_off_means_no_liked_songs_in_the_preview(manager, client):
    preview = manager.preview_tree(client, sync_saved=False)

    assert preview.to_save == [] and preview.sync_saved is False
    assert client.sp.contains_batches == []  # nothing was even checked


def test_preview_of_one_merge_includes_the_ones_above_and_remembers_the_scope(manager, client):
    preview = manager.preview_with_propagation("Intermedia", client)

    assert [j.name for j in preview.jobs] == ["Intermedia", "Raíz"] and preview.scope == "Intermedia"
    assert [j.name for j in manager.preview_with_propagation("Raíz", client).jobs] == ["Raíz"]


def test_local_files_are_counted_but_not_listed_as_additions(manager, client):
    client.sp.playlists[LEAF_2].append("spotify:local:a:b:c:1")

    preview = manager.preview_with_propagation("Intermedia", client)

    inter = preview.jobs[0]
    assert "spotify:local:a:b:c:1" not in uris(inter.to_add) and inter.local_skipped == 1


def test_what_the_preview_promises_is_what_the_run_does(manager, client):
    preview = manager.preview_tree(client)

    results = {r.name: r for r in manager.run_tree_intelligent(client)}

    for job in preview.jobs:
        assert results[job.name].added == len(job.to_add), job.name
    assert results["Me gusta"].added == len(preview.to_save)


def test_after_running_the_preview_is_empty(manager, client):
    manager.run_tree_intelligent(client)

    preview = manager.preview_tree(client)

    assert all(not j.to_add for j in preview.jobs) and preview.to_save == []


def test_a_cycle_is_reported_and_left_out(manager, client):
    manager.add_job(MergeJob(name="Bucle", target_id=LEAF_1, source_ids=[ROOT]))

    preview = manager.preview_tree(client)

    # Bucle fills LEAF_1, which feeds Intermedia, which feeds Raíz, which feeds Bucle: all three are stuck
    assert set(preview.cyclic) == {"Bucle", "Intermedia", "Raíz"}
    assert preview.jobs == []  # cyclic merges are reported, not simulated
