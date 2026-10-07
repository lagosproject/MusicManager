import pytest

from fakes import make_client, pid, uri
from music_manager.core.job_manager import JobManager
from music_manager.core.models import MergeJob

LEAF_1, LEAF_2, MID, OTHER, ROOT = (pid(c) for c in "ABCDE")


@pytest.fixture
def manager(tmp_path):
    m = JobManager(config_path=str(tmp_path / "merges.json"))
    # Listed root-first on purpose: the order must not depend on how they were saved
    m.add_job(MergeJob(name="Raíz", target_id=ROOT, source_ids=[MID, OTHER]))
    m.add_job(MergeJob(name="Intermedia", target_id=MID, source_ids=[LEAF_1, LEAF_2]))
    return m


@pytest.fixture
def client():
    return make_client({
        LEAF_1: [uri(1), uri(2)],
        LEAF_2: [uri(3)],
        MID: [],
        OTHER: [uri(9)],
        ROOT: [],
    })


def contents(client, playlist_id):
    return client.sp.playlists[playlist_id]


def test_running_a_leaf_merge_propagates_to_the_root(manager, client):
    results = manager.run_with_propagation("Intermedia", client, sync_saved=False)

    assert [(r.name, r.added, r.status) for r in results] == [("Intermedia", 3, "ok"), ("Raíz", 4, "ok")]
    assert contents(client, MID) == [uri(1), uri(2), uri(3)]
    assert sorted(contents(client, ROOT)) == sorted([uri(1), uri(2), uri(3), uri(9)])


def test_a_new_track_in_a_leaf_reaches_the_root_on_the_next_run(manager, client):
    manager.run_with_propagation("Intermedia", client, sync_saved=False)
    client.sp.playlists[LEAF_1].append(uri(7))

    results = manager.run_with_propagation("Intermedia", client, sync_saved=False)

    assert [(r.name, r.added) for r in results] == [("Intermedia", 1), ("Raíz", 1)]
    assert uri(7) in contents(client, MID) and uri(7) in contents(client, ROOT)


def test_running_again_adds_nothing(manager, client):
    manager.run_with_propagation("Intermedia", client, sync_saved=False)
    client.sp.add_calls.clear()

    results = manager.run_with_propagation("Intermedia", client, sync_saved=False)

    assert [r.added for r in results] == [0, 0]
    assert client.sp.add_calls == []


def test_running_the_root_does_not_touch_the_children(manager, client):
    results = manager.run_with_propagation("Raíz", client, sync_saved=False)

    assert [r.name for r in results] == ["Raíz"]
    assert contents(client, MID) == []
    assert contents(client, ROOT) == [uri(9)]  # only what its direct sources hold today


def test_whole_tree_runs_children_first_even_if_saved_last(manager, client):
    results = manager.run_tree_intelligent(client, sync_saved=False)

    assert [r.name for r in results] == ["Intermedia", "Raíz"]
    assert len(contents(client, ROOT)) == 4


def test_failure_skips_the_merges_above_but_not_unrelated_ones(manager, client):
    manager.add_job(MergeJob(name="Aparte", target_id=pid("F"), source_ids=[OTHER]))
    client.sp.playlists[pid("F")] = []
    client.sp.fail_writes.add(MID)

    results = {r.name: r for r in manager.run_tree_intelligent(client, sync_saved=False)}

    assert results["Intermedia"].status == "error" and "403" in results["Intermedia"].detail
    assert results["Raíz"].status == "skipped"
    assert results["Aparte"].status == "ok" and results["Aparte"].added == 1
    assert contents(client, ROOT) == []


def test_each_playlist_is_read_once_per_run(manager, client):
    manager.run_tree_intelligent(client, sync_saved=False)

    reads = client.sp.read_calls
    assert sorted(reads) == sorted(set(reads))  # no playlist read twice (the chain reuses what it just wrote)


def test_local_files_are_not_added(manager, client):
    client.sp.playlists[LEAF_1].append("spotify:local:artist:album:song:123")

    results = manager.run_with_propagation("Intermedia", client, sync_saved=False)

    assert results[0].added == 3
    assert all(not u.startswith("spotify:local:") for u in contents(client, MID))


def test_tracks_in_several_sources_are_added_once(manager, client):
    client.sp.playlists[LEAF_2].append(uri(1))

    manager.run_with_propagation("Intermedia", client, sync_saved=False)

    assert contents(client, MID).count(uri(1)) == 1


def test_unknown_job(manager, client):
    results = manager.run_with_propagation("No existe", client, sync_saved=False)

    assert results[0].status == "error"


def test_large_merge_is_sent_in_batches_of_100(tmp_path):
    client = make_client({LEAF_1: [uri(i) for i in range(250)], MID: []})
    m = JobManager(config_path=str(tmp_path / "merges.json"))
    m.add_job(MergeJob(name="Grande", target_id=MID, source_ids=[LEAF_1]))

    m.run_with_propagation("Grande", client, sync_saved=False)

    assert [len(uris) for _, uris in client.sp.add_calls] == [100, 100, 50]
