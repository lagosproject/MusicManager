from fakes import make_client, pid, uri
from music_manager.core.duplicates import (
    MODE_SAME_TITLE,
    MODE_SAME_TRACK,
    copies_to_remove,
    describe_copy,
    find_duplicate_groups,
    format_duration,
    plan_operations,
    remove_duplicates,
    title_key,
    track_url,
)

PL = pid("P")
NO_WAIT = {"sleep": lambda seconds: None}


def track(n, name=None, artist="Artista", uri_=None, album=None, year=None, added=None, ms=200000):
    t = {"uri": uri_ or uri(n), "name": name or f"Cancion {n}", "artists": [{"name": artist}], "duration_ms": ms}
    if album:
        t["album"] = {"name": album, "release_date": f"{year or 2000}-01-01"}
    item = {"item": t}
    if added:
        item["added_at"] = added
    return item


# ---------- grouping ----------

def test_same_track_groups_report_every_position():
    items = [track(1), track(2), track(1), track(3), track(1), track(2)]

    groups = {g.key: g for g in find_duplicate_groups(items)}

    assert groups[uri(1)].positions == [0, 2, 4] and groups[uri(1)].extras == 2
    assert groups[uri(2)].positions == [1, 5]
    assert uri(3) not in groups


def test_a_group_keeps_the_details_of_each_copy():
    items = [track(1, album="Original", year=2004, added="2023-01-05T10:00:00Z"),
             track(1, album="Original", year=2004, added="2024-06-01T10:00:00Z")]

    group = find_duplicate_groups(items)[0]

    assert [t["album"]["name"] for t in group.tracks] == ["Original", "Original"]
    assert group.added == ["2023-01-05T10:00:00Z", "2024-06-01T10:00:00Z"]


def test_unavailable_entries_and_local_files_are_ignored_but_still_count_as_positions():
    items = [{"item": None}, track(1), {"item": None}, track(1), track(7, uri_="spotify:local:a:b:c:1"),
             track(8, uri_="spotify:local:a:b:c:1")]

    groups = find_duplicate_groups(items)

    assert [(g.key, g.positions) for g in groups] == [(uri(1), [1, 3])]


def test_title_key_ignores_case_accents_and_version_tags():
    base = {"name": "Sálvame", "artists": [{"name": "Rauw Alejandro"}]}
    key = title_key(base)
    for name in ("SALVAME", "Sálvame - Remastered 2011", "Sálvame (Radio Edit)", "Salvame [Explicit]",
                 "Sálvame (feat. Alguien)"):
        assert title_key({**base, "name": name}) == key, name


def test_title_key_keeps_remixes_live_and_other_artists_apart():
    base = {"name": "Gasolina", "artists": [{"name": "Daddy Yankee"}]}
    key = title_key(base)
    assert title_key({**base, "name": "Gasolina - Remix"}) != key
    assert title_key({**base, "name": "Gasolina (Live)"}) != key
    assert title_key({**base, "artists": [{"name": "Otro"}]}) != key
    assert title_key({"name": "Sin artista", "artists": []}) == ""


def test_same_title_mode_finds_different_releases_of_a_song():
    items = [track(1, "Gasolina", "Daddy Yankee"), track(2, "Gasolina - Remastered", "Daddy Yankee"),
             track(3, "Gasolina - Remix", "Daddy Yankee")]

    assert find_duplicate_groups(items, MODE_SAME_TRACK) == []
    groups = find_duplicate_groups(items, MODE_SAME_TITLE)
    assert len(groups) == 1 and groups[0].uris == [uri(1), uri(2)] and groups[0].distinct_uris == [uri(1), uri(2)]


# ---------- planning: Spotify can only remove a track by URI, every copy ----------

def test_an_exact_duplicate_is_collapsed_not_removed():
    groups = find_duplicate_groups([track(1), track(2), track(1), track(2), track(1)])

    ops = plan_operations(groups, {uri(1): uri(1), uri(2): uri(2)})

    assert ops.collapse == [uri(1), uri(2)] and ops.remove_entirely == []


def test_only_groups_with_a_choice_are_planned():
    groups = find_duplicate_groups([track(1), track(1), track(2), track(2)])

    assert plan_operations(groups, {uri(2): uri(2)}).collapse == [uri(2)]
    assert plan_operations(groups, {}).collapse == []


def test_the_versions_not_chosen_are_removed_entirely_and_the_chosen_one_is_left_alone():
    items = [track(1, "Gasolina", "Daddy Yankee"), track(2, "Gasolina - Remastered", "Daddy Yankee")]
    group = find_duplicate_groups(items, MODE_SAME_TITLE)[0]

    keep_second = plan_operations([group], {group.key: uri(2)})
    keep_first = plan_operations([group], {group.key: uri(1)})

    assert keep_second.remove_entirely == [uri(1)] and keep_second.collapse == []  # nothing is re-added: no date lost
    assert keep_first.remove_entirely == [uri(2)] and keep_first.collapse == []


def test_a_chosen_version_that_itself_appears_twice_is_also_collapsed():
    items = [track(1, "Gasolina", "Daddy Yankee"), track(2, "Gasolina - Remastered", "Daddy Yankee"),
             track(1, "Gasolina", "Daddy Yankee")]
    group = find_duplicate_groups(items, MODE_SAME_TITLE)[0]

    ops = plan_operations([group], {group.key: uri(1)})

    assert ops.remove_entirely == [uri(2)] and ops.collapse == [uri(1)]


def test_a_choice_that_is_not_in_the_group_is_ignored():
    group = find_duplicate_groups([track(1), track(1)])[0]

    ops = plan_operations([group], {group.key: uri(99)})

    assert ops.collapse == [] and ops.remove_entirely == []


def test_copies_to_remove_lists_what_the_user_will_lose():
    items = [track(1, "Gasolina", "Daddy Yankee", album="Barrio Fino", year=2004),
             track(2, "Gasolina - Remastered", "Daddy Yankee", album="Barrio Fino Edición", year=2005),
             track(1, "Gasolina", "Daddy Yankee", album="Barrio Fino", year=2004)]
    group = find_duplicate_groups(items, MODE_SAME_TITLE)[0]

    removed = copies_to_remove(group, uri(2))

    assert [t["uri"] for t, _ in removed] == [uri(1), uri(1)]
    assert copies_to_remove(group, uri(99)) == []


# ---------- how a copy is described ----------

def test_describe_copy_tells_versions_apart():
    t = {"album": {"name": "Barrio Fino", "release_date": "2004-07-13"}, "duration_ms": 192000, "explicit": True}

    assert describe_copy(t, "2024-03-12T21:00:00Z") == "Barrio Fino (2004) · 3:12 · explícita · añadida el 12/03/2024"
    assert describe_copy({}, "") == "álbum desconocido"


def test_format_duration_and_url():
    assert format_duration(61000) == "1:01" and format_duration(0) == "" and format_duration(None) == ""
    assert track_url({"id": "abc"}) == "https://open.spotify.com/track/abc"
    assert track_url({"uri": "spotify:track:xyz"}) == "https://open.spotify.com/track/xyz"


# ---------- doing it on the (fake) API ----------

def client_with(uris):
    return make_client({PL: list(uris)})


def run(client, mode, keep, **kwargs):
    return remove_duplicates(client, PL, mode, keep, **NO_WAIT, **kwargs)


def test_an_exact_duplicate_ends_up_once_in_the_position_of_its_first_copy():
    client = client_with([uri(1), uri(2), uri(1), uri(3), uri(2), uri(1)])

    result = run(client, MODE_SAME_TRACK, {uri(1): uri(1), uri(2): uri(2)})

    assert client.sp.playlists[PL] == [uri(1), uri(2), uri(3)]
    assert (result.removed, result.restored, result.error, result.lost) == (3, 0, None, [])


def test_a_track_in_the_middle_keeps_its_place():
    client = client_with([uri(5), uri(1), uri(1), uri(6), uri(7)])

    run(client, MODE_SAME_TRACK, {uri(1): uri(1)})

    assert client.sp.playlists[PL] == [uri(5), uri(1), uri(6), uri(7)]


def test_only_groups_with_a_choice_are_touched():
    client = client_with([uri(1), uri(1), uri(2), uri(2)])

    run(client, MODE_SAME_TRACK, {uri(2): uri(2)})

    assert client.sp.playlists[PL] == [uri(1), uri(1), uri(2)]


def test_positions_are_right_when_unavailable_entries_come_first():
    client = client_with([None, uri(1), None, uri(1), uri(2)])

    result = run(client, MODE_SAME_TRACK, {uri(1): uri(1)})

    assert client.sp.playlists[PL] == [None, uri(1), None, uri(2)]
    assert result.removed == 1


def test_a_version_that_is_not_kept_is_removed_in_one_request_without_re_adding_anything():
    client = client_with([uri(1), uri(2), uri(3)])
    client.sp.track_info = {
        uri(1): {"uri": uri(1), "name": "Gasolina", "artists": [{"name": "Daddy Yankee"}]},
        uri(2): {"uri": uri(2), "name": "Gasolina - Remastered", "artists": [{"name": "Daddy Yankee"}]},
        uri(3): {"uri": uri(3), "name": "Otra", "artists": [{"name": "Daddy Yankee"}]},
    }
    key = find_duplicate_groups(client.get_playlist_tracks(PL), MODE_SAME_TITLE)[0].key

    result = run(client, MODE_SAME_TITLE, {key: uri(2)})  # keep the remaster, drop the original

    assert client.sp.playlists[PL] == [uri(2), uri(3)] and result.removed == 1
    assert client.sp.remove_calls == [[uri(1)]] and client.sp.add_calls == []


def test_every_copy_of_a_removed_version_goes_away():
    client = client_with([uri(1), uri(2), uri(1)])
    client.sp.track_info = {
        uri(1): {"uri": uri(1), "name": "Gasolina", "artists": [{"name": "Daddy Yankee"}]},
        uri(2): {"uri": uri(2), "name": "Gasolina - Remastered", "artists": [{"name": "Daddy Yankee"}]},
    }
    key = find_duplicate_groups(client.get_playlist_tracks(PL), MODE_SAME_TITLE)[0].key

    run(client, MODE_SAME_TITLE, {key: uri(2)})

    assert client.sp.playlists[PL] == [uri(2)]


def test_a_large_cleanup_stays_exact():
    base = [uri(i) for i in range(150)]
    client = client_with(base + base)  # every track twice

    result = run(client, MODE_SAME_TRACK, {u: u for u in base})

    assert client.sp.playlists[PL] == base
    assert result.removed == 150 and result.lost == []


def test_progress_is_reported():
    client = client_with([uri(1), uri(1), uri(2), uri(2)])
    seen = []

    run(client, MODE_SAME_TRACK, {uri(1): uri(1), uri(2): uri(2)}, on_progress=lambda done, total: seen.append((done, total)))

    assert seen == [(1, 2), (2, 2)]


def test_a_failed_removal_reports_the_error_and_changes_nothing():
    client = client_with([uri(1), uri(1)])
    client.sp.fail_writes.add(PL)

    result = run(client, MODE_SAME_TRACK, {uri(1): uri(1)})

    assert "403" in result.error and result.removed == 0 and result.lost == []
    assert client.sp.playlists[PL] == [uri(1), uri(1)]


def test_if_putting_a_track_back_in_place_fails_it_is_added_at_the_end_instead_of_lost():
    client = client_with([uri(1), uri(2), uri(1)])
    client.sp.insert_failures.add(uri(1))  # inserting at a position fails

    result = run(client, MODE_SAME_TRACK, {uri(1): uri(1)})

    assert result.error is not None and result.lost == []
    assert client.sp.playlists[PL] == [uri(2), uri(1)]  # not in its place, but not lost


def test_a_track_that_cannot_be_put_back_at_all_is_reported_as_lost():
    client = client_with([uri(1), uri(1), uri(2)])
    client.sp.insert_failures.add(uri(1))
    original_add = client.sp.playlist_add_items

    def failing_add(playlist_id, uris, position=None):  # the fallback append fails too
        raise __import__("spotipy").exceptions.SpotifyException(500, -1, "down")

    client.sp.playlist_add_items = failing_add

    result = run(client, MODE_SAME_TRACK, {uri(1): uri(1)})

    assert result.lost == [uri(1)] and result.error
    client.sp.playlist_add_items = original_add


def test_the_final_check_waits_for_spotify_to_reflect_the_changes():
    client = client_with([uri(1), uri(1), uri(2)])
    client.sp.stale_reads = 2  # the first reads after a write still show the old state
    waits = []

    result = remove_duplicates(client, PL, MODE_SAME_TRACK, {uri(1): uri(1)}, sleep=waits.append)

    assert client.sp.playlists[PL] == [uri(1), uri(2)]
    assert result.restored == 0 and result.removed == 1  # a stale read must not look like a failure
    assert waits  # it did wait


def test_nothing_chosen_makes_no_request():
    client = client_with([uri(1), uri(1)])

    result = run(client, MODE_SAME_TRACK, {})

    assert client.sp.remove_calls == [] and client.sp.add_calls == [] and result.removed == 0
