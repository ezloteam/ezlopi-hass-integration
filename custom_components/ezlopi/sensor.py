"""Sensor platform for the ezloPi integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzloConfigEntry
from .coordinator import EzloDataUpdateCoordinator
from .entity import EzloEntity, async_setup_ezlo_platform
from typing import Any

# Push integration: there is no per-entity polling to serialize.
PARALLEL_UPDATES = 0

_DEVICE_CLASS_MAP = {
    "battery": SensorDeviceClass.BATTERY,
    "temperature": SensorDeviceClass.TEMPERATURE,
    "humidity": SensorDeviceClass.HUMIDITY,
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
    "voltage": SensorDeviceClass.VOLTAGE,
    "current": SensorDeviceClass.CURRENT,
    "pressure": SensorDeviceClass.PRESSURE,
    "illuminance": SensorDeviceClass.ILLUMINANCE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzloConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ezloPi sensors from the coordinators on this entry."""
    for coordinator in entry.runtime_data.coordinators:
        async_setup_ezlo_platform(
            coordinator, "sensor", EzloSensor, async_add_entities
        )


class EzloSensor(EzloEntity, SensorEntity):
    """An ezloPi sensor item."""

    def __init__(self, coordinator: EzloDataUpdateCoordinator, element: dict[str, Any]) -> None:
        super().__init__(coordinator, element)
        self._attr_device_class = _DEVICE_CLASS_MAP.get(element.get("deviceClass") or "")
        self._attr_native_unit_of_measurement = element.get("unitOfMeasurement")
        if self._attr_device_class == SensorDeviceClass.BATTERY:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        return self._element.get("value")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        element = self._element
        attrs = {
            "device_name": element.get("deviceName"),
            "device_type": element.get("type"),
            "hubDeviceId": element.get("deviceId"),
            "sensorId": self._device_id,
            "unit_of_measurement": element.get("unitOfMeasurement"),
        }
        if self._attr_device_class == SensorDeviceClass.BATTERY:
            attrs["battery_status"] = self._get_battery_status(element.get("value"))
        return attrs

    @property
    def icon(self) -> str | None:
        """Battery sensors get a level-appropriate icon."""
        if self._attr_device_class != SensorDeviceClass.BATTERY:
            return None
        try:
            level = float(self.native_value) if self.native_value is not None else 0
        except (ValueError, TypeError):
            return "mdi:battery-unknown"
        if level >= 95:
            return "mdi:battery"
        for threshold, suffix in (
            (85, "-90"), (75, "-80"), (65, "-70"), (55, "-60"), (45, "-50"),
            (35, "-40"), (25, "-30"), (15, "-20"), (5, "-10"),
        ):
            if level >= threshold:
                return f"mdi:battery{suffix}"
        if level > 0:
            return "mdi:battery-alert"
        return "mdi:battery-unknown"
