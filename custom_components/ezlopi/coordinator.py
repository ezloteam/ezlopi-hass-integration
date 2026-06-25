"""Push DataUpdateCoordinator for a single ezloPi hub."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .connection import EzloHubConnection
from .const import DOMAIN
from .utils import getItemsData

_LOGGER = logging.getLogger(__name__)


class EzloDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Owns one hub's websocket connection and pushes item updates to entities.

    This is a push coordinator: ``update_interval`` is ``None`` and new data is
    delivered via ``async_set_updated_data`` whenever the hub broadcasts an item
    change, rather than by polling.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        connection: EzloHubConnection,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {connection.serial}",
            update_interval=None,
            config_entry=entry,
        )
        self.connection = connection
        self.serial = connection.serial
        # The connection calls this whenever hub state changes (or connectivity
        # is lost), so entities re-render with fresh data / availability.
        connection._on_update = self._handle_push

    @callback
    def _handle_push(self) -> None:
        self.async_set_updated_data(self._build_data())

    def _build_data(self) -> dict[str, Any]:
        """Process the hub's raw items into {item_id: element}."""
        elements = getItemsData(self.connection) or []
        return {element["id"]: element for element in elements}

    async def _async_update_data(self) -> dict[str, Any]:
        # Pure push: only used for the initial refresh; the data is already in
        # memory from the connection's first item list.
        return self._build_data()
