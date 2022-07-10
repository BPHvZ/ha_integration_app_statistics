"""Support for the AccuWeather service."""
from __future__ import annotations
import logging
from typing import cast

from homeassistant.const import CONF_NAME
from homeassistant.helpers.typing import StateType

from .const import (
    CONF_IOS_BUNDLE_ID,
    DOMAIN,
    SENSOR_ANDROID_CURRENT_ACTIVE_INSTALLS,
    SENSOR_IOS_TOTAL_INSTALLS,
)
from .report_coordinator import ReportCoordinator

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=SENSOR_IOS_TOTAL_INSTALLS, name="iOS total app installs"
    ),
    SensorEntityDescription(
        key=SENSOR_ANDROID_CURRENT_ACTIVE_INSTALLS,
        name="Android current active installs",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add App Statistics entities from a config_entry."""
    config = entry.data

    app_bundle_id = config.get(CONF_IOS_BUNDLE_ID)

    coordinator: ReportCoordinator = hass.data[DOMAIN][entry.entry_id]

    if app_bundle_id is None:
        _LOGGER.error("App bundle ID is not set in Home Assistant config")
        return

    _LOGGER.debug(
        "Initializing app statistics sensor app bundle ID %s",
        app_bundle_id,
    )

    entities = [
        AppStatisticsSensor(
            config.get(CONF_NAME, "App Statistics"),
            app_bundle_id,
            description,
            coordinator,
        )
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities)


class AppStatisticsSensor(CoordinatorEntity[ReportCoordinator], SensorEntity):
    """Define an App Statistics entity."""

    def __init__(
        self,
        client_name: str,
        app_bundle_id: str,
        description: SensorEntityDescription,
        coordinator: ReportCoordinator,
    ) -> None:
        """Initialize."""
        logging.debug("initializing sensor %i", description.key)
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = f"{client_name} {description.name}"
        self._measured = None
        self._attr_unique_id = "{}{}".format(app_bundle_id, description.key)
        self._sensor_data = _get_sensor_data(coordinator.data, description.key)

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        return cast(StateType, self._sensor_data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        logging.debug("update data with %i", self.coordinator.data)
        self._sensor_data = _get_sensor_data(
            self.coordinator.data, self.entity_description.key
        )
        self.async_write_ha_state()


def _get_sensor_data(sensors: dict[str, int], kind: str) -> int:
    """Get sensor data."""
    logging.debug(kind)
    return sensors[kind]
