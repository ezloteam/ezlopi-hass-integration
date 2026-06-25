"""Lock platform for ezloPi integration."""
from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .utils import *
import logging
import asyncio
import time
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

locks = []

async def async_update_locks(event):
    """Handle update events for locks."""
    event_data = event.data
    lock_id = event_data.get('id', None)

    if lock_id:
        for lock in locks:
            if lock.get_device_id() == lock_id:
                await lock.async_update()
                lock.async_schedule_update_ha_state(True)
    else:
        await update_locks()


async def update_locks():
    """Update all locks."""
    for lock in locks:
        _LOGGER.info(f"Updating lock {lock.name}")
        await lock.async_update()
        lock.async_schedule_update_ha_state(True)


def callback():
    """Callback for WebSocket updates."""
    pass


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    """Set up ezloPi locks from a config entry."""
    hubInfo = hass.data[DOMAIN][entry.entry_id]["hubInfo"]
    _LOGGER.info('Setting up locks for hub: {}'.format(hubInfo))
    
    # Listen for update events
    hass.bus.async_listen('update_all_sensors_and_switches', async_update_locks)
    await asyncio.sleep(5)

    for key, value in hubInfo.items():
        serial = key
        connection = value

        devices = await get_devices_from_platform(connection)
        global locks
        
        # Filter for lock devices
        locks_local = [
            EzloLock(device, hass, connection, serial)
            for device in devices
            if device["type"] == "lock"
        ]
        
        _LOGGER.info('Found {} locks'.format(len(locks_local)))
        
        # Log device detection for debugging
        for device in devices:
            if device["type"] == "lock":
                _LOGGER.debug(
                    f"Lock '{device.get('name')}' - "
                    f"class: {device.get('deviceClass')}, "
                    f"value: {device.get('value')}"
                )
        
        async_add_entities(locks_local)
        connection.add_callback(callback)
        locks += locks_local
        
        # Store in hass.data for access from other components
        hass.data.setdefault('locks', []).extend(locks_local)


class EzloLock(LockEntity):
    """Representation of an ezloPi lock."""
    
    def __init__(self, device, hass, connection, serial):
        """Initialize the lock."""
        _LOGGER.info('Adding lock {}:{}'.format(serial, device))
        
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
        
        # Initialize lock state
        value = device.get("value")
        if isinstance(value, bool):
            self._is_locked = value
        elif isinstance(value, str):
            # Handle string values like "locked", "unlocked"
            self._is_locked = value.lower() in ['locked', 'true', '1']
        elif isinstance(value, (int, float)):
            # Non-zero values mean locked
            self._is_locked = bool(value)
        else:
            # Default to unlocked if unknown
            self._is_locked = False
        
        # Check if lock supports codes
        self._supports_codes = device.get("supportsUserCodes", False)
        
        # Set supported features
        self._attr_supported_features = LockEntityFeature(0)
        if self._supports_codes:
            # Add support for open if lock supports codes
            self._attr_supported_features |= LockEntityFeature.OPEN
        
        self._timing = 0
        
        self._attributes = {
            "device_name": device.get("deviceName", ""),
            "device_type": device["type"],
            "hubDeviceId": device["deviceId"],
            "lockId": self._device_id,
        }
        
        # Add category/subcategory if available
        if "category" in device:
            self._attributes["category"] = device["category"]
        if "subcategory" in device:
            self._attributes["subcategory"] = device["subcategory"]
        
        # Add battery level if available
        if "battery" in device:
            self._attributes["battery_level"] = device["battery"]
        
        # Add tamper status if available
        if "tamper" in device:
            self._attributes["tamper_detected"] = device["tamper"]
        
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
        """Return the name of the lock."""
        return self._name
    
    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self._is_locked
    
    @property
    def available(self):
        """Return True if entity is available."""
        return True
    
    async def async_lock(self, **kwargs):
        """Lock the lock."""
        await self.set_lock_state(True)
        self._is_locked = True
        self.async_write_ha_state()
        self._timing = time.time()
        _LOGGER.info(f"Locked {self._name}")
    
    async def async_unlock(self, **kwargs):
        """Unlock the lock."""
        await self.set_lock_state(False)
        self._is_locked = False
        self.async_write_ha_state()
        self._timing = time.time()
        _LOGGER.info(f"Unlocked {self._name}")
    
    async def async_open(self, **kwargs):
        """Open the lock (if supported)."""
        if self._attr_supported_features & LockEntityFeature.OPEN:
            # Send open command (typically for locks with auto-close)
            await self.set_lock_state(False, action="open")
            self._is_locked = False
            self.async_write_ha_state()
            self._timing = time.time()
            _LOGGER.info(f"Opened {self._name}")
        else:
            _LOGGER.warning(f"Lock {self._name} does not support open")
    
    def get_device_name(self):
        """Get the device name."""
        return self._device_name
    
    def get_device_id(self):
        """Get the device ID."""
        return self._device_id
    
    async def set_lock_state(self, locked, action=None):
        """Set the lock to a specific state."""
        # Determine the value to send
        if action == "open":
            # Special handling for open command
            value = "open"
        else:
            # Standard lock/unlock
            value = locked
        
        request = set_item_value_request(self._device_id, value)
        self.connection.send_message(json.dumps(request))
        _LOGGER.debug(f"Set {self._name} to {'locked' if locked else 'unlocked'}")
    
    async def test_connection(self):
        """Test connection to the device."""
        ip_address = self.connection.get_ip_address()
        if ip_address and not await ping_host(ip_address):
            # If connection lost, assume unknown state
            self._is_locked = None
    
    async def async_update(self):
        """Fetch new state data for this lock."""
        # Don't update immediately after setting value (avoid race condition)
        if time.time() - self._timing > 3.0:
            try:
                value = await get_device_data(self._device_id, self.connection)
                
                if isinstance(value, bool):
                    self._is_locked = value
                elif isinstance(value, str):
                    # Handle string values
                    value_lower = value.lower()
                    if value_lower in ['locked', 'unlocked']:
                        self._is_locked = value_lower == 'locked'
                    elif value_lower in ['true', 'false']:
                        self._is_locked = value_lower == 'true'
                    elif value_lower in ['1', '0']:
                        self._is_locked = value_lower == '1'
                    else:
                        _LOGGER.warning(f"Unknown lock state value: {value}")
                elif isinstance(value, (int, float)):
                    # Non-zero means locked
                    self._is_locked = bool(value)
                else:
                    _LOGGER.warning(f"Unexpected lock value type: {type(value)}")
                
                _LOGGER.debug(f"Updated {self._name} - locked: {self._is_locked}")
                
                # Update battery level if available
                battery_level = get_device_battery_level(self._device_id, self.connection)
                if battery_level is not None:
                    self._attributes["battery_level"] = battery_level
                    self._attributes["battery_status"] = self._get_battery_status(battery_level)
                
            except Exception as e:
                _LOGGER.error(f"Error updating {self._name}: {e}")
    
    def _get_battery_status(self, battery_level):
        """Get battery status description."""
        if battery_level is None:
            return "unknown"
        
        try:
            level = float(battery_level)
            if level > 75:
                return "good"
            elif level > 50:
                return "fair"
            elif level > 25:
                return "low"
            elif level > 10:
                return "critical"
            else:
                return "very_low"
        except (ValueError, TypeError):
            return "unknown"
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes