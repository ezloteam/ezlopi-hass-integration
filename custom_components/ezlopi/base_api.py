import logging

_LOGGER = logging.getLogger(__name__)

class BaseApi:
    def get_items(self, connector):
        pass

    def get_devices(self, connector):
        pass

    def set_item_value(self, id, value, connector):
        pass

    def set_dimmer(self, value, connector):
        pass