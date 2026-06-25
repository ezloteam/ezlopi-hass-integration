"""Climate platform for the ezloPi integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzloConfigEntry
from .coordinator import EzloDataUpdateCoordinator
from .entity import EzloEntity, async_setup_ezlo_platform

PARALLEL_UPDATES = 0

_MODE_TO_HVAC = {
    "off": HVACMode.OFF,
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
    "auto": HVACMode.AUTO,
    "heat_cool": HVACMode.HEAT_COOL,
    "fan_only": HVACMode.FAN_ONLY,
}
_HVAC_TO_MODE = {
    HVACMode.OFF: "off",
    HVACMode.HEAT: "heat",
    HVACMode.COOL: "cool",
    HVACMode.AUTO: "auto",
    HVACMode.HEAT_COOL: "auto",
    HVACMode.FAN_ONLY: "fan_only",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzloConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ezloPi thermostats."""
    for coordinator in entry.runtime_data.coordinators:
        async_setup_ezlo_platform(
            coordinator, "climate", EzloClimate, async_add_entities
        )


class EzloClimate(EzloEntity, ClimateEntity):
    """An ezloPi thermostat item."""

    _attr_translation_key = "thermostat"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator: EzloDataUpdateCoordinator, element: dict[str, Any]) -> None:
        super().__init__(coordinator, element)
        if element.get("scale") == "fahrenheit":
            self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
            self._attr_min_temp, self._attr_max_temp = 50.0, 95.0
        else:
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS
            self._attr_min_temp, self._attr_max_temp = 10.0, 35.0
        # The hub exposes a single item; HVAC mode / setpoint are tracked
        # optimistically until the hub reports a richer structure.
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 20.0

    @property
    def current_temperature(self) -> float | None:
        value = self._element.get("value")
        if isinstance(value, dict):
            value = value.get("current_temp")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @property
    def hvac_action(self) -> HVACAction:
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        current, target = self.current_temperature, self._attr_target_temperature
        if current is None or target is None:
            return HVACAction.IDLE
        if self._attr_hvac_mode == HVACMode.HEAT:
            return HVACAction.HEATING if current < target else HVACAction.IDLE
        if self._attr_hvac_mode == HVACMode.COOL:
            return HVACAction.COOLING if current > target else HVACAction.IDLE
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._attr_target_temperature = temperature
        await self._async_set_value(self._device_id, temperature)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._attr_hvac_mode = hvac_mode
        await self._async_set_value(
            self._device_id, _HVAC_TO_MODE.get(hvac_mode, "off")
        )
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)
