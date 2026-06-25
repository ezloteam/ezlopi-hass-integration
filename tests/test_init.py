"""Full setup/unload + diagnostics tests with the hub mocked at a low level."""
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ezlopi.const import DOMAIN
from custom_components.ezlopi.diagnostics import async_get_config_entry_diagnostics
from custom_components.ezlopi.ezlopi_utils import EzloAuthError, EzloConnectionError

from .fixtures import SERIAL, FakeBrowser, FakeCloudAPI, FakeConnection

pytestmark = pytest.mark.real_setup

_DATA = {CONF_USERNAME: "user", CONF_PASSWORD: "pass"}


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=_DATA, unique_id="user")


def _patches():
    return (
        patch("custom_components.ezlopi.EzloPiMDSConnector", FakeBrowser),
        patch("custom_components.ezlopi.EzloHubConnection", FakeConnection),
        patch("custom_components.ezlopi.EzloCloudAPI", FakeCloudAPI),
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    with _patches()[0], _patches()[1], _patches()[2]:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_setup_creates_entities_and_devices(hass: HomeAssistant) -> None:
    entry = _entry()
    await _setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED

    # the dimmer is one light, named after its device (has_entity_name)
    light = hass.states.get("light.hall_dimmer")
    assert light is not None
    assert light.state == "on"

    # Devices are the physical end-devices only — no separate hub/controller device.
    dev_reg = dr.async_get(hass)
    identifiers = {ident for d in dev_reg.devices.values() for ident in d.identifiers}
    assert (DOMAIN, f"{SERIAL}_d_light") in identifiers
    assert (DOMAIN, SERIAL) not in identifiers  # no hub device

    # firmware from hub.info.get is shown as the device's sw_version
    phys = dev_reg.async_get_device(identifiers={(DOMAIN, f"{SERIAL}_d_light")})
    assert phys is not None
    assert phys.sw_version == "4.1.6"


async def test_stale_devices_pruned(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    # Pre-seed a leftover hub/controller device from an older version.
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, SERIAL)}, name="old hub"
    )
    await _setup(hass, entry)
    assert dev_reg.async_get_device(identifiers={(DOMAIN, SERIAL)}) is None


async def test_unload(hass: HomeAssistant) -> None:
    entry = _entry()
    await _setup(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_diagnostics(hass: HomeAssistant) -> None:
    entry = _entry()
    await _setup(hass, entry)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["data"][CONF_PASSWORD] == "**REDACTED**"
    assert diag["hubs"][0]["item_count"] == 6
    assert diag["hubs"][0]["connected"] is True


async def test_setup_auth_failure_raises(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)

    class AuthFail(FakeCloudAPI):
        async def fetch_hub_list(self) -> bool:
            raise EzloAuthError("bad")

    with (
        patch("custom_components.ezlopi.EzloPiMDSConnector", FakeBrowser),
        patch("custom_components.ezlopi.EzloCloudAPI", AuthFail),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_connection_failure_retries(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)

    class NoHubs(FakeCloudAPI):
        def get_hub_list(self) -> dict:
            return {}

    with (
        patch("custom_components.ezlopi.EzloPiMDSConnector", FakeBrowser),
        patch("custom_components.ezlopi.EzloCloudAPI", NoHubs),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_cloud_connection_error_retries(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)

    class ConnFail(FakeCloudAPI):
        async def fetch_hub_list(self) -> bool:
            raise EzloConnectionError("down")

    with (
        patch("custom_components.ezlopi.EzloPiMDSConnector", FakeBrowser),
        patch("custom_components.ezlopi.EzloCloudAPI", ConnFail),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
