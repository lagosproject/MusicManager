import pytest

from fakes import make_client, pid, uri
from music_manager.core.job_manager import SAVED_LABEL, JobManager
from music_manager.core.models import MergeJob

LEAF, MID, ROOT = pid("A"), pid("B"), pid("C")


@pytest.fixture
def manager(tmp_path):
    m = JobManager(config_path=str(tmp_path / "merges.json"))
    m.add_job(MergeJob(name="Raíz", target_id=ROOT, source_ids=[MID]))
    m.add_job(MergeJob(name="Intermedia", target_id=MID, source_ids=[LEAF]))
    return m


def saved_row(results):
    return next(r for r in results if r.name == SAVED_LABEL)


def test_tracks_missing_from_saved_are_saved_after_the_merges(manager):
    client = make_client({LEAF: [uri(1), uri(2), uri(3)], MID: [], ROOT: []})
    client.sp.saved = {uri(2)}

    results = manager.run_with_propagation("Intermedia", client)

    assert saved_row(results).added == 2 and saved_row(results).status == "ok"
    assert client.sp.saved == {uri(1), uri(2), uri(3)}


def test_already_saved_tracks_are_not_sent_again(manager):
    client = make_client({LEAF: [uri(1), uri(2)], MID: [], ROOT: []})
    client.sp.saved = {uri(1), uri(2)}

    results = manager.run_with_propagation("Intermedia", client)

    assert saved_row(results).added == 0
    assert client.sp.saved_add_batches == []


def test_requests_never_exceed_the_40_uri_limit(manager):
    client = make_client({LEAF: [uri(i) for i in range(100)], MID: [], ROOT: []})

    results = manager.run_with_propagation("Intermedia", client)

    assert saved_row(results).added == 100
    assert [len(b) for b in client.sp.saved_add_batches] == [40, 40, 20]
    assert max(client.sp.contains_batches) <= 40


def test_it_covers_tracks_of_every_playlist_in_the_run_not_only_the_targets(manager):
    # uri(7) lives only in the leaf and the merges copy it up; uri(8) is already in the root
    client = make_client({LEAF: [uri(7)], MID: [], ROOT: [uri(8)]})

    manager.run_with_propagation("Intermedia", client)

    assert {uri(7), uri(8)} <= client.sp.saved


def test_local_files_and_episodes_are_never_saved(manager):
    client = make_client({LEAF: [uri(1), "spotify:local:a:b:c:1", "spotify:episode:xyz"], MID: [], ROOT: []})

    manager.run_with_propagation("Intermedia", client)

    assert client.sp.saved == {uri(1)}


def test_sync_can_be_turned_off(manager):
    client = make_client({LEAF: [uri(1)], MID: [], ROOT: []})

    results = manager.run_with_propagation("Intermedia", client, sync_saved=False)

    assert all(r.name != SAVED_LABEL for r in results)
    assert client.sp.saved == set()


def test_a_failure_saving_is_reported_but_the_merges_still_count(manager):
    client = make_client({LEAF: [uri(1)], MID: [], ROOT: []})
    client.sp.fail_saving = True

    results = manager.run_with_propagation("Intermedia", client)

    assert [r.status for r in results if r.name != SAVED_LABEL] == ["ok", "ok"]
    assert saved_row(results).status == "error" and "403" in saved_row(results).detail
    assert client.sp.playlists[ROOT] == [uri(1)]


def test_no_sync_when_every_merge_failed(manager):
    client = make_client({LEAF: [uri(1)], MID: [], ROOT: []})
    client.sp.fail_writes.update({MID})

    results = manager.run_with_propagation("Intermedia", client)

    assert all(r.name != SAVED_LABEL for r in results)
