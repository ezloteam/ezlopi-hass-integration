"""Tests for utils helpers not covered by the data-path tests."""
from typing import Any
from unittest.mock import MagicMock, patch

from custom_components.ezlopi import utils
from custom_components.ezlopi.utils import (
    extract_battery_info,
    get_device_battery_level,
    get_devices,
    get_devices_from_platform,
    get_items,
    get_login_params,
    getItemsData,
    set_item_value,
    should_create_low_battery_sensor,
    system_logging_param,
)

from .fixtures import FakeConnection


def test_request_builders() -> None:
    assert system_logging_param()["method"] == "hub.log.set"
    assert set_item_value()["method"] == "hub.item.value.set"
    assert get_login_params()["method"] == "hub.offline.login.ui"
    conn = FakeConnection()
    assert get_items(conn) is conn.items
    assert get_devices(conn) is conn.devices


def test_get_items_data_units_and_battery() -> None:
    conn = FakeConnection()
    conn.items = [
        {"_id": "t", "deviceId": "d", "name": "temp", "value": 21.0,
         "valueType": "temperature", "hasSetter": False, "show": True,
         "scale": "celsius"},
        {"_id": "f", "deviceId": "d", "name": "temp2", "value": 70.0,
         "valueType": "temperature", "hasSetter": False, "show": True,
         "scale": "fahrenheit"},
        {"_id": "h", "deviceId": "d", "name": "hum", "value": 55,
         "valueType": "humidity", "hasSetter": False, "show": True},
        {"_id": "hidden", "deviceId": "d", "name": "x", "value": 1,
         "valueType": "int", "hasSetter": False, "show": False},
    ]
    conn.devices = [{"_id": "d", "name": "Dev", "deviceTypeId": None,
                     "category": "battery", "subcategory": None, "armed": False}]
    by_id = {e["id"]: e for e in getItemsData(conn)}
    assert "hidden" not in by_id  # show=False filtered out
    assert by_id["t"]["unitOfMeasurement"] == "°C"
    assert by_id["f"]["unitOfMeasurement"] == "°F"
    assert by_id["h"]["unitOfMeasurement"] == "%"
    # request a single item by id
    single = getItemsData(conn, "t")
    assert single["id"] == "t"


async def test_get_devices_from_platform_retries() -> None:
    conn = FakeConnection()
    conn.items = []  # getItemsData returns [] -> still returned
    result = await get_devices_from_platform(conn)
    assert result == []


def test_battery_helpers() -> None:
    devices = [
        {"deviceId": "d1", "id": "b1", "deviceClass": "battery", "value": 80},
        {"deviceId": "d2", "id": "x", "deviceClass": "temperature", "value": 5},
        {"id": "no_device"},
    ]
    info = extract_battery_info(devices)
    assert info["d1"]["battery_level"] == 80
    assert "d2" not in info

    # get_device_battery_level processes items through getItemsData, so feed it
    # a properly-shaped item that detects as a battery sensor.
    conn = FakeConnection()
    conn.items = [{"_id": "b1", "deviceId": "d1", "name": "battery", "value": 80,
                   "valueType": "int", "hasSetter": False, "show": True}]
    conn.devices = []
    assert get_device_battery_level("d1", conn) == 80
    assert get_device_battery_level("missing", conn) is None

    assert should_create_low_battery_sensor(10) is True
    assert should_create_low_battery_sensor(50) is False
    assert should_create_low_battery_sensor(None) is False


async def test_ping_host(hass: Any) -> None:
    with patch("custom_components.ezlopi.utils.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        assert await utils.ping_host("10.0.0.1") is True
        run.return_value = MagicMock(returncode=1)
        assert await utils.ping_host("10.0.0.1") is False
    with patch("custom_components.ezlopi.utils.subprocess.run", side_effect=OSError):
        assert await utils.ping_host("10.0.0.1") is False
