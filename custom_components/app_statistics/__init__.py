"""The App Statistics integration."""
from __future__ import annotations
from dataclasses import dataclass
import logging
from typing import Any
import google.oauth2.credentials

import aiohttp
from .report_coordinator import ReportCoordinator
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import json

from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant


from .const import (
    CONF_ADMOB_CLIENT_ID,
    CONF_ADMOB_CLIENT_SECRET,
    CONF_ADMOB_PUBLISHER_ID,
    CONF_BUCKET_NAME,
    CONF_IOS_BUNDLE_ID,
    CONF_IOS_CONNECT_ISSUER_ID,
    CONF_IOS_CONNECT_KEY_ID,
    CONF_IOS_CONNECT_KEY_PATH,
    CONF_PLAY_BUNDLE_ID,
    CONF_PLAY_SERVICE_ACCOUNT_PATH,
    DOMAIN,
)
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)

# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


@dataclass
class HomeAssistantAppStatisticsData:
    """App statistics data stored in the Home Assistant data object."""

    admob_client: Any
    admob_user: dict[str, Any]
    session: OAuth2Session


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Spotify integration."""
    if DOMAIN not in config:
        return True

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up App Statistics from a config entry."""
    _LOGGER.debug(msg=entry.data)
    implementation = await async_get_config_entry_implementation(hass, entry)
    session = OAuth2Session(hass, entry, implementation)
    _LOGGER.debug(msg=entry.data)

    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientError as err:
        raise ConfigEntryNotReady from err

    google_credentials = json.json_loads(entry.data["google_credentials"])
    credentials = google.oauth2.credentials.Credentials(
        google_credentials["token"],
        refresh_token=google_credentials["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=google_credentials["scopes"],
        client_id=entry.data["reports"][CONF_ADMOB_CLIENT_ID],
        client_secret=entry.data["reports"][CONF_ADMOB_CLIENT_SECRET],
        enable_reauth_refresh=True,
    )

    coordinator = ReportCoordinator(
        hass,
        play_service_account_path=entry.data["reports"][CONF_PLAY_SERVICE_ACCOUNT_PATH],
        bucket_name=entry.data["reports"][CONF_BUCKET_NAME],
        play_bundle_id=entry.data["reports"][CONF_PLAY_BUNDLE_ID],
        ios_bundle_id=entry.data["reports"][CONF_IOS_BUNDLE_ID],
        ios_key_id=entry.data["reports"][CONF_IOS_CONNECT_KEY_ID],
        ios_key_path=entry.data["reports"][CONF_IOS_CONNECT_KEY_PATH],
        ios_issuer_id=entry.data["reports"][CONF_IOS_CONNECT_ISSUER_ID],
        admob_publisher_id=entry.data["reports"][CONF_ADMOB_PUBLISHER_ID],
        admob_credentials=credentials,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)
