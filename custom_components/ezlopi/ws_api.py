from .base_api import BaseApi
import logging

from .ws_connector import WebsocketConnector
from .mdns_connector import EzloPiMDSConnector

_LOGGER = logging.getLogger(__name__)

class WsApi(BaseApi):
    def __init__(self):
        self.browser = EzloPiMDSConnector()
        self.connections = {}

    async def async_init(self, hass):
        await self.browser.async_init(hass)
        await self.browser.async_get_service_info()
        self.hass = hass

    def connect(self, login, password):
        websocket_link = self.browser.get_connection_link_from_serial(login)
        if websocket_link is not None:
            connector = WebsocketConnector(websocket_link, login, password, self.hass)
            if connector is not None:
                connector.start()
                self.connections[login] = connector
                return connector
        return None

    def is_connected(self, serial):
        connector = self.connections.get(serial)
        if connector:
            return True
        return False

    def get_connections(self):
        return self.connections

    def remove_connection(self, serial):
        if serial in self.connections:
            self.connections[serial].close()
            del self.connections[serial]
        else:
            _LOGGER.warning(f"Attempt to remove non-existent connection for serial: {serial}")

    def get_connection_ip(self, serial):
        return self.connections[serial].get_ip_address()
    
    def get_connection_links(self):
        return self.browser.get_connection_links()
