"""Binary sensor platform for the ezloPi integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzloConfigEntry
from .coordinator import EzloDataUpdateCoordinator
from .entity import EzloEntity, async_setup_ezlo_platform
from typing import Any

PARALLEL_UPDATES = 0

_DEVICE_CLASS_MAP = {
    "motion": BinarySensorDeviceClass.MOTION,
    "door": BinarySensorDeviceClass.DOOR,
    "window": BinarySensorDeviceClass.WINDOW,
    "tamper": BinarySensorDeviceClass.TAMPER,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "presence": BinarySensorDeviceClass.PRESENCE,
    "occupancy": BinarySensorDeviceClass.OCCUPANCY,
    "moisture": BinarySensorDeviceClass.MOISTURE,
    "water": BinarySensorDeviceClass.MOISTURE,
    "leak": BinarySensorDeviceClass.MOISTURE,
    "safety": BinarySensorDeviceClass.SAFETY,
    "battery": BinarySensorDeviceClass.BATTERY,
    "problem": BinarySensorDeviceClass.PROBLEM,
    "gas": BinarySensorDeviceClass.GAS,
    "heat": BinarySensorDeviceClass.HEAT,
    "light": BinarySensorDeviceClass.LIGHT,
    "lock": BinarySensorDeviceClass.LOCK,
    "opening": BinarySensorDeviceClass.OPENING,
    "plug": BinarySensorDeviceClass.PLUG,
    "power": BinarySensorDeviceClass.POWER,
    "running": BinarySensorDeviceClass.RUNNING,
    "sound": BinarySensorDeviceClass.SOUND,
    "update": BinarySensorDeviceClass.UPDATE,
    "vibration": BinarySensorDeviceClass.VIBRATION,
}

_TRUTHY = ("on", "true", "1", "open", "detected", "motion")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzloConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ezloPi binary sensors."""
    for coordinator in entry.runtime_data.coordinators:
        async_setup_ezlo_platform(
            coordinator, "binary_sensor", EzloBinarySensor, async_add_entities
        )


class EzloBinarySensor(EzloEntity, BinarySensorEntity):
    """An ezloPi binary sensor item."""

    def __init__(self, coordinator: EzloDataUpdateCoordinator, element: dict[str, Any]) -> None:
        super().__init__(coordinator, element)
        self._attr_device_class = _DEVICE_CLASS_MAP.get(element.get("deviceClass") or "")

    @property
    def is_on(self) -> bool:
        value = self._element.get("value")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in _TRUTHY
        if isinstance(value, (int, float)):
            return bool(value)
        return False
