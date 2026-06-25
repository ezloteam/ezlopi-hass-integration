"""Light platform for ezloPi integration."""
from homeassistant.components.light import (
    LightEntity,
    ColorMode,
    ATTR_BRIGHTNESS,
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

lights = []

async def async_update_lights(event):
    """Handle update events for lights."""
    event_data = event.data
    light_id = event_data.get('id', None)

    if light_id:
        for light in lights:
            if light.get_device_id() == light_id:
                await light.async_update()
                light.async_schedule_update_ha_state(True)
    else:
        await update_lights()


async def update_lights():
    """Update all lights."""
    for light in lights:
        _LOGGER.info(f"Updating light {light.name}")
        await light.async_update()
        light.async_schedule_update_ha_state(True)


def callback():
    """Callback for WebSocket updates."""
    pass


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    """Set up ezloPi lights from a config entry."""
    hubInfo = hass.data[DOMAIN][entry.entry_id]["hubInfo"]
    _LOGGER.info('Setting up lights for hub: {}'.format(hubInfo))
    
    # Listen for update events
    hass.bus.async_listen('update_all_sensors_and_switches', async_update_lights)
    await asyncio.sleep(5)

    for key, value in hubInfo.items():
        serial = key
        connection = value

        devices = await get_devices_from_platform(connection)
        global lights
        
        # Filter for light devices (dimmers)
        lights_local = [
            EzloLight(device, hass, connection, serial)
            for device in devices
            if device["type"] == "light"
        ]
        
        _LOGGER.info('Found {} lights/dimmers'.format(len(lights_local)))
        
        # Log device detection for debugging
        for device in devices:
            if device["type"] == "light":
                _LOGGER.debug(
                    f"Light '{device.get('name')}' - "
                    f"class: {device.get('deviceClass')}, "
                    f"value: {device.get('value')}"
                )
        
        async_add_entities(lights_local)
        connection.add_callback(callback)
        lights += lights_local
        
        # Store in hass.data for access from other components
        hass.data.setdefault('lights', []).extend(lights_local)


class EzloLight(LightEntity):
    """Representation of an ezloPi light/dimmer."""
    
    def __init__(self, device, hass, connection, serial):
        """Initialize the light."""
        _LOGGER.info('Adding light {}:{}'.format(serial, device))
        
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
        
        # Initialize brightness and state
        value = device.get("value", 0)
        if isinstance(value, (int, float)):
            # If value is numeric, use it as brightness (0-100)
            self._brightness = int(value)
            self._is_on = self._brightness > 0
        elif isinstance(value, str):
            # If value is string, check if it's on/off
            self._is_on = value.lower() in ['on', 'true']
            self._brightness = 100 if self._is_on else 0
        elif isinstance(value, bool):
            # If value is bool, convert to brightness
            self._is_on = value
            self._brightness = 100 if value else 0
        else:
            # Default state
            self._is_on = False
            self._brightness = 0
        
        # Set color mode - dimmers only support brightness
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        
        self._timing = 0
        
        self._attributes = {
            "device_name": device.get("deviceName", ""),
            "device_type": device["type"],
            "hubDeviceId": device["deviceId"],
            "lightId": self._device_id,
        }
        
        # Add category/subcategory if available
        if "category" in device:
            self._attributes["category"] = device["category"]
        if "subcategory" in device:
            self._attributes["subcategory"] = device["subcategory"]
        
        self._unique_id = f"{self._serial}_{self._device_id}"
    
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
        """Return the name of the light."""
        return self._name
    
    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        # Convert from ezloPi scale (0-100) to Home Assistant scale (0-255)
        return int((self._brightness * 255) / 100)
    
    @property
    def is_on(self):
        """Return true if light is on."""
        return self._is_on
    
    @property
    def available(self):
        """Return True if entity is available."""
        return True
    
    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs:
            # Convert Home Assistant brightness (0-255) to ezloPi scale (0-100)
            brightness = kwargs[ATTR_BRIGHTNESS]
            self._brightness = int((brightness * 100) / 255)
        else:
            # If no brightness specified, use 100%
            self._brightness = 100
        
        self._is_on = True
        await self.set_dimmer_value(self._brightness)
        self.async_write_ha_state()
        self._timing = time.time()
    
    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        self._brightness = 0
        self._is_on = False
        await self.set_dimmer_value(0)
        self.async_write_ha_state()
        self._timing = time.time()
    
    def get_device_name(self):
        """Get the device name."""
        return self._device_name
    
    def get_device_id(self):
        """Get the device ID."""
        return self._device_id
    
    async def set_dimmer_value(self, value):
        """Set the dimmer to a specific value (0-100)."""
        # Check if this is a special dimmer that needs different handling
        if self._name_internal == "Dimmer":
            # Look for associated dimmer value item
            # This is for devices that have separate on/off and dimmer items
            await self.set_associated_dimmer(value)
        else:
            # Standard dimmer - send value directly
            request = set_item_value_request(self._device_id, value)
            self.connection.send_message(json.dumps(request))
            _LOGGER.debug(f"Set {self._name} brightness to {value}%")
    
    async def set_associated_dimmer(self, value):
        """Handle dimmers that have a separate dimmer value item."""
        # This handles special case where dimmer has separate control items
        # Look for associated dimmer value item in sensors
        sensors = self._hass.data.get('sensors', [])
        
        value_item_id = None
        for sensor in sensors:
            if hasattr(sensor, 'get_device_name'):
                if sensor.get_device_name() == "dimmer":
                    value_item_id = sensor.get_device_id()
                    break
        
        if value_item_id:
            request = set_item_value_request(value_item_id, value)
            self.connection.send_message(json.dumps(request))
            _LOGGER.debug(f"Set associated dimmer {value_item_id} to {value}%")
        else:
            # Fallback to setting own value
            request = set_item_value_request(self._device_id, value)
            self.connection.send_message(json.dumps(request))
            _LOGGER.debug(f"Set {self._name} brightness to {value}%")
    
    async def test_connection(self):
        """Test connection to the device."""
        ip_address = self.connection.get_ip_address()
        if ip_address and not await ping_host(ip_address):
            self._is_on = False
            self._brightness = 0
    
    async def async_update(self):
        """Fetch new state data for this light."""
        # Don't update immediately after setting value (avoid race condition)
        if time.time() - self._timing > 3.0:
            try:
                value = await get_device_data(self._device_id, self.connection)
                
                if isinstance(value, (int, float)):
                    # Numeric value is brightness
                    self._brightness = int(value)
                    self._is_on = self._brightness > 0
                elif isinstance(value, str):
                    # String value might be on/off
                    if value.lower() in ['on', 'off']:
                        self._is_on = value.lower() == 'on'
                        # Keep current brightness if turning on/off
                        if not self._is_on:
                            self._brightness = 0
                    else:
                        # Try to parse as number
                        try:
                            self._brightness = int(value)
                            self._is_on = self._brightness > 0
                        except (ValueError, TypeError):
                            _LOGGER.warning(f"Unable to parse light value: {value}")
                elif isinstance(value, bool):
                    # Boolean value
                    self._is_on = value
                    if not self._is_on:
                        self._brightness = 0
                
                _LOGGER.debug(f"Updated {self._name} - on: {self._is_on}, brightness: {self._brightness}%")
            except Exception as e:
                _LOGGER.error(f"Error updating {self._name}: {e}")
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = self._attributes.copy()
        attrs["brightness_percent"] = self._brightness
        return attrs