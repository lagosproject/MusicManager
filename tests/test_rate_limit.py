import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import spotipy
from spotipy.exceptions import SpotifyException

from music_manager.core.api_calls import call_with_retry, describe_api_error, humanize_seconds, make_session


class FakeSpotify(BaseHTTPRequestHandler):
    """Answers 429 with a huge Retry-After (what Spotify did), or a few 503s before succeeding."""
    mode = "429"
    hits = 0

    def do_GET(self):
        type(self).hits += 1
        if self.mode == "429":
            self.send_response(429)
            self.send_header("Retry-After", "99999")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": {"status": 429, "message": "rate limit"}}')
        elif self.mode == "503-then-ok" and type(self).hits <= 2:
            self.send_response(503)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"name": "ok"}')

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    FakeSpotify.hits = 0
    httpd = HTTPServer(("127.0.0.1", 0), FakeSpotify)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()


def client_for(server):
    sp = spotipy.Spotify(auth="token", requests_session=make_session(), requests_timeout=5)
    sp.prefix = f"http://127.0.0.1:{server.server_port}/"
    return sp


def test_a_429_with_a_huge_retry_after_comes_back_at_once_instead_of_sleeping(server):
    FakeSpotify.mode = "429"
    sp = client_for(server)

    started = time.time()
    with pytest.raises(SpotifyException) as caught:
        call_with_retry(sp.playlist, "abc")

    assert time.time() - started < 3          # spotipy used to sleep for the whole 99999 s here
    assert caught.value.http_status == 429
    assert caught.value.headers["Retry-After"] == "99999"
    assert FakeSpotify.hits == 1               # and it did not hammer the server while it was limiting us


def test_the_user_is_told_how_long_spotify_asks_to_wait(server):
    FakeSpotify.mode = "429"
    with pytest.raises(SpotifyException) as caught:
        call_with_retry(client_for(server).playlist, "abc")

    assert "27,8 horas" in describe_api_error(caught.value)


def test_real_server_errors_are_still_retried(server):
    FakeSpotify.mode = "503-then-ok"
    sp = client_for(server)

    assert sp.playlist("abc")["name"] == "ok"
    assert FakeSpotify.hits == 3


def test_humanize_seconds():
    assert humanize_seconds(45) == "45 s"
    assert humanize_seconds(600) == "10 min"
    assert humanize_seconds(78994) == "21,9 horas"
