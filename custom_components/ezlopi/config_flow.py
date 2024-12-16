import aiohttp
from homeassistant import config_entries
import voluptuous as vol
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
import logging
from .const import DOMAIN, EZLOPI_API_URL_BASE

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self._show_form()

        if CONF_USERNAME not in user_input or CONF_PASSWORD not in user_input:
            return self._show_form(errors={"base": "missing_required_fields"})

        try:
            await self._validate_input(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
        except ValueError as e:
            _LOGGER.error(f"Validation failed: {e}")
            return self._show_form(errors={"base": "invalid_credentials"})

        if not isinstance(user_input[CONF_USERNAME], str) or not isinstance(user_input[CONF_PASSWORD], str):
            raise ValueError("Invalid input data")

        res =  self.async_create_entry(
            title=user_input[CONF_USERNAME],
            data={
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD]
            }
        )

        return res

    def _show_form(self, errors=None):
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME, default=""): str,
                vol.Required(CONF_PASSWORD, default=""): str,
            }),
            errors=errors or {},
            description_placeholders={
                CONF_USERNAME: "Ezlo username",
                CONF_PASSWORD: "Ezlo password"
            }
        )

    async def _validate_input(self, username, password):
        """
        Validate user credentials by making an asynchronous API call.

        Args:
            username (str): The username to authenticate.
            password (str): The password for the user.

        Returns:
            dict: A dictionary with the validation result.
                Example:
                {"status": "success", "token": "abc123"} if valid
                {"status": "error", "message": "Invalid credentials"} if invalid
        """
        login_url = EZLOPI_API_URL_BASE
        headers = {"Content-type": "application/json"}
        login_data = {
            "call": "login_with_id_and_password",
            "params": {
                "user_id": username,
                "user_password": password
            }
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(login_url, headers=headers, json=login_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("data", {}).get("token"):
                            return
            except aiohttp.ClientError as e:
                _LOGGER.error(f"Error during API call: {e}")
        raise ValueError("Invalid username or pasword")
