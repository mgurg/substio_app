import pytest
from fastapi import HTTPException

from app.common.auth import check_token


class Creds:
    def __init__(self, token):
        self.credentials = token


def test_check_token_missing():
    with pytest.raises(HTTPException) as ei:
        check_token(Creds(None))
    assert ei.value.status_code == 401
    assert "Missing auth token" in ei.value.detail


def test_check_token_incorrect_length():
    with pytest.raises(HTTPException) as ei:
        check_token(Creds("short"))
    assert ei.value.status_code == 401
    assert "Incorrect auth token" in ei.value.detail


def test_check_token_ok():
    token = "x" * 31
    assert check_token(Creds(token)) is True
