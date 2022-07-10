"""The App Statistics integration."""
from __future__ import annotations
from .report_coordinator import ReportCoordinator

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

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

# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up buienradar from a config entry."""
    coordinator = ReportCoordinator(
        hass,
        play_service_account_path=entry.data[CONF_PLAY_SERVICE_ACCOUNT_PATH],
        bucket_name=entry.data[CONF_BUCKET_NAME],
        play_bundle_id=entry.data[CONF_PLAY_BUNDLE_ID],
        ios_bundle_id=entry.data[CONF_IOS_BUNDLE_ID],
        ios_key_id=entry.data[CONF_IOS_CONNECT_KEY_ID],
        ios_key_path=entry.data[CONF_IOS_CONNECT_KEY_PATH],
        ios_issuer_id=entry.data[CONF_IOS_CONNECT_ISSUER_ID],
    )
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

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
