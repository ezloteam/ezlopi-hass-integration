import aiohttp
import asyncio
import logging
from typing import Dict
from .const import EZLOPI_API_URL_BASE

_LOGGER = logging.getLogger(__name__)


class EzloPIHubInfo:
    def __init__(self, serial: str, token: str, name: str):
        self.serial = serial
        self.token = token
        self.name = name

class EzloCloudAPI:
    def __init__(self, username: str, password: str):
        """
        Initialize with username and password.
        """
        self.username = username
        self.password = password
        self.token = None
        self.hub_list: Dict[str, EzloPIHubInfo] = {}
        self._lock = asyncio.Lock()

    async def __login(self):
        """
        Asynchronously login to the Ezlo Cloud API to retrieve a token.
        """
        login_url = EZLOPI_API_URL_BASE
        headers = {"Content-type": "application/json"}
        login_data = {
            "call": "login_with_id_and_password",
            "params": {
                "user_id": self.username,
                "user_password": self.password
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(login_url, headers=headers, json=login_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("data") and result["data"].get("token"):
                            self.token = result["data"]["token"]
                            _LOGGER.info("Login successful!")
                            return True
                        _LOGGER.error("Login failed: Token not received")
                    _LOGGER.error(f"Login failed: HTTP {response.status}")
        except Exception as err:
            _LOGGER.exception('login err:[' + str(err) + ']')
        return False
        

    async def fetch_hub_list(self):
        """
        Asynchronously fetch the list of hubs associated with the account using the token.
        """
        await self.__login()
        if not self.token:
            _LOGGER.error("Token is missing. Please login first.")
            return False

        controller_list_url = EZLOPI_API_URL_BASE
        headers_with_token = {
            "Content-type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        controller_list_data = {
            "call": "controller_list",
            "params": {
                "local_key": 1
            }
        }

        try:
            async with self._lock:
                async with aiohttp.ClientSession() as session:
                    async with session.post(controller_list_url, headers=headers_with_token, json=controller_list_data) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("data") and result["data"].get("controllers"):
                                self.hub_list = {}
                                for hub in result["data"]["controllers"]:
                                    serial = hub['serial']
                                    if(serial != None and serial != ''):
                                        self.hub_list[serial] = EzloPIHubInfo(serial=serial, token=hub['uuid'], name=hub['name'])
                                _LOGGER.info("Hub list fetched successfully:{}".format(self.hub_list))
                                return True
                            _LOGGER.error("Hub list not found in the response")
                        _LOGGER.error(f"Failed to fetch hub list: HTTP {response.status}")
        except Exception as err:
            _LOGGER.exception('fetch hub list err:[' + str(err) + ']')
        return False

    def get_hub_list(self) -> Dict[str, EzloPIHubInfo]:
        """
        Return the list of hubs.
        """
        return self.hub_list
