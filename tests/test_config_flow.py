"""Tests for the ezloPi config, reauth, reconfigure and discovery flows."""
from ipaddress import ip_address
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ezlopi.const import DOMAIN
from custom_components.ezlopi.ezlopi_utils import EzloAuthError, EzloConnectionError

_USER_INPUT = {CONF_USERNAME: "user", CONF_PASSWORD: "pass"}
_FETCH = "custom_components.ezlopi.config_flow.EzloCloudAPI.fetch_hub_list"


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=_USER_INPUT, unique_id="user")


async def test_user_flow_success(hass: HomeAssistant, mock_setup_entry: None) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(_FETCH, new=AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _USER_INPUT
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "user"
    assert result["data"] == _USER_INPUT
    assert result["result"].unique_id == "user"


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (EzloAuthError(), "invalid_auth"),
        (EzloConnectionError(), "cannot_connect"),
        (RuntimeError(), "unknown"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant, side_effect: Exception, error: str
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(_FETCH, new=AsyncMock(side_effect=side_effect)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _USER_INPUT
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    # Recover on a subsequent valid attempt.
    with patch(_FETCH, new=AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _USER_INPUT
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_account_aborts(
    hass: HomeAssistant, mock_setup_entry: None
) -> None:
    _entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(_FETCH, new=AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _USER_INPUT
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(hass: HomeAssistant, mock_setup_entry: None) -> None:
    entry = _entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(_FETCH, new=AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "newpass"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "newpass"


async def test_reconfigure_flow(hass: HomeAssistant, mock_setup_entry: None) -> None:
    entry = _entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(_FETCH, new=AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "user", CONF_PASSWORD: "changed"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_PASSWORD] == "changed"


async def test_reauth_invalid_shows_error(
    hass: HomeAssistant, mock_setup_entry: None
) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    with patch(_FETCH, new=AsyncMock(side_effect=EzloAuthError())):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "wrong"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reconfigure_invalid_shows_error(
    hass: HomeAssistant, mock_setup_entry: None
) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    with patch(_FETCH, new=AsyncMock(side_effect=EzloConnectionError())):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "user", CONF_PASSWORD: "x"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


def _discovery() -> ZeroconfServiceInfo:
    return ZeroconfServiceInfo(
        ip_address=ip_address("10.0.0.5"),
        ip_addresses=[ip_address("10.0.0.5")],
        port=17001,
        hostname="ezlopi_3280.local.",
        type="_ezlo._tcp.local.",
        name="EzloPi._ezlo._tcp.local.",
        properties={"Serial": "105203280"},
    )


async def test_zeroconf_discovery_prompts_user(
    hass: HomeAssistant, mock_setup_entry: None
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_discovery(),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(_FETCH, new=AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _USER_INPUT
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_zeroconf_discovery_aborts_when_configured(
    hass: HomeAssistant, mock_setup_entry: None
) -> None:
    _entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_discovery(),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
