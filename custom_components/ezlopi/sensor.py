from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .utils import *
import logging
import asyncio
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

sensors = []

async def async_update_sensors(event):
    event_data = event.data
    sensor_id = event_data.get('id', None)

    if sensor_id:
        for sensor in sensors:
            if sensor.get_device_id() == sensor_id:
                await sensor.async_update()
                sensor.async_schedule_update_ha_state(True)
    else:
        await update_sensors()


async def update_sensors():
    for sensor in sensors:
        _LOGGER.info(f"Updating sensor {sensor.name}")
        await sensor.async_update()
        sensor.async_schedule_update_ha_state(True)

def callback():
    pass

# async def update_sensors():
#     for sensor in sensors:
#         await sensor.async_update()
#         asyncio.create_task(sensor.async_schedule_update_ha_state(True))

# async def async_setup_platform(hass, config, async_add_entities, hubInfo):
#     _LOGGER.info('async_setup_platform:{} {} {}'.format(config, async_add_entities, hubInfo))
#     await asyncio.sleep(5)
#     hass.bus.async_listen('update_all_sensors_and_switches', async_update_sensors)

#     for key, value in hubInfo.items():
#         serial = key
#         connection = value

#         devices = await get_devices_from_platform(connection)
#         global sensors
#         sensors_local = [EzloSensor(device, hass, connection, serial) for device in devices if device["type"] == "sensor"]
#         _LOGGER.info('sensors_local is {}'.format(sensors_local))
#         async_add_entities(sensors_local)
#         connection.add_callback(callback)
#         sensors += sensors_local
#         hass.data['sensors'] = sensors

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hubInfo = hass.data[DOMAIN][entry.entry_id]["hubInfo"]
    _LOGGER.info('async_setup_platform:{}, {}'.format(async_add_entities, hubInfo))
    hass.bus.async_listen('update_all_sensors_and_switches', async_update_sensors)
    await asyncio.sleep(5)

    for key, value in hubInfo.items():
        serial = key
        connection = value

        devices = await get_devices_from_platform(connection)
        global sensors
        sensors_local = [EzloSensor(device, hass, connection, serial) for device in devices if device["type"] == "sensor"]
        _LOGGER.info('sensors_local is {}'.format(sensors_local))
        # Log device detection for debugging
        for device in devices:
            _LOGGER.debug(f"Device '{device.get('name')}' detected as platform: {device.get('type')}, class: {device.get('deviceClass')}")
        async_add_entities(sensors_local)
        connection.add_callback(callback)
        sensors += sensors_local
        hass.data['sensors'] = sensors

class EzloSensor(SensorEntity):
    def __init__(self, device, hass, connection, serial):
        _LOGGER.info('we will add {}:{}'.format(serial, device))

        self._hass = hass
        self._name = serial + ": "
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
        self._attr_device_class = self._map_device_class(device.get("deviceClass"))
        self._attr_unit_of_measurement = device["unitOfMeasurement"]
        
        # Set state class for battery sensors
        if self._attr_device_class == SensorDeviceClass.BATTERY:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        
        self._attributes = {
            "device_name": device["deviceName"],
            "device_type": device["type"],
            "hubDeviceId": device["deviceId"],
            "sensorId": self._device_id,
            "unit_of_measurement": device["unitOfMeasurement"],
        }
        
        # Check if this is a battery sensor and add battery status
        if self._attr_device_class == SensorDeviceClass.BATTERY:
            self._attributes["battery_status"] = self._get_battery_status(device.get("value"))
        
        self._unique_id = f"{self._serial}_{self._device_id}"
    
    @property
    def unique_id(self):
        return self._unique_id
    
    @property
    def device_info(self):
        """Return device information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._serial)},
        }

    def get_device_name(self):
        return self._device_name

    def get_device_id(self):
        return self._device_id

    async def rebuild_platform(self):
        await self._hass.services.async_call("custom_component", "rebuild_platform")

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    async def test_connection(self):
        ip_address = self.connection.get_ip_address()
        if not await ping_host(ip_address):
            self._state = None

    async def async_update(self):
        # self.connection.send_serial_log_enable_message()
        # self.connection.send_some_query_params()
        self._state = await get_device_data(self._device_id, self.connection)

    @property
    def extra_state_attributes(self):
        return self._attributes
    
    def _map_device_class(self, device_class_str):
        """Map string device class to SensorDeviceClass enum."""
        if not device_class_str:
            return None
            
        mapping = {
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
        
        return mapping.get(device_class_str, None)
    
    def _get_battery_status(self, battery_level):
        """Get battery status description based on level."""
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
    def icon(self):
        """Return the icon to use in the frontend."""
        if self._attr_device_class == SensorDeviceClass.BATTERY:
            level = self.state
            try:
                level = float(level) if level is not None else 0
                if level >= 95:
                    return "mdi:battery"
                elif level >= 85:
                    return "mdi:battery-90"
                elif level >= 75:
                    return "mdi:battery-80"
                elif level >= 65:
                    return "mdi:battery-70"
                elif level >= 55:
                    return "mdi:battery-60"
                elif level >= 45:
                    return "mdi:battery-50"
                elif level >= 35:
                    return "mdi:battery-40"
                elif level >= 25:
                    return "mdi:battery-30"
                elif level >= 15:
                    return "mdi:battery-20"
                elif level >= 5:
                    return "mdi:battery-10"
                elif level > 0:
                    return "mdi:battery-alert"
                else:
                    return "mdi:battery-unknown"
            except (ValueError, TypeError):
                return "mdi:battery-unknown"
        
        return None
