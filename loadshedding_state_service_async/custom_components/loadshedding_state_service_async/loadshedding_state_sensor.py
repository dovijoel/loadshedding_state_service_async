"""Loadshedding state service async sensor platform."""
import logging
from datetime import timedelta
from typing import Callable, Optional, Dict

import voluptuous as vol
from aiohttp import ClientSession

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
)
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType, ConfigType, DiscoveryInfoType

from loadshedding_api import LoadsheddingAPI
from .const import (
    DOMAIN,
    ATTR_CURRENT_STAGE,
    ATTR_STAGE_CHANGE_DATETIME,
    ATTR_NEXT_STAGE,
    ATTR_IS_LOADSHEDDING,
    ATTR_NEXT_LOADSHEDDING_START,
    ATTR_NEXT_LOADSHEDDING_END,
    ATTR_LOADSHEDDING_CALENDAR,
    ATTR_BLOCK_ID,
    ATTR_BLOCK_NAME,
    BASE_API_URL
)

_LOGGER = logging.getLogger(__name__)
# Time between updating data from ESP API
SCAN_INTERVAL = timedelta(hours=1)

CONF_LOADSHEDDING = "loadshedding"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ACCESS_TOKEN): cv.string
    }
)


async def async_setup_platform(
        hass: HomeAssistantType,
        config: ConfigType,
        async_add_entities: Callable,
        discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    session = async_create_clientsession(hass, headers={"token": config[CONF_ACCESS_TOKEN]})
    loadshedding_api = LoadsheddingAPI(session, BASE_API_URL)
    load_shedding_sensor = LoadsheddingSensor(loadshedding_api, config[CONF_LOADSHEDDING])
    async_add_entities([load_shedding_sensor], update_before_add=True)


class LoadsheddingSensor(Entity):
    """Representation of a Loadshedding Sensor."""

    def __init__(self, loadshedding_api: LoadsheddingAPI, loadshedding_config: Dict[str, str]) -> None:
        """Initialize the sensor."""
        super().__init__()
        self.loadshedding_api = loadshedding_api
        self.block_id = loadshedding_config["block_id"]
        self.attrs: Dict[str, str] = {ATTR_BLOCK_ID: self.block_id}
        self._name = f"Loadshedding {loadshedding_config['block_name']}"
        self._state = None
        self._available = True

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return self._state

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available is not None

    @property
    def device_state_attributes(self) -> Dict[str, str]:
        """Return the state attributes."""
        return self.attrs

    async def async_update(self) -> None:
        """Update the sensor."""
        try:
            data = await self.loadshedding_api.get_loadshedding_status()
            self._state = data[ATTR_CURRENT_STAGE]
            self.attrs.update(data)
            self._available = True
        except Exception as e:
            _LOGGER.error(f"Error updating loadshedding sensor: {e}")
            self._available = False

