"""Config flow for Systemair integration."""
from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.auth.providers.homeassistant import InvalidAuth
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import (DOMAIN, HA_SC_AUTHENTICATION_INTERVAL, HA_SC_CLOUD_PUSH,
                    HA_SC_CLOUD_PUSH_DEFAULT)
from .gateway import SaveConnectAPI

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_EMAIL): vol.basestring,
    vol.Required(CONF_PASSWORD): vol.basestring,
    vol.Optional(HA_SC_CLOUD_PUSH, default=HA_SC_CLOUD_PUSH_DEFAULT): cv.boolean,
}, required=True)


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    hub = SaveConnectAPI(
        hass,
        email=data[CONF_EMAIL],
        password=data[CONF_PASSWORD],
        ws_enabled=data[HA_SC_CLOUD_PUSH],
        refresh_token_interval=HA_SC_AUTHENTICATION_INTERVAL,
        loop=hass.loop
    )

    result = await hub.test_connection()
    if not result:
        raise CannotConnect

    auth_result = await hub.auth()
    if not auth_result:
        raise InvalidAuth

    return {"title": f"{data[CONF_EMAIL]}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hello World."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidHost:
                errors["host"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""
