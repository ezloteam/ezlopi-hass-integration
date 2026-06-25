"""Switch platform for the ezloPi integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzloConfigEntry
from .coordinator import EzloDataUpdateCoordinator
from .entity import EzloEntity, async_setup_ezlo_platform

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzloConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ezloPi switches (standalone on/off devices only)."""
    for coordinator in entry.runtime_data.coordinators:
        async_setup_ezlo_platform(
            coordinator, "switch", _make_switch, async_add_entities
        )


def _make_switch(
    coordinator: EzloDataUpdateCoordinator, element: dict[str, Any]
) -> "EzloSwitch | None":
    """Create a switch, unless this on/off item belongs to a dimmer.

    A dimmer device's on/off item is owned by its light entity, so it must not
    also surface as a standalone switch.
    """
    device_id = element.get("deviceId")
    if any(
        e.get("deviceId") == device_id and e["type"] == "light"
        for e in coordinator.data.values()
    ):
        return None
    return EzloSwitch(coordinator, element)


class EzloSwitch(EzloEntity, SwitchEntity):
    """An ezloPi on/off switch item."""

    _attr_translation_key = "switch"

    def __init__(self, coordinator: EzloDataUpdateCoordinator, element: dict[str, Any]) -> None:
        super().__init__(coordinator, element)
        if element.get("deviceClass") == "outlet":
            self._attr_device_class = SwitchDeviceClass.OUTLET

    @property
    def is_on(self) -> bool:
        return self._element.get("value") == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_value(self._device_id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_value(self._device_id, False)
