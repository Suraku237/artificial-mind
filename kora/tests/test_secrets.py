import pytest

from memory import looks_like_secret


@pytest.mark.parametrize("text", [
    "my password is hunter2",
    "PASSWORD: Tr0ub4dor&3",
    "api_key=abc123def456",
    "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789",
    "AKIAIOSFODNN7EXAMPLE",
    "sk-proj-abcdefghijklmnopqrstuvwxyz123456",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "x7Kq9Lm2Np4Rs6Tv8Wx0Yz1Ab3Cd5Ef7Gh9Ij1Kl3Mn",
])
def test_secrets_are_detected(text):
    assert looks_like_secret(text)


@pytest.mark.parametrize("text", [
    "My systems design exam is on 3 November",
    "I prefer Flutter for mobile and React for web",
    "I deployed the attendance app on Contabo with Docker on Monday",
    "Jenkins runs the CI pipeline for my projects",
])
def test_normal_sentences_pass(text):
    assert not looks_like_secret(text)


def test_known_false_positive_is_blocked():
    # The filter is strict on purpose: harmless uses of "token" are blocked too.
    assert looks_like_secret("I studied the token bucket algorithm")
