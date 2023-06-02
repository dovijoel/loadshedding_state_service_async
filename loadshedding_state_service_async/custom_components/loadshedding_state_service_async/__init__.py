import logging

from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Loadshedding State Service Async component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: core.HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Loadshedding State Service Async from a config entry."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True
