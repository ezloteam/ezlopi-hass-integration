"""Binary sensor platform for ezloPi integration."""
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .utils import *
import logging
import asyncio
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

binary_sensors = []

async def async_update_binary_sensors(event):
    """Handle update events for binary sensors."""
    event_data = event.data
    sensor_id = event_data.get('id', None)

    if sensor_id:
        for sensor in binary_sensors:
            if sensor.get_device_id() == sensor_id:
                await sensor.async_update()
                sensor.async_schedule_update_ha_state(True)
    else:
        await update_binary_sensors()


async def update_binary_sensors():
    """Update all binary sensors."""
    for sensor in binary_sensors:
        _LOGGER.info(f"Updating binary sensor {sensor.name}")
        await sensor.async_update()
        sensor.async_schedule_update_ha_state(True)


def callback():
    """Callback for WebSocket updates."""
    pass


async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
):
    """Set up ezloPi binary sensors from a config entry."""
    hubInfo = hass.data[DOMAIN][entry.entry_id]["hubInfo"]
    _LOGGER.info('Setting up binary sensors for hub: {}'.format(hubInfo))
    
    # Listen for update events
    hass.bus.async_listen('update_all_sensors_and_switches', async_update_binary_sensors)
    await asyncio.sleep(5)

    for key, value in hubInfo.items():
        serial = key
        connection = value

        devices = await get_devices_from_platform(connection)
        global binary_sensors
        
        # Filter for binary sensor devices
        binary_sensors_local = [
            EzloBinarySensor(device, hass, connection, serial) 
            for device in devices 
            if device["type"] == "binary_sensor"
        ]
        
        _LOGGER.info('Found {} binary sensors'.format(len(binary_sensors_local)))
        
        # Log device detection for debugging
        for device in devices:
            if device["type"] == "binary_sensor":
                _LOGGER.debug(
                    f"Binary sensor '{device.get('name')}' - "
                    f"class: {device.get('deviceClass')}, "
                    f"value: {device.get('value')}"
                )
        
        async_add_entities(binary_sensors_local)
        connection.add_callback(callback)
        binary_sensors += binary_sensors_local
        
        # Store in hass.data for access from other components
        hass.data.setdefault('binary_sensors', []).extend(binary_sensors_local)


class EzloBinarySensor(BinarySensorEntity):
    """Representation of an ezloPi binary sensor."""
    
    def __init__(self, device, hass, connection, serial):
        """Initialize the binary sensor."""
        _LOGGER.info('Adding binary sensor {}:{}'.format(serial, device))
        
        self._hass = hass
        self._name = '{}_{}:'.format(serial, device["id"])
        
        if 'deviceName' in device:
            self._name += device["deviceName"] + ": " + device["name"]
        else:
            self._name = device["name"]
        
        self._serial = serial
        self._device_id = device["id"]
        self._state = device["value"]
        self.connection = connection
        self._device_name = device["name"]
        
        # Map device class string to BinarySensorDeviceClass
        device_class_str = device.get("deviceClass")
        self._attr_device_class = self._map_device_class(device_class_str)
        
        self._attributes = {
            "device_name": device.get("deviceName", ""),
            "device_type": device["type"],
            "hubDeviceId": device["deviceId"],
            "sensorId": self._device_id,
        }
        
        # Add category/subcategory if available
        if "category" in device:
            self._attributes["category"] = device["category"]
        if "subcategory" in device:
            self._attributes["subcategory"] = device["subcategory"]
        if "armed" in device:
            self._attributes["armed"] = device["armed"]
        
        self._unique_id = f"{self._serial}_{self._device_id}"
    
    def _map_device_class(self, device_class_str):
        """Map string device class to BinarySensorDeviceClass."""
        if not device_class_str:
            return None
            
        mapping = {
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
        
        return mapping.get(device_class_str)
    
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
        """Return the name of the binary sensor."""
        return self._name
    
    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        # Handle different value types that might come from ezloPi
        if isinstance(self._state, bool):
            return self._state
        elif isinstance(self._state, str):
            return self._state.lower() in ['on', 'true', '1', 'open', 'detected', 'motion']
        elif isinstance(self._state, (int, float)):
            return bool(self._state)
        else:
            # Default to off if we can't determine state
            return False
    
    @property
    def available(self):
        """Return True if entity is available."""
        return self._state is not None
    
    def get_device_name(self):
        """Get the device name."""
        return self._device_name
    
    def get_device_id(self):
        """Get the device ID."""
        return self._device_id
    
    async def test_connection(self):
        """Test connection to the device."""
        ip_address = self.connection.get_ip_address()
        if ip_address and not await ping_host(ip_address):
            self._state = None
    
    async def async_update(self):
        """Fetch new state data for this binary sensor."""
        try:
            self._state = await get_device_data(self._device_id, self.connection)
            _LOGGER.debug(f"Updated {self._name} state to: {self._state}")
            
            # Update battery level if available (for battery-powered sensors)
            battery_level = get_device_battery_level(self._device_id, self.connection)
            if battery_level is not None:
                self._attributes["battery_level"] = battery_level
                self._attributes["battery_powered"] = True
                
        except Exception as e:
            _LOGGER.error(f"Error updating {self._name}: {e}")
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes