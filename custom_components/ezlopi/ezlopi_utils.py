import aiohttp
import asyncio
import logging
from typing import Dict
from .const import EZLOPI_CONTROLLER_LIST_URL, EZLOPI_LOGIN_URL

_LOGGER = logging.getLogger(__name__)


class EzloAuthError(Exception):
    """Credentials were rejected by the Ezlo cloud."""


class EzloConnectionError(Exception):
    """The Ezlo cloud could not be reached (transient/network failure)."""


class EzloPIHubInfo:
    def __init__(self, serial: str, token: str | None, name: str) -> None:
        self.serial = serial
        self.token = token
        self.name = name

class EzloCloudAPI:
    def __init__(self, username: str, password: str, session: aiohttp.ClientSession) -> None:
        """Initialize with credentials and a shared (HA-injected) aiohttp session."""
        self.username = username
        self.password = password
        self._session = session
        self.token = None
        self.hub_list: Dict[str, EzloPIHubInfo] = {}
        self._lock = asyncio.Lock()

    async def __login(self) -> bool:
        """
        Asynchronously login to the Ezlo Cloud API to retrieve a token.

        Uses the v4 REST login endpoint, which takes the credentials directly
        and returns the JWT at the top level ({"token": ...}). The minted JWT
        is accepted by the legacy /v1/request gateway for subsequent calls
        (e.g. controller_list).
        """
        login_url = EZLOPI_LOGIN_URL
        headers = {"Content-type": "application/json"}
        login_data = {
            "user_id": self.username,
            "user_password": self.password
        }

        try:
            async with self._session.post(login_url, headers=headers, json=login_data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("token"):
                        self.token = result["token"]
                        _LOGGER.info("Login successful!")
                        return True
                    _LOGGER.error("Login failed: token not received")
                    raise EzloAuthError("No token in login response")
                if response.status in (400, 401, 403):
                    _LOGGER.error(f"Login rejected: HTTP {response.status}")
                    raise EzloAuthError(f"Credentials rejected (HTTP {response.status})")
                _LOGGER.error(f"Login failed: HTTP {response.status}")
                raise EzloConnectionError(f"Login failed (HTTP {response.status})")
        except aiohttp.ClientError as err:
            _LOGGER.error('login connection err:[' + str(err) + ']')
            raise EzloConnectionError(str(err)) from err
        

    async def fetch_hub_list(self) -> bool:
        """
        Asynchronously fetch the list of hubs associated with the account using the token.
        """
        await self.__login()
        if not self.token:
            _LOGGER.error("Token is missing. Please login first.")
            return False

        # v4 REST: GET with the JWT in x-access-token; controllers are returned
        # at the top level (no {"data": ...} envelope). `local_key=1` asks the
        # service to include the hub's local access key.
        controller_list_url = EZLOPI_CONTROLLER_LIST_URL + "?local_key=1"
        headers_with_token = {
            "Content-type": "application/json",
            "x-access-token": self.token
        }

        try:
            async with self._lock:
                async with self._session.get(controller_list_url, headers=headers_with_token) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("controllers"):
                            self.hub_list = {}
                            for hub in result["controllers"]:
                                serial = hub['serial']
                                if(serial != None and serial != ''):
                                    # Use the hub's local_key as the local
                                    # hub.offline.login.ui token — this is what
                                    # the firmware enforces once updated.
                                    token = hub.get('local_key')
                                    self.hub_list[serial] = EzloPIHubInfo(serial=serial, token=token, name=hub['name'])
                            _LOGGER.info("Hub list fetched successfully:{}".format(self.hub_list))
                            return True
                        _LOGGER.error("Hub list not found in the response")
                    else:
                        _LOGGER.error(f"Failed to fetch hub list: HTTP {response.status}")
        except aiohttp.ClientError as err:
            _LOGGER.error('fetch hub list connection err:[' + str(err) + ']')
            raise EzloConnectionError(str(err)) from err
        return False

    def get_hub_list(self) -> Dict[str, EzloPIHubInfo]:
        """
        Return the list of hubs.
        """
        return self.hub_list
