"""Asyncio-native local websocket connection to a single ezloPi hub.

Replaces the previous threaded ``websocket-client`` implementation. Runs entirely
on the Home Assistant event loop and uses the HA-shared aiohttp ``ClientSession``
(injected), so no per-connection session and no background OS threads.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .mdns_connector import EzloPiMDSConnector
from .utils import get_devices_info, get_login_params, set_item_value_request

_LOGGER = logging.getLogger(__name__)

_LOGIN_METHOD = "hub.offline.login.ui"
_RECONNECT_DELAY = 5
_READY_TIMEOUT = 20
# The hub closes idle sockets; keep traffic flowing well under that window.
_KEEPALIVE_INTERVAL = 15
# Raise a repair issue once a hub has been unreachable for this many tries.
_UNREACHABLE_THRESHOLD = 3


class EzloHubConnection:
    """A persistent, self-healing websocket connection to one ezloPi hub."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        browser: EzloPiMDSConnector,
        serial: str,
        token: str | None,
        on_update: Callable[[], None],
    ) -> None:
        self._hass = hass
        self._session = session
        self._browser = browser
        self._serial = serial
        self._token = token
        self._on_update = on_update

        # Latest hub state, consumed by the coordinator via the utils helpers
        # (get_items/get_devices read these attributes).
        self.items: list[dict[str, Any]] = []
        self.devices: list[dict[str, Any]] = []
        self.device_metadata: dict[str, Any] = {}
        # Controller firmware version, from hub.info.get.
        self.firmware: str | None = None

        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._run_task: asyncio.Task[None] | None = None
        self._closed = False
        self._connected = False
        self._ready = asyncio.Event()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def serial(self) -> str:
        return self._serial

    def start(self) -> None:
        """Launch the supervised connect/listen/reconnect loop."""
        self._run_task = self._hass.async_create_background_task(
            self._async_run(), f"ezlopi-ws-{self._serial}"
        )

    async def async_wait_ready(self) -> None:
        """Wait until the hub has delivered its first item (and ideally device) list.

        Resolves once both items and devices have arrived. If only items arrive
        within the timeout we still proceed (devices refine metadata via a later
        push); we only fail when nothing at all came back.
        """
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=_READY_TIMEOUT)
        except (TimeoutError, asyncio.TimeoutError):
            if not self.items:
                raise

    async def async_stop(self) -> None:
        self._closed = True
        if self._ws is not None:
            await self._ws.close()
        if self._run_task is not None:
            self._run_task.cancel()

    async def async_set_item_value(self, item_id: str, value: Any) -> None:
        await self._send(set_item_value_request(item_id, value))

    def _resolve_url(self) -> str | None:
        return self._browser.get_connection_link_from_serial(self._serial)

    async def _send(self, payload: dict[str, Any]) -> None:
        if self._ws is None or self._ws.closed:
            raise RuntimeError(f"hub {self._serial} not connected")
        await self._ws.send_str(json.dumps(payload))

    @property
    def _issue_id(self) -> str:
        return f"hub_unreachable_{self._serial}"

    async def _async_run(self) -> None:
        failures = 0
        while not self._closed:
            url = self._resolve_url()
            if url is None:
                # Hub not yet discovered over mDNS; wait and retry.
                failures += 1
            else:
                try:
                    await self._async_connect_and_listen(url)
                    failures = 0
                except asyncio.CancelledError:
                    raise
                except Exception as err:  # noqa: BLE001 - keep the supervisor alive
                    _LOGGER.debug("hub %s connection error: %s", self._serial, err)
                    failures += 1
            self._connected = False
            self._on_update()  # surface unavailability to entities
            if failures == _UNREACHABLE_THRESHOLD:
                ir.async_create_issue(
                    self._hass,
                    DOMAIN,
                    self._issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="hub_unreachable",
                    translation_placeholders={"serial": self._serial},
                )
            if not self._closed:
                await asyncio.sleep(_RECONNECT_DELAY)

    async def _async_connect_and_listen(self, url: str) -> None:
        _LOGGER.info("Connecting to hub %s at %s", self._serial, url)
        # No ws heartbeat: the hub does not answer ping frames, so aiohttp's
        # heartbeat would tear the socket down. We keep it alive with periodic
        # application-level queries instead (see _async_keepalive).
        async with self._session.ws_connect(url) as ws:
            self._ws = ws
            self._connected = True

            # Offline login first; the hub only answers item/device queries once
            # the login has been processed, so we send those on confirmation.
            login = get_login_params()
            login["params"]["user"] = self._serial
            login["params"]["token"] = self._token
            await self._send(login)

            keepalive: asyncio.Task[None] | None = None
            try:
                queries_sent = False
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = self._parse(msg.data)
                        if data is None:
                            continue
                        if not queries_sent and data.get("method") == _LOGIN_METHOD:
                            _LOGGER.info("Hub %s logged in", self._serial)
                            await self._send_queries()
                            queries_sent = True
                            keepalive = asyncio.ensure_future(self._async_keepalive())
                            continue
                        self._handle(data)
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
            finally:
                if keepalive is not None:
                    keepalive.cancel()

    async def _send_queries(self) -> None:
        for query in get_devices_info():
            await self._send(query)

    async def _async_keepalive(self) -> None:
        """Periodically re-query so the hub keeps the socket open and data fresh."""
        while True:
            await asyncio.sleep(_KEEPALIVE_INTERVAL)
            await self._send_queries()

    @staticmethod
    def _parse(raw: str) -> dict[str, Any] | None:
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def _handle(self, data: dict[str, Any]) -> None:
        if data.get("method") == _LOGIN_METHOD:
            return

        if data.get("id") == "ui_broadcast":
            if data.get("msg_subclass") == "hub.item.updated":
                result = data.get("result", {})
                self._update_item(result.get("_id"), result.get("value"))
            return

        result = data.get("result") or {}
        changed = False
        if "firmware" in result:  # hub.info.get response
            self.firmware = result["firmware"]
            changed = True
        if "items" in result:
            self.items = result["items"]
            changed = True
        if "devices" in result:
            self.devices = result["devices"]
            self.device_metadata = {
                str(d["_id"]): {
                    "deviceType": d.get("deviceTypeId"),
                    "category": d.get("category"),
                    "subcategory": d.get("subcategory"),
                    "armed": d.get("armed", False),
                    "room_id": d.get("roomId"),
                    "battery_powered": d.get("batteryPowered", False),
                }
                for d in self.devices
                if d.get("_id")
            }
            changed = True
        if changed and self.items:
            # Ready once we have both items and their device metadata.
            if self.devices:
                self._ready.set()
                # Hub is reachable again — clear any unreachable repair issue.
                ir.async_delete_issue(self._hass, DOMAIN, self._issue_id)
            self._on_update()

    def _update_item(self, item_id: str | None, value: Any) -> None:
        if item_id is None:
            return
        for item in self.items:
            if item.get("_id") == item_id:
                item["value"] = value
                break
        self._on_update()

    def get_device_metadata(self, device_id: str) -> dict[str, Any]:
        meta: dict[str, Any] = self.device_metadata.get(device_id, {})
        return meta
