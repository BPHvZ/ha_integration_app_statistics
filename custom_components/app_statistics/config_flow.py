"""Config flow for App Statistics integration."""
from __future__ import annotations

import logging
from typing import Any, Mapping

import voluptuous as vol
from homeassistant.components import persistent_notification

from homeassistant.config_entries import ConfigEntry

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow
import homeassistant.helpers.config_validation as cv
from googleapiclient.discovery import build
import google.oauth2.credentials as gCredentials


from .const import (
    CONF_ADMOB_CLIENT_ID,
    CONF_ADMOB_PUBLISHER_ID,
    CONF_ADMOB_CLIENT_SECRET,
    CONF_BUCKET_NAME,
    CONF_GOOGLE_ACCESS_TOKEN,
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
        vol.Required(
            CONF_PLAY_SERVICE_ACCOUNT_PATH
        ): cv.string,
        vol.Required(
            CONF_PLAY_BUNDLE_ID
        ): cv.string,
        vol.Required(
            CONF_BUCKET_NAME
        ): cv.string,
        vol.Required(
            CONF_IOS_BUNDLE_ID
        ): cv.string,
        vol.Required(CONF_IOS_CONNECT_KEY_ID): cv.string,
        vol.Required(
            CONF_IOS_CONNECT_KEY_PATH
        ): cv.string,
        vol.Required(
            CONF_IOS_CONNECT_ISSUER_ID
        ): cv.string,
        vol.Required(
            CONF_ADMOB_PUBLISHER_ID
        ): cv.string,
        vol.Required(
            CONF_ADMOB_CLIENT_ID
        ): cv.string,
        vol.Required(
            CONF_ADMOB_CLIENT_SECRET
        ): cv.string,
    }
)

STEP_GOOGLE_AUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GOOGLE_ACCESS_TOKEN): cv.string,
    }
)


async def validate_input(data: dict[str, str]) -> dict[str, str]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    for k, _v in data.items():
        data[k] = _v.strip()

    cv.isfile(data[CONF_PLAY_SERVICE_ACCOUNT_PATH])
    cv.isfile(data[CONF_IOS_CONNECT_KEY_PATH])


class AppStatisticsFlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle App Statistics Admob OAuth2 authentication."""

    DOMAIN = DOMAIN
    VERSION = 1

    reauth_entry: ConfigEntry | None = None

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data that needs to be appended to the authorize url."""
        return {
            "scope": " ".join(
                [
                    "https://www.googleapis.com/auth/admob.readonly",
                    "https://www.googleapis.com/auth/admob.report",
                ]
            ),
            "access_type": "offline",
            "response_type": "code",
            "include_granted_scopes": "true",
        }

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Create an entry for App Statistics."""
        self.logger.debug(msg=data)

        scopes_str: str = data["token"]["scope"]
        scopes_list: list[str] = scopes_str.split(" ")

        credentials = gCredentials.Credentials(
            data["token"]["access_token"],
            refresh_token=data["token"]["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            scopes=scopes_list,
            client_id=self.reports_input[CONF_ADMOB_CLIENT_ID],
            client_secret=self.reports_input[CONF_ADMOB_CLIENT_SECRET],
            enable_reauth_refresh=True,
        )
        admob = build("admob", "v1", credentials=credentials)

        try:
            accounts = await self.hass.async_add_executor_job(
                admob.accounts().list().execute
            )
            self.logger.debug(msg=accounts)
        except Exception:  # pylint: disable=broad-except
            return self.async_abort(reason="connection_error")

        if (
            self.reauth_entry
            and self.reauth_entry.data["id"] != self.reports_input[CONF_IOS_BUNDLE_ID]
        ):
            return self.async_abort(reason="reauth_account_mismatch")

        await self.async_set_unique_id(self.reports_input[CONF_IOS_BUNDLE_ID])
        self._abort_if_unique_id_configured()

        data["google_credentials"] = credentials.to_json()
        data["reports"] = self.reports_input

        return self.async_create_entry(
            title=self.reports_input[CONF_IOS_BUNDLE_ID],
            data=data,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the manifest step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(user_input)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(user_input[CONF_IOS_BUNDLE_ID])
            self._abort_if_unique_id_configured()
            self.reports_input = user_input
            return await super().async_step_user()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon migration of old entries."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        persistent_notification.async_create(
            self.hass,
            f"App Statistics Admob integration for account {entry_data['id']} needs to be "
            "re-authenticated. Please go to the integrations page to re-configure it.",
            "Admob re-authentication",
            "app_statistics_admob_reauth",
        )

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauth dialog."""
        if self.reauth_entry is None:
            return self.async_abort(reason="reauth_account_mismatch")

        if user_input is None and self.reauth_entry:
            return self.async_show_form(
                step_id="reauth_confirm",
                description_placeholders={
                    "account": self.reauth_entry.data["id"]},
                errors={},
            )

        persistent_notification.async_dismiss(
            self.hass, "app_statistics_admob_reauth")
        return await self.async_step_pick_implementation(
            user_input={
                "implementation": self.reauth_entry.data["auth_implementation"]}
        )
