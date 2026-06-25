"""Tests for the Ezlo cloud API client (login + controller listing)."""
from typing import Any

import aiohttp
import pytest

from custom_components.ezlopi.ezlopi_utils import (
    EzloAuthError,
    EzloCloudAPI,
    EzloConnectionError,
)


class _Resp:
    def __init__(self, status: int, payload: dict | None = None,
                 raise_client: bool = False) -> None:
        self.status = status
        self._payload = payload or {}
        self._raise = raise_client

    async def __aenter__(self) -> "_Resp":
        if self._raise:
            raise aiohttp.ClientError("boom")
        return self

    async def __aexit__(self, *args: Any) -> None:
        return

    async def json(self) -> dict:
        return self._payload


class _Session:
    """Returns queued responses for successive post()/get() calls."""

    def __init__(self, *responses: _Resp) -> None:
        self._responses = list(responses)

    def _next(self) -> _Resp:
        return self._responses.pop(0)

    def post(self, *args: Any, **kwargs: Any) -> _Resp:
        return self._next()

    def get(self, *args: Any, **kwargs: Any) -> _Resp:
        return self._next()


def _api(*responses: _Resp) -> EzloCloudAPI:
    return EzloCloudAPI("user", "pass", _Session(*responses))  # type: ignore[arg-type]


async def test_fetch_hub_list_success() -> None:
    api = _api(
        _Resp(200, {"token": "jwt"}),
        _Resp(200, {"controllers": [
            {"serial": "111", "uuid": "u", "name": "Hub", "local_key": "lk"},
            {"serial": "", "uuid": "x", "name": "skip"},  # blank serial ignored
        ]}),
    )
    assert await api.fetch_hub_list() is True
    hubs = api.get_hub_list()
    assert list(hubs) == ["111"]
    assert hubs["111"].token == "lk"


async def test_login_invalid_credentials() -> None:
    with pytest.raises(EzloAuthError):
        await _api(_Resp(200, {})).fetch_hub_list()


async def test_login_rejected_status() -> None:
    with pytest.raises(EzloAuthError):
        await _api(_Resp(401)).fetch_hub_list()


async def test_login_server_error() -> None:
    with pytest.raises(EzloConnectionError):
        await _api(_Resp(500)).fetch_hub_list()


async def test_login_client_error() -> None:
    with pytest.raises(EzloConnectionError):
        await _api(_Resp(200, raise_client=True)).fetch_hub_list()


async def test_controller_list_no_controllers() -> None:
    api = _api(_Resp(200, {"token": "jwt"}), _Resp(200, {"controllers": []}))
    assert await api.fetch_hub_list() is False


async def test_controller_list_http_error() -> None:
    api = _api(_Resp(200, {"token": "jwt"}), _Resp(503))
    assert await api.fetch_hub_list() is False


async def test_controller_list_client_error() -> None:
    api = _api(_Resp(200, {"token": "jwt"}), _Resp(200, raise_client=True))
    with pytest.raises(EzloConnectionError):
        await api.fetch_hub_list()
