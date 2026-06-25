"""Climate platform for ezloPi integration."""
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .utils import *
import logging
import asyncio
import time
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

climates = []

async def async_update_climates(event):
    """Handle update events for climate entities."""
    event_data = event.data
    climate_id = event_data.get('id', None)

    if climate_id:
        for climate in climates:
            if climate.get_device_id() == climate_id:
                await climate.async_update()
                climate.async_schedule_update_ha_state(True)
    else:
        await update_climates()


async def update_climates():
    """Update all climate entities."""
    for climate in climates:
        _LOGGER.info(f"Updating climate {climate.name}")
        await climate.async_update()
        climate.async_schedule_update_ha_state(True)


def callback():
    """Callback for WebSocket updates."""
    pass


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    """Set up ezloPi climate entities from a config entry."""
    hubInfo = hass.data[DOMAIN][entry.entry_id]["hubInfo"]
    _LOGGER.info('Setting up climate entities for hub: {}'.format(hubInfo))
    
    # Listen for update events
    hass.bus.async_listen('update_all_sensors_and_switches', async_update_climates)
    await asyncio.sleep(5)

    for key, value in hubInfo.items():
        serial = key
        connection = value

        devices = await get_devices_from_platform(connection)
        global climates
        
        # Filter for climate devices (thermostats)
        climates_local = [
            EzloClimate(device, hass, connection, serial)
            for device in devices
            if device["type"] == "climate"
        ]
        
        _LOGGER.info('Found {} climate devices'.format(len(climates_local)))
        
        # Log device detection for debugging
        for device in devices:
            if device["type"] == "climate":
                _LOGGER.debug(
                    f"Climate '{device.get('name')}' - "
                    f"class: {device.get('deviceClass')}, "
                    f"value: {device.get('value')}"
                )
        
        async_add_entities(climates_local)
        connection.add_callback(callback)
        climates += climates_local
        
        # Store in hass.data for access from other components
        hass.data.setdefault('climates', []).extend(climates_local)


class EzloClimate(ClimateEntity):
    """Representation of an ezloPi thermostat."""
    
    def __init__(self, device, hass, connection, serial):
        """Initialize the climate entity."""
        _LOGGER.info('Adding climate {}:{}'.format(serial, device))
        
        self._hass = hass
        self._name = '{}_{}:'.format(serial, device["id"])
        
        if 'deviceName' in device:
            self._name += device["deviceName"] + ": " + device["name"]
        else:
            self._name = device["name"]
        
        self._serial = serial
        self._device_id = device["id"]
        self._device_name = device["name"]
        self._name_internal = device.get("deviceName", "")
        self.connection = connection
        
        # Initialize temperature and mode
        self._current_temperature = None
        self._target_temperature = None
        self._hvac_mode = HVACMode.OFF
        self._hvac_action = HVACAction.OFF
        
        # Parse initial value if available
        value = device.get("value")
        if isinstance(value, dict):
            # Value might contain temperature and mode info
            self._current_temperature = value.get("current_temp")
            self._target_temperature = value.get("target_temp", 20.0)
            mode = value.get("mode", "off")
            self._hvac_mode = self._map_mode_to_hvac(mode)
        elif isinstance(value, (int, float)):
            # Simple numeric value, assume it's current temperature
            self._current_temperature = float(value)
            self._target_temperature = 20.0
        
        # Set supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.TURN_ON |
            ClimateEntityFeature.TURN_OFF
        )
        
        # Set temperature unit (default to Celsius)
        scale = device.get("scale", "celsius")
        if scale == "fahrenheit":
            self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
        else:
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        
        # Set HVAC modes
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.AUTO,
        ]
        
        # Temperature settings
        self._attr_min_temp = 10.0 if self._attr_temperature_unit == UnitOfTemperature.CELSIUS else 50.0
        self._attr_max_temp = 35.0 if self._attr_temperature_unit == UnitOfTemperature.CELSIUS else 95.0
        self._attr_target_temperature_step = 0.5
        
        self._timing = 0
        
        self._attributes = {
            "device_name": device.get("deviceName", ""),
            "device_type": device["type"],
            "hubDeviceId": device["deviceId"],
            "climateId": self._device_id,
        }
        
        # Add category/subcategory if available
        if "category" in device:
            self._attributes["category"] = device["category"]
        if "subcategory" in device:
            self._attributes["subcategory"] = device["subcategory"]
        
        self._unique_id = f"{self._serial}_{self._device_id}"
        
        # Track related items (for multi-item thermostats)
        self._temperature_item_id = None
        self._setpoint_item_id = None
        self._mode_item_id = None
        self._find_related_items()
    
    def _find_related_items(self):
        """Find related thermostat items (temperature sensor, setpoint, mode)."""
        # This would scan for related items based on device ID
        # For now, we'll use the main item for all functions
        self._temperature_item_id = self._device_id
        self._setpoint_item_id = self._device_id
        self._mode_item_id = self._device_id
    
    @property
    def unique_id(self):
        """Return unique ID for this entity."""
        return self._unique_id
    
    @property
    def device_info(self):
        """Return device information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._serial)},
        }
    
    @property
    def name(self):
        """Return the name of the climate entity."""
        return self._name
    
    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature
    
    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature
    
    @property
    def hvac_mode(self):
        """Return current HVAC mode."""
        return self._hvac_mode
    
    @property
    def hvac_action(self):
        """Return current HVAC action."""
        # Determine action based on current and target temp
        if self._hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        elif self._hvac_mode == HVACMode.HEAT:
            if self._current_temperature and self._target_temperature:
                if self._current_temperature < self._target_temperature:
                    return HVACAction.HEATING
                else:
                    return HVACAction.IDLE
        elif self._hvac_mode == HVACMode.COOL:
            if self._current_temperature and self._target_temperature:
                if self._current_temperature > self._target_temperature:
                    return HVACAction.COOLING
                else:
                    return HVACAction.IDLE
        
        return HVACAction.IDLE
    
    @property
    def available(self):
        """Return True if entity is available."""
        return True
    
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._target_temperature = temperature
            await self.set_thermostat_setpoint(temperature)
            self.async_write_ha_state()
            self._timing = time.time()
            _LOGGER.info(f"Set {self._name} target temperature to {temperature}°")
    
    async def async_set_hvac_mode(self, hvac_mode):
        """Set new HVAC mode."""
        self._hvac_mode = hvac_mode
        await self.set_thermostat_mode(hvac_mode)
        self.async_write_ha_state()
        self._timing = time.time()
        _LOGGER.info(f"Set {self._name} mode to {hvac_mode}")
    
    async def async_turn_on(self):
        """Turn on the climate device."""
        # Default to heat mode when turning on
        await self.async_set_hvac_mode(HVACMode.HEAT)
    
    async def async_turn_off(self):
        """Turn off the climate device."""
        await self.async_set_hvac_mode(HVACMode.OFF)
    
    def get_device_name(self):
        """Get the device name."""
        return self._device_name
    
    def get_device_id(self):
        """Get the device ID."""
        return self._device_id
    
    async def set_thermostat_setpoint(self, temperature):
        """Set the thermostat setpoint temperature."""
        # Send setpoint command via WebSocket
        request = set_item_value_request(self._setpoint_item_id, temperature)
        self.connection.send_message(json.dumps(request))
        _LOGGER.debug(f"Set {self._name} setpoint to {temperature}°")
    
    async def set_thermostat_mode(self, hvac_mode):
        """Set the thermostat mode."""
        # Map HVAC mode to ezloPi mode
        mode_value = self._map_hvac_to_mode(hvac_mode)
        
        # Send mode command via WebSocket
        request = set_item_value_request(self._mode_item_id, mode_value)
        self.connection.send_message(json.dumps(request))
        _LOGGER.debug(f"Set {self._name} mode to {mode_value}")
    
    def _map_mode_to_hvac(self, mode):
        """Map ezloPi mode to HVAC mode."""
        mode_lower = str(mode).lower()
        mapping = {
            "off": HVACMode.OFF,
            "heat": HVACMode.HEAT,
            "cool": HVACMode.COOL,
            "auto": HVACMode.AUTO,
            "heat_cool": HVACMode.HEAT_COOL,
            "fan_only": HVACMode.FAN_ONLY,
        }
        return mapping.get(mode_lower, HVACMode.OFF)
    
    def _map_hvac_to_mode(self, hvac_mode):
        """Map HVAC mode to ezloPi mode."""
        mapping = {
            HVACMode.OFF: "off",
            HVACMode.HEAT: "heat",
            HVACMode.COOL: "cool",
            HVACMode.AUTO: "auto",
            HVACMode.HEAT_COOL: "auto",
            HVACMode.FAN_ONLY: "fan_only",
        }
        return mapping.get(hvac_mode, "off")
    
    async def test_connection(self):
        """Test connection to the device."""
        ip_address = self.connection.get_ip_address()
        if ip_address and not await ping_host(ip_address):
            self._hvac_mode = HVACMode.OFF
    
    async def async_update(self):
        """Fetch new state data for this climate entity."""
        # Don't update immediately after setting value (avoid race condition)
        if time.time() - self._timing > 3.0:
            try:
                # Get current state
                value = await get_device_data(self._device_id, self.connection)
                
                if isinstance(value, dict):
                    # Complex value with multiple fields
                    if "current_temp" in value:
                        self._current_temperature = float(value["current_temp"])
                    if "target_temp" in value:
                        self._target_temperature = float(value["target_temp"])
                    if "mode" in value:
                        self._hvac_mode = self._map_mode_to_hvac(value["mode"])
                elif isinstance(value, (int, float)):
                    # Simple temperature value
                    self._current_temperature = float(value)
                elif isinstance(value, str):
                    # Might be mode or temperature as string
                    try:
                        self._current_temperature = float(value)
                    except ValueError:
                        # Not a temperature, might be mode
                        self._hvac_mode = self._map_mode_to_hvac(value)
                
                _LOGGER.debug(
                    f"Updated {self._name} - "
                    f"current: {self._current_temperature}°, "
                    f"target: {self._target_temperature}°, "
                    f"mode: {self._hvac_mode}"
                )
                
                # Check for battery level if available
                battery_level = get_device_battery_level(self._device_id, self.connection)
                if battery_level is not None:
                    self._attributes["battery_level"] = battery_level
                
            except Exception as e:
                _LOGGER.error(f"Error updating {self._name}: {e}")
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = self._attributes.copy()
        attrs["hvac_action"] = self.hvac_action
        return attrs