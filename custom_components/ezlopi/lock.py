"""Lock platform for the ezloPi integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzloConfigEntry
from .entity import EzloEntity, async_setup_ezlo_platform

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzloConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ezloPi locks."""
    for coordinator in entry.runtime_data.coordinators:
        async_setup_ezlo_platform(
            coordinator, "lock", EzloLock, async_add_entities
        )


class EzloLock(EzloEntity, LockEntity):
    """An ezloPi lock item."""

    _attr_translation_key = "lock"

    @property
    def is_locked(self) -> bool | None:
        value = self._element.get("value")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("locked", "true", "1")
        if isinstance(value, (int, float)):
            return bool(value)
        return None

    async def async_lock(self, **kwargs: Any) -> None:
        await self._async_set_value(self._device_id, True)

    async def async_unlock(self, **kwargs: Any) -> None:
        await self._async_set_value(self._device_id, False)
