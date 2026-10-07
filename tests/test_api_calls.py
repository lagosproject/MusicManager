import pytest
from spotipy.exceptions import SpotifyException

from music_manager.core.api_calls import call_with_retry, describe_api_error


def rate_limited(wait="2"):
    return SpotifyException(429, -1, "rate limit", headers={"Retry-After": wait})


def flaky(failures, exc):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] <= failures:
            raise exc
        return "ok"

    return fn, calls


def test_waits_out_a_429_and_succeeds():
    fn, calls = flaky(2, rate_limited("3"))
    waits = []

    assert call_with_retry(fn, sleep=waits.append) == "ok"
    assert calls["n"] == 3 and waits == [3, 3]


def test_gives_up_after_the_attempts():
    fn, calls = flaky(99, rate_limited())

    with pytest.raises(SpotifyException):
        call_with_retry(fn, attempts=3, sleep=lambda s: None)
    assert calls["n"] == 3


def test_does_not_wait_for_a_very_long_retry_after():
    fn, calls = flaky(1, rate_limited("3600"))
    waits = []

    with pytest.raises(SpotifyException):
        call_with_retry(fn, sleep=waits.append)
    assert waits == [] and calls["n"] == 1


def test_other_errors_are_not_retried():
    fn, calls = flaky(5, SpotifyException(403, -1, "Forbidden"))

    with pytest.raises(SpotifyException):
        call_with_retry(fn, sleep=lambda s: None)
    assert calls["n"] == 1


def test_describe_api_error():
    assert "limita" in describe_api_error(rate_limited("30"))
    assert "30" in describe_api_error(rate_limited("30"))
    assert "403" in describe_api_error(SpotifyException(403, -1, "Forbidden"))
    assert "404" in describe_api_error(SpotifyException(404, -1, "Not found"))
    assert "500" in describe_api_error(SpotifyException(500, -1, "boom"))
