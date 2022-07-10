"""Config flow for App Statistics integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_BUCKET_NAME,
    CONF_IOS_BUNDLE_ID,
    CONF_IOS_CONNECT_ISSUER_ID,
    CONF_IOS_CONNECT_KEY_ID,
    CONF_IOS_CONNECT_KEY_PATH,
    CONF_PLAY_BUNDLE_ID,
    CONF_PLAY_SERVICE_ACCOUNT_PATH,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLAY_SERVICE_ACCOUNT_PATH): cv.string,
        vol.Required(CONF_PLAY_BUNDLE_ID): cv.string,
        vol.Required(CONF_BUCKET_NAME): cv.string,
        vol.Required(CONF_IOS_BUNDLE_ID): cv.string,
        vol.Required(CONF_IOS_CONNECT_KEY_ID): cv.string,
        vol.Required(CONF_IOS_CONNECT_KEY_PATH): cv.string,
        vol.Required(CONF_IOS_CONNECT_ISSUER_ID): cv.string,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    cv.isfile(data[CONF_PLAY_SERVICE_ACCOUNT_PATH])
    cv.isfile(data[CONF_IOS_CONNECT_KEY_PATH])


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for App Statistics."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(user_input[CONF_IOS_BUNDLE_ID])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_IOS_BUNDLE_ID], data=user_input
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
