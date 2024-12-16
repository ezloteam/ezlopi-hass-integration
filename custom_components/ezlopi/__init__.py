"""The EzloPI component."""
import logging
import asyncio
import subprocess
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, EZLOPI_API, WS_API, LOCK
from .ezlopi_utils import EzloCloudAPI
from .ws_api import WsApi

_LOGGER = logging.getLogger(__name__)

SUPPORTED_DOMAINS = ['sensor', 'switch']
PLATFORMS: list[Platform] = [
    # Platform.BINARY_SENSOR,
    # Platform.CLIMATE,
    # Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    config = entry.data
    device_registry = dr.async_get(hass)

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    

    _LOGGER.info(f"{CONF_USERNAME}: {username}")
    ws_api = hass.data[DOMAIN][WS_API]
    lock =  hass.data[DOMAIN][LOCK]

    async with lock:
        if(entry.entry_id in hass.data[DOMAIN][EZLOPI_API]):
            _LOGGER.error('{} already configed'.format(username))
            return False
        ezlopi_api = EzloCloudAPI(username=username, password=password)
        hass.data[DOMAIN][EZLOPI_API][entry.entry_id] = ezlopi_api
    await ezlopi_api.fetch_hub_list()
    
    for key, hub in ezlopi_api.get_hub_list().items():
        ws_api.connect(hub.serial, hub.token)
        if not ws_api.is_connected(hub.serial):
            _LOGGER.error(f"Failed to connect to hub {hub.serial}.")
            continue

        _LOGGER.warning('we will add device:{}'.format({(DOMAIN, hub.serial)}))
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, hub.serial)},
            manufacturer="ezloPi",
            model="ezloPi ESP32",
            name=f"ezloPi {hub.serial}",
            sw_version="1.0"
        )

        for serial, value in ws_api.get_connections().items():
            if(serial == hub.serial):
                _LOGGER.info(f"New hub {serial} connected value: {value}")
                try:
                    await register_platforms(hass, key, value, entry)
                except Exception as err:
                    _LOGGER.exception('register_platforms err:[' + str(err) + ']')
    return True

async def async_unload_entry(hass, entry) -> bool:
    _LOGGER.info(f"async_unload_entry: {entry}")
    config = entry.data
    username = config.get(CONF_USERNAME)
    ws_api = hass.data[DOMAIN][WS_API]
    lock = hass.data[DOMAIN][LOCK]
    
    if(username == None):
        _LOGGER.error('{} not exist'.format(username))
        return False

    async with lock:
        ezlopi_api = hass.data[DOMAIN][EZLOPI_API].get(entry.entry_id)
    
        if(ezlopi_api != None):
            for key, hub in ezlopi_api.get_hub_list().items():
                ws_api.remove_connection(hub.serial)
            hass.data[DOMAIN][EZLOPI_API].pop(entry.entry_id)

    try:
        unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        return unloaded
    except Exception as err:
        _LOGGER.exception('async_unload_entry err:[' + str(err) + ']')
        unloaded = False
    return unloaded

async def async_setup(hass: HomeAssistant, config):
    _LOGGER.info('start mDNS discovery')
    ws_api = WsApi()
    hass.data[DOMAIN] = {WS_API: ws_api, EZLOPI_API: {}, 'lock': asyncio.Lock()}
    await ws_api.async_init(hass)
    hass.loop.create_task(monitor_connections(hass, config))
    _LOGGER.info("Global monitor_connections task has been created.")

    return True

async def register_platforms(hass, serial, ws_connection, entry=None):
    info = {serial: ws_connection}
    if(entry != None):
        if(entry.entry_id not in hass.data[DOMAIN]):
            hass.data[DOMAIN][entry.entry_id] = {}
        hass.data[DOMAIN][entry.entry_id]['hubInfo'] = info
        try:
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        except Exception as err:
            _LOGGER.exception('register_platforms err:[' + str(err) + ']')

async def ping_host(ip_address):
    try:
        response = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip_address],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return response.returncode == 0
    except Exception as e:
        _LOGGER.error(f"Error during ping: {e}")
        return False

async def monitor_connections_impl(hass, ws_api, lock):
    try:
        # for serial in list(ws_api.get_connections().keys()):
        #     ip_address = ws_api.get_connection_ip(serial)
        #     if not ip_address:
        #         _LOGGER.error(f"IP address not found for serial {serial}.")
        #         continue

        #     if not await ping_host(ip_address):
        #         ping_failures[serial] = ping_failures.get(serial, 0) + 1
        #         _LOGGER.warning(f"Ping failed for hub {serial}. Failure count: {ping_failures[serial]}")

        #         if ping_failures[serial] >= 5:
        #             _LOGGER.warning(f"Hub {serial} considered disconnected after 5 failed pings.")
        #     else:
        #         ping_failures[serial] = 0

        for serial, ws_connection in ws_api.get_connections().items():
            try:
                if(ws_connection.is_open()):
                    ws_connection.send_serial_log_enable_message()
                    ws_connection.send_some_query_params()
            except Exception as err:
                _LOGGER.exception('sync err:[' + str(err) + ']')
            
        
        _LOGGER.debug(ws_api.get_connection_links())
        for serial, websocket_address in ws_api.get_connection_links().items():
            if serial not in ws_api.get_connections():
                _LOGGER.debug('handle serial:{}'.format(serial))
                async with lock:
                    for entry_id, ezlopi_api in hass.data[DOMAIN][EZLOPI_API].items():
                        await ezlopi_api.fetch_hub_list()
                        for key, hub in ezlopi_api.get_hub_list().items():
                            if(hub.serial == serial):
                                _LOGGER.info('try to connect to {}'.format(websocket_address))
                                ws_connection = ws_api.connect(hub.serial, hub.token)
                                if ws_api.is_connected(hub.serial):
                                    _LOGGER.info(f"New hub {hub.serial} connected.")
                                    entry = hass.config_entries.async_get_entry(entry_id)
                                    await register_platforms(hass, hub.serial, ws_connection, entry=entry)
                                else:
                                    _LOGGER.error(f"Failed to connect to hub {hub.serial}.")
                                break
    except Exception as err:
        _LOGGER.exception('monitor_connections err:[' + str(err) + ']')

async def monitor_connections(hass, config):
    _LOGGER.info("monitor_connections thread has started.")
    # ping_failures = {}
    ws_api = hass.data[DOMAIN][WS_API]
    lock = hass.data[DOMAIN][LOCK]

    while True:
        await asyncio.sleep(5)
        await monitor_connections_impl(hass, ws_api, lock)
