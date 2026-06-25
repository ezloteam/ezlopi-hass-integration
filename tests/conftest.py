"""Fixtures for ezloPi tests."""
from collections.abc import Generator
from unittest.mock import patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""
    return


@pytest.fixture(autouse=True)
def mock_setup_entry(request: pytest.FixtureRequest) -> Generator[None]:
    """Stub integration setup so flow tests don't open the mDNS browser or a hub.

    ``async_setup`` creates the global zeroconf browser (real socket) and
    ``async_setup_entry`` connects to a hub; both are out of scope for config
    flow tests. Tests marked ``real_setup`` opt out to exercise the real setup
    path (with the connection/browser/cloud mocked at a lower level).
    """
    if "real_setup" in request.keywords:
        yield
        return
    with (
        patch("custom_components.ezlopi.async_setup", return_value=True),
        patch("custom_components.ezlopi.async_setup_entry", return_value=True),
    ):
        yield
