from homeassistant.helpers.entity import ToggleEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import logging
import time
from .const import DOMAIN
from .utils import *

_LOGGER = logging.getLogger(__name__)
sensors = []

switches = []

def callback():
    pass

async def async_update_switches(event):
    event_data = event.data
    switch_id = event_data.get('id', None)

    if switch_id:
        for switch in switches:
            if switch.get_device_id() == switch_id:
                await switch.async_update()
                switch.async_schedule_update_ha_state(True)
    else:
        await update_switches()


async def update_switches():
    for switch in switches:
        _LOGGER.info(f"Updating switch {switch.name}")
        await switch.async_update()
        switch.async_schedule_update_ha_state(True)


# async def async_setup_platform(hass, config, async_add_entities, hubInfo):
#     hass.bus.async_listen('update_all_sensors_and_switches', async_update_switches)
#     for key, value in hubInfo.items():
#         serial = key
#         connection = value

#     devices = await get_devices_from_platform(connection)
#     global switches
#     switches_local = [EzloSwitch(device, hass, connection, serial) for device in devices if device["type"] == "switch"]
#     async_add_entities(switches_local)
#     connection.add_callback(callback)

#     switches += switches_local

#     global sensors
#     sensors = hass.data.get('sensors', [])

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hubInfo = hass.data[DOMAIN][entry.entry_id]["hubInfo"]
    _LOGGER.info('async_setup_platform:{}, {}'.format(async_add_entities, hubInfo))
    hass.bus.async_listen('update_all_sensors_and_switches', async_update_switches)
    await asyncio.sleep(5)

    for key, value in hubInfo.items():
        serial = key
        connection = value

        devices = await get_devices_from_platform(connection)
        global switches
        switches_local = [EzloSwitch(device, hass, connection, serial) for device in devices if device["type"] == "switch"]
        _LOGGER.info('switches_local is {}'.format(switches_local))
        async_add_entities(switches_local)
        connection.add_callback(callback)
        switches += switches_local
        
        global sensors
        sensors = hass.data.get('sensors', [])

class EzloSwitch(ToggleEntity):
    def __init__(self, device, hass, connection, serial):
        _LOGGER.info('we will add {}:{}'.format(serial, device))
        
        self._hass = hass
        self._name = '{}_{}:'.format(serial, device["id"])
        if 'deviceName' in device:
            self._name += device["deviceName"] + ": " + device["name"]
        else:
            self._name = device["name"]

        self._serial = serial
        self._name_internal = device["deviceName"]
        self._device_name = device["name"]
        self._device_id = device["id"]
        self._state = device["value"]
        self._hasSetter = device["hasSetter"]
        self._timing = 0
        self.connection = connection
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

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state == "on"

    @property
    def available(self):
        return self._hasSetter

    async def async_turn_on(self, **kwargs):
        await self.set_item_value(self._device_id, True)
        self._state = "on"
        self.async_write_ha_state()
        self._timing = time.time()

    async def async_turn_off(self, **kwargs):
        await self.set_item_value(self._device_id, False)
        self._state = "off"
        self.async_write_ha_state()
        self._timing = time.time()

    def get_device_name(self):
        return self._device_name

    def get_device_id(self):
        return self._device_id

    def set_dimmer(self, value):
        value_item_id = ""
        for sensor in sensors:
            name = sensor.get_device_name()
            if sensor.get_device_name() == "dimmer":
                value_item_id = sensor.get_device_id()

        dimmer_value = 0
        if value == True:
            dimmer_value = 100

        request = set_item_value_request(value_item_id, dimmer_value)
        self.connection.send_message(json.dumps(request))

        return {}

    async def set_item_value(self, device_id, value):
        if self._name_internal == "Dimmer":
            self.set_dimmer(value)
        else:
            request = set_item_value_request(device_id, value)
            self.connection.send_message(json.dumps(request))

    async def test_connection(self):
        ip_address = self.connection.get_ip_address()
        if not await ping_host(ip_address):
            self._state = None

    async def async_update(self):
     if time.time() - self._timing > 3.0:
        value = await get_device_data(self._device_id, self.connection)
        self._state = value