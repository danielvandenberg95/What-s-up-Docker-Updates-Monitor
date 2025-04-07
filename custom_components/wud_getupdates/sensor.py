import logging
import aiohttp
from datetime import timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class WUDUpdateCoordinator(DataUpdateCoordinator):
    """Coordinates fetching container updates from WUD."""

    def __init__(self, hass, host, port):
        self.host = host
        self.port = port
        super().__init__(
            hass,
            _LOGGER,
            name="WUD Update Coordinator",
            update_interval=timedelta(minutes=1),  # Customize interval here
        )

    async def _async_update_data(self):
        """Fetch data from WUD API."""
        url = f"http://{self.host}:{self.port}/api/containers"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise UpdateFailed("WUD API request failed")
                    return await response.json()
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up WUD sensors using the coordinator."""
    host = config_entry.data["host"]
    port = config_entry.data["port"]
    instance_name = config_entry.data["instance_name"]

    coordinator = WUDUpdateCoordinator(hass, host, port)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        WUDContainerSensor(container, config_entry, instance_name, coordinator)
        for container in coordinator.data
    ]
    async_add_entities(sensors)


class WUDContainerSensor(CoordinatorEntity, Entity):
    """Representation of a What's Up Docker container sensor."""

    def __init__(self, container, config_entry, instance_name, coordinator):
        super().__init__(coordinator)
        self._container_name = container["name"]
        self._name = f"{container['name']} Update Available"
        self._unique_id = f"wud_{config_entry.entry_id}_{self._container_name.lower().replace(' ', '_')}_update_available"
        self._instance_name = instance_name
        self._config_entry = config_entry

        self._device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": instance_name,
            "manufacturer": "What's Up Docker",
            "model": "Docker Instance",
        }

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        container = self._get_container()
        return "Yes" if container.get("updateAvailable", False) else "No"

    @property
    def extra_state_attributes(self):
        container = self._get_container()
        return {
            "container_id": container["id"],
            "version": container.get("version", "unknown"),
            "update_available": container.get("updateAvailable", False),
        }

    @property
    def device_info(self):
        return self._device_info

    def _get_container(self):
        return next(
            (c for c in self.coordinator.data if c["name"] == self._container_name),
            {},
        )
