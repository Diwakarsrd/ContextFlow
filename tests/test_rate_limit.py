import time

from contextflow.auth.rate_limit import RateLimiter


def test_allows_attempts_under_the_limit():
    limiter = RateLimiter(max_attempts=3, window_seconds=60)
    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    assert not limiter.is_blocked("1.2.3.4")


def test_blocks_after_max_attempts():
    limiter = RateLimiter(max_attempts=3, window_seconds=60)
    for _ in range(3):
        limiter.record_failure("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4")


def test_success_clears_failure_count():
    limiter = RateLimiter(max_attempts=3, window_seconds=60)
    for _ in range(3):
        limiter.record_failure("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4")

    limiter.record_success("1.2.3.4")
    assert not limiter.is_blocked("1.2.3.4")


def test_old_attempts_outside_window_do_not_count():
    limiter = RateLimiter(max_attempts=2, window_seconds=0.05)
    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4")

    time.sleep(0.1)
    assert not limiter.is_blocked("1.2.3.4")


def test_different_identities_are_independent():
    limiter = RateLimiter(max_attempts=1, window_seconds=60)
    limiter.record_failure("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4")
    assert not limiter.is_blocked("5.6.7.8")
