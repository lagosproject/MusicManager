from unittest.mock import MagicMock

import pytest

from music_manager.core.spotify_client import SpotifyClient


def make_track(n: int, artist: str = "Artista") -> dict:
    return {"uri": f"spotify:track:{n}", "name": f"Cancion {n}", "artists": [{"name": artist}]}


@pytest.fixture
def client() -> SpotifyClient:
    # Skip __init__ so no OAuth/network is involved
    c = SpotifyClient.__new__(SpotifyClient)
    c.sp = MagicMock()
    return c


def test_create_playlist_uses_me_playlists_route(client):
    client.sp.current_user_playlist_create.return_value = {"id": "abc123"}

    playlist_id = client.create_playlist("Mi lista", public=False, description="d")

    assert playlist_id == "abc123"
    client.sp.current_user_playlist_create.assert_called_once_with(
        name="Mi lista", public=False, description="d"
    )
    client.sp.user_playlist_create.assert_not_called()  # /users/{id}/playlists returns 403 since 2026


def test_add_tracks_batches_of_100(client):
    uris = [f"spotify:track:{i}" for i in range(250)]

    client.add_tracks_to_playlist("pl", uris)

    sizes = [len(call.args[1]) for call in client.sp.playlist_add_items.call_args_list]
    assert sizes == [100, 100, 50]
