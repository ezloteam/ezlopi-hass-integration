"""Config, reauth and reconfigure flows for the ezloPi integration."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN
from .ezlopi_utils import EzloAuthError, EzloCloudAPI, EzloConnectionError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step (add a new Ezlo account)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME]
            error = await self._async_validate(username, user_input[CONF_PASSWORD])
            if error is None:
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=username, data=user_input)
            errors["base"] = error

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle an ezloPi hub discovered on the LAN via mDNS.

        The integration is account-based (one cloud account manages all of its
        hubs), so discovery can't auto-provision a hub. It confirms a hub is
        present and routes the user to enter their Ezlo credentials; if an
        account is already configured the hub is already handled.
        """
        serial = discovery_info.properties.get("Serial")
        await self.async_set_unique_id(serial or discovery_info.name)
        # Dedupe re-announcements of the same hub.
        self._abort_if_unique_id_configured()
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        self.context["title_placeholders"] = {"name": f"ezloPi {serial}"}
        return await self.async_step_user()

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Triggered by ConfigEntryAuthFailed: ask for fresh credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication, keeping the same account."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        username = reauth_entry.data[CONF_USERNAME]

        if user_input is not None:
            error = await self._async_validate(username, user_input[CONF_PASSWORD])
            if error is None:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={CONF_USERNAME: username},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change the account credentials in place."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            error = await self._async_validate(username, user_input[CONF_PASSWORD])
            if error is None:
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_mismatch(reason="account_mismatch")
                return self.async_update_reload_and_abort(
                    reconfigure_entry, data_updates=user_input
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA,
                {CONF_USERNAME: reconfigure_entry.data[CONF_USERNAME]},
            ),
            errors=errors,
        )

    async def _async_validate(self, username: str, password: str) -> str | None:
        """Validate credentials. Return None on success or an error key."""
        api = EzloCloudAPI(
            username=username,
            password=password,
            session=async_get_clientsession(self.hass),
        )
        try:
            await api.fetch_hub_list()
        except EzloAuthError:
            return "invalid_auth"
        except EzloConnectionError:
            return "cannot_connect"
        except Exception:  # noqa: BLE001 - surface anything unexpected to the user
            _LOGGER.exception("Unexpected error validating ezloPi credentials")
            return "unknown"
        return None
