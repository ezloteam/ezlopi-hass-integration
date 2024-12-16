import asyncio
from tabulate import tabulate
from homeassistant.components.zeroconf import async_get_instance
from zeroconf import ServiceListener, ServiceBrowser, ZeroconfServiceTypes
import logging

_LOGGER = logging.getLogger(__name__)

class EzloPiMDSConnector(ServiceListener):
    def __init__(self, service='_ezlo', proto='_tcp') -> None:
        self.service = service
        self.proto = proto
        self.type = f'{self.service}.{self.proto}.local.'
        self.zc = None  # Zeroconf instance will be assigned later
        self.service_dict = dict()
        self.service_size = 0

    async def async_init(self, hass):
        self.zc = await async_get_instance(hass)


    # If services are updated, refer to ServiceListener
    def update_service(self, zc, type_: str, name: str) -> None:
        _LOGGER.info(f"Service {name} updated")

    # If services are removed, refer to ServiceListener
    def remove_service(self, zc, type_: str, name: str) -> None:
        _LOGGER.info(f"Service {name} removed")

    # If services are added, process the service info and set values in a dictionary
    def add_service(self, zc, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        info_dict = dict()
        info_dict['type'] = info.type
        info_dict['name'] = info.name
        info_dict['address'] = info.parsed_addresses()
        info_dict['port'] = info.port
        info_dict['server'] = info.server
        info_dict['properties'] = {key.decode('utf-8'): value.decode('utf-8') for key, value in info.properties.items()}
        info_dict['interface_index'] = info.interface_index
        self.service_dict[name] = info_dict
        _LOGGER.info('got new service {}'.format(self.service_dict[name]))

    async def async_get_service_info(self):
        await asyncio.sleep(2)
        _LOGGER.info(f"Autodiscover devices...")
        self.browser = ServiceBrowser(zc=self.zc, type_=self.type, listener=self)

        try:
            for i in range(1, 3):
                _LOGGER.info(f"Progress: {i * 10}%")
                await asyncio.sleep(1)
        finally:
            _LOGGER.info(f"Service discovery complete.")

    def get_serial(self, data):
        properties = data.get('properties', {})
        serial = properties.get('Serial')

        if not serial:
            raise KeyError("Key 'Serial' is missing in 'properties'.")

        return serial

    def get_connection_link_from_serial(self, serial=None):
        if serial is None:
            raise ValueError('Expected serial but got None')

        for key, value in self.service_dict.items():
            if self.get_serial(value) == serial:
                # _LOGGER.debug(f'Selected EzloPI PI device: {value}')
                websocket_address = f'ws://{value["address"][0]}:{value["port"]}'
                return websocket_address

        _LOGGER.error(f"Link by serial: [{serial}] is not defined")
        return None
    
    def get_connection_links(self):
        connection_links = {}
        for key, value in self.service_dict.items():
            serial = self.get_serial(value)
            # _LOGGER.debug(f'Selected EzloPI PI device: {value}')
            websocket_address = f'ws://{value["address"][0]}:{value["port"]}'
            connection_links[serial] = websocket_address
        return connection_links

    async def discover_advertised_service_types(self):
        self.discovered_service_types = ZeroconfServiceTypes.find()
        self.all_services = [[item for item in service if item] for service in
                             [service_type.split('.') for service_type in self.discovered_service_types]]
        _LOGGER.info(
            f"Discovered services:\n{tabulate(self.all_services, headers=['service', 'protocol', 'domain'], tablefmt='mixed_grid')}")