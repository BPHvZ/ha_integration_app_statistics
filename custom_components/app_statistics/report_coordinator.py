"""Download reports from App Storen Connect and Play Console."""

from datetime import timedelta
import logging
from typing import Any
import google.oauth2.credentials


from .api import ReportApi
from .const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class ReportCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        play_service_account_path: str,
        bucket_name: str,
        play_bundle_id: str,
        ios_bundle_id: str,
        ios_key_id: str,
        ios_key_path: str,
        ios_issuer_id: str,
        admob_publisher_id: str,
        admob_credentials: google.oauth2.credentials.Credentials,
    ) -> None:
        """Initialize my coordinator."""
        self.api = ReportApi(
            hass=hass,
            play_service_account_path=play_service_account_path,
            bucket_name=bucket_name,
            play_bundle_id=play_bundle_id,
            ios_bundle_id=ios_bundle_id,
            ios_key_id=ios_key_id,
            ios_key_path=ios_key_path,
            ios_issuer_id=ios_issuer_id,
            admob_publisher_id=admob_publisher_id,
            admob_credentials=admob_credentials
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            data = await self.api.update_data()
            logging.debug(data)
            return data
        except Exception as err:
            logging.error(err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
