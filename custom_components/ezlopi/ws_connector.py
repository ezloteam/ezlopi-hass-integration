import threading
import websocket
from .utils import *

import logging
_LOGGER = logging.getLogger(__name__)

class WebsocketConnector(websocket.WebSocketApp):
    def __init__(self, url, login, password, hass) -> None:
        self.answers = []
        self.items = []
        self.devices = []
        self.callbacks = []
        self.url = url

        self.login_params = get_login_params()
        self.login_params["params"]["user"] = login
        self.login_params["params"]["token"] = password

        self.hass = hass

        self.system_logging_param = get_login_params()
        self.get_devices_info = get_devices_info()

        self.logged_in = False
        websocket.enableTrace = True
        super().__init__(url=url, on_message=self.on_message, on_open=self.on_open, on_error=self.on_error, on_close=self.on_close)

    def start(self):
        _LOGGER.info(f'Starting WebSocket connection to {self.url}')
        thread = threading.Thread(target=self.run_forever, kwargs={'reconnect': 5})
        thread.daemon = True
        thread.start()

    def on_open(self, ws):
        _LOGGER.info(f'[{ws}] websocket connected')
        self.connection_open = True
        self.send_login_message()

    def on_error(self, ws, error):
        _LOGGER.info(f'[{ws}] Error received:  {error}')

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def on_message(self, ws, message):
        if not self.logged_in:
            self.process_login_message(message)

        _LOGGER.debug(f'[{ws}]RECEIVE <<<<  {message}\n')

        json_data = json.loads(message)
        if json_data["id"] != "ui_broadcast":
            self.get_devices_and_items_in_answers(json_data)
        else:
            self.check_and_update_items(json_data)


    def check_and_update_items(self, json_data):
        if json_data["msg_subclass"] == "hub.item.updated":
            result = json_data["result"]
            self.change_item_value(result["_id"], result["value"])
            if self.hass:
                self.hass.bus.fire('update_all_sensors_and_switches', {'id':result["_id"]})

    def get_devices_and_items_in_answers(self, json_data):
        items = self.find_answer("items", json_data)
        if items != '':
            self.items = items
        devices = self.find_answer("devices", json_data)
        if devices != '':
            self.devices = devices

    def find_answer(self, name, data):
        result = data["result"]
        if name in result:
            return result[name]
        return ''

    def change_item_value(self, id, value):
        _LOGGER.info(f'change_item_value id: {id} value: {value}')
        items_updated = []
        for item in self.items:
            if item["_id"] == id:
                item["value"] = value
            items_updated.append(item)
        self.items = items_updated

    def on_close(self, ws, close_status_code, close_msg):
        _LOGGER.info(f'[{ws}] Closing websocket code: {close_status_code}, message: {close_msg} ')
        self.connection_open = False

    def send_message(self, message):
        self.send(message)
        _LOGGER.debug(f"SEND >>>> {message}")

    def process_login_message(self, message):
        login_response = json.loads(message)
        if 'method' in login_response.keys() and self.login_params['method'] == login_response['method']:
            self.logged_in = True
            _LOGGER.info(f'Logged successfully')
            self.send_serial_log_enable_message()
            self.send_some_query_params()

    def send_serial_log_enable_message(self):
        self.send_message(json.dumps(self.system_logging_param))

    def send_login_message(self):
        self.send_message(json.dumps(self.login_params))

    def send_some_query_params(self):
        for query_param in self.get_devices_info:
            self.send_message(json.dumps(query_param))

    def is_open(self):
        return self.connection_open

    def get_ip_address(self):
        from urllib.parse import urlparse
        import socket

        parsed_url = urlparse(self.url)
        hostname = parsed_url.hostname
        try:
            ip_address = socket.gethostbyname(hostname)
            return ip_address
        except socket.error as e:
            _LOGGER.error(f"Could not resolve IP for {hostname}: {e}")
            return None