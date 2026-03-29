import pytest
from fastapi import HTTPException

from app.core.auth import check_token


class Creds:
    def __init__(self, token):
        self.credentials = token


def test_should_fail_when_check_token_missing():
    # When & Then
    with pytest.raises(HTTPException) as ei:
        check_token(Creds(None))
    assert ei.value.status_code == 401
    assert "Missing auth token" in ei.value.detail


def test_should_fail_when_check_token_incorrect_length():
    # When & Then
    with pytest.raises(HTTPException) as ei:
        check_token(Creds("short"))
    assert ei.value.status_code == 401
    assert "Incorrect auth token" in ei.value.detail


def test_should_pass_when_check_token_ok():
    # Given
    token = "x" * 31

    # Then
    assert check_token(Creds(token)) is True
