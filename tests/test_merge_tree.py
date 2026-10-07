from music_manager.core.merge_tree import (
    consumers,
    creates_cycle,
    execution_order,
    is_valid_playlist_id,
    leaf_playlists,
    normalize_playlist_id,
    propagation_plan,
    shared_targets,
    subtree_playlists,
    tree_lines,
)
from music_manager.core.models import MergeJob

# Same shape as the real merges.json: Sync Macro <- Sync Family Friendly <- two playlists
MACRO = "2GHIEBMJKaUqkoDVOIxFao"
FAMILY = "5i8jCq2ISdWXwgXBVb5Nys"
OTHER = "3xf4p0pKyfZ0cOpRevLGC0"
LEAF_A = "3HD2idzM5B9mlHI64o7XMn"
LEAF_B = "05OTaAnmlHWcj6Qjc5aaIo"


def url(pid: str) -> str:
    return f"https://open.spotify.com/playlist/{pid}"


def real_tree():
    # Written in the "wrong" order on purpose, and with an http:// URL like the real file
    return [
        MergeJob(name="Sync Macro", target_id="http://open.spotify.com/playlist/" + MACRO,
                 source_ids=[url(FAMILY), url(OTHER)]),
        MergeJob(name="Sync Family Friendly", target_id=url(FAMILY),
                 source_ids=[url(LEAF_A), url(LEAF_B)]),
    ]


def names(jobs):
    return [j.name for j in jobs]


def test_normalize_playlist_id_accepts_urls_uris_and_bare_ids():
    assert normalize_playlist_id(url(MACRO) + "?si=abc") == MACRO
    assert normalize_playlist_id("http://open.spotify.com/playlist/" + MACRO) == MACRO
    assert normalize_playlist_id(f"https://open.spotify.com/intl-es/playlist/{MACRO}") == MACRO
    assert normalize_playlist_id(f"spotify:playlist:{MACRO}") == MACRO
    assert normalize_playlist_id(f"  {MACRO}  ") == MACRO


def test_is_valid_playlist_id():
    assert is_valid_playlist_id(url(MACRO))
    assert not is_valid_playlist_id("hola")
    assert not is_valid_playlist_id("")


def test_children_run_before_parents():
    ordered, cyclic = execution_order(real_tree())
    assert names(ordered) == ["Sync Family Friendly", "Sync Macro"]
    assert cyclic == []


def test_order_works_when_target_is_a_uri_and_source_a_url():
    jobs = [
        MergeJob(name="Padre", target_id="spotify:playlist:" + MACRO, source_ids=[url(FAMILY)]),
        MergeJob(name="Hijo", target_id=FAMILY, source_ids=[url(LEAF_A)]),
    ]
    assert names(execution_order(jobs)[0]) == ["Hijo", "Padre"]


def test_cycle_is_reported_not_looped():
    jobs = [
        MergeJob(name="A", target_id=MACRO, source_ids=[FAMILY]),
        MergeJob(name="B", target_id=FAMILY, source_ids=[MACRO]),
    ]
    ordered, cyclic = execution_order(jobs)
    assert ordered == [] and names(cyclic) == ["A", "B"]


def test_creates_cycle():
    jobs = real_tree()
    loop = MergeJob(name="Bucle", target_id=LEAF_A, source_ids=[MACRO])
    assert creates_cycle(jobs, loop)
    harmless = MergeJob(name="Nuevo", target_id=url(OTHER), source_ids=[url(LEAF_B)])
    assert not creates_cycle(jobs, harmless)


def test_consumers_are_the_parents():
    jobs = real_tree()
    assert names(consumers(jobs[1], jobs)) == ["Sync Macro"]
    assert consumers(jobs[0], jobs) == []


def test_running_a_leaf_job_propagates_upwards_in_order():
    assert names(propagation_plan(real_tree(), "Sync Family Friendly")) == ["Sync Family Friendly", "Sync Macro"]


def test_running_the_root_only_runs_itself():
    assert names(propagation_plan(real_tree(), "Sync Macro")) == ["Sync Macro"]


def test_propagation_reaches_grandparents():
    jobs = real_tree() + [MergeJob(name="Hoja", target_id=LEAF_A, source_ids=["1" * 22])]
    assert names(propagation_plan(jobs, "Hoja")) == ["Hoja", "Sync Family Friendly", "Sync Macro"]


def test_propagation_of_unknown_job_is_empty():
    assert propagation_plan(real_tree(), "No existe") == []


def test_subtree_and_leaves_of_the_real_tree():
    jobs = real_tree()
    macro = jobs[0]

    # Below Macro: Family Friendly (a merge target), its two leaves, and the other source
    assert set(subtree_playlists(macro, jobs)) == {FAMILY, LEAF_A, LEAF_B, OTHER}
    # Leaves are the playlists no merge fills: where a song is really placed
    assert leaf_playlists(macro, jobs) == [LEAF_A, LEAF_B, OTHER]  # in the order the tree is read
    assert leaf_playlists(jobs[1], jobs) == [LEAF_A, LEAF_B]


def test_subtree_survives_a_cycle():
    jobs = [
        MergeJob(name="A", target_id=MACRO, source_ids=[FAMILY]),
        MergeJob(name="B", target_id=FAMILY, source_ids=[MACRO]),
    ]
    assert subtree_playlists(jobs[0], jobs) == [FAMILY]
    assert leaf_playlists(jobs[0], jobs) == []


def test_shared_targets():
    jobs = real_tree() + [MergeJob(name="Otro", target_id=url(MACRO), source_ids=[url(LEAF_A)])]
    assert shared_targets(jobs) == [MACRO]
    assert shared_targets(real_tree()) == []


def test_tree_lines_nests_children_under_their_parent():
    label = {MACRO: "Macro", FAMILY: "Family", OTHER: "Otra", LEAF_A: "Hoja A", LEAF_B: "Hoja B"}
    lines = tree_lines(real_tree(), lambda ref: label[normalize_playlist_id(ref)])
    assert lines == [
        "- **Sync Macro** → Macro",
        "  - **Sync Family Friendly** → Family",
        "    - Hoja A",
        "    - Hoja B",
        "  - Otra",
    ]


def test_tree_lines_survives_cycles():
    jobs = [
        MergeJob(name="A", target_id=MACRO, source_ids=[FAMILY]),
        MergeJob(name="B", target_id=FAMILY, source_ids=[MACRO]),
    ]
    assert len(tree_lines(jobs, lambda ref: ref)) >= 2
