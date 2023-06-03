"""Loadshedding state service async sensor platform."""
from __future__ import annotations

import logging
from datetime import timedelta, datetime
from typing import Callable, Optional, Dict, List

import voluptuous as vol
from aiohttp import ClientSession
from homeassistant.components.calendar import CalendarEntity, CalendarEvent

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType, ConfigType, DiscoveryInfoType

from loadshedding_api import LoadsheddingAPI
from .const import (
    DOMAIN,
    ATTR_CURRENT_STAGE,
    ATTR_NEXT_STAGE,
    ATTR_BLOCK_ID,
    ATTR_BLOCK_NAME,
    BASE_API_URL, ATTR_STAGE_UPDATED_DATETIME, ATTR_NEXT_STAGES, ATTR_AREA_INFORMATION_SCHEDULE,
    ATTR_AREA_INFORMATION_DAYS, ATTR_AREA_INFORMATION_DAYS_DATE, ATTR_AREA_INFORMATION_DAYS_STAGES
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


class LoadsheddingSensor(CalendarEntity):
    """Representation of a Loadshedding Sensor."""
    _attr_has_entity_name = True
    _attr_name = "Loadshedding"

    def __init__(self, loadshedding_api: LoadsheddingAPI, loadshedding_config: Dict[str, str]) -> None:
        """Initialize the sensor."""
        super().__init__()
        # defined attributes for loadshedding
        self.loadshedding_api = loadshedding_api
        self.block_id: str = loadshedding_config["block_id"]
        self.block_name: str | None = None
        self.current_stage: int | None = None
        self.stages_last_updated: datetime | None = None
        self.stages: List[Dict[str, str]] = []
        self.schedule: List[CalendarEvent] = []
        self.attrs: Dict[str, str] = {ATTR_BLOCK_ID: self.block_id}
        self._name = f"Loadshedding"
        self._state = None
        self._available = True
        self._event: CalendarEvent | None = None

    @property
    def should_poll(self) -> bool:
        """Enable polling for the entity.
        TODO why?
        """
        return True

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available is not None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        # TODO is updating every hour good enough to ensure latest event here?
        return self.schedule[0] if self.schedule and len(self.schedule) > 0 else None

    async def async_get_events(
            self,
            hass: HomeAssistant,
            start_date: datetime,
            end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return the loadshedding schedule."""
        return self.schedule

    async def async_update(self) -> None:
        """Update the sensor."""
        try:
            # update loadshedding stage
            data = await self.loadshedding_api.get_loadshedding_status()
            stages_last_updated = datetime.strptime(data[ATTR_STAGE_UPDATED_DATETIME], "%Y-%m-%dT%H:%M:%S.%fZ")
            if self.stages_last_updated != stages_last_updated:
                self.stages_last_updated = stages_last_updated
                self.current_stage = data[ATTR_CURRENT_STAGE]
                self.stages = data[ATTR_NEXT_STAGES]

            # update loadshedding schedule
            data = await self.loadshedding_api.get_area_information(self.block_id)
            raw_schedule: List = data[ATTR_AREA_INFORMATION_SCHEDULE][ATTR_AREA_INFORMATION_DAYS]
            if isinstance(raw_schedule, list):
                schedule = []
                for day in raw_schedule:
                    date = datetime.strptime(day[ATTR_AREA_INFORMATION_DAYS_DATE], "%Y-%m-%d")
                    # iterate through stages, keeping track of index in list
                    for i, stage in enumerate(day[ATTR_AREA_INFORMATION_DAYS_STAGES]):
                        # if stage is not empty, add to schedule
                        if len(stage) > 0:
                            for slot in stage:
                                times = slot.split("-")
                                start_time = datetime.strptime(times[0], "%H:%M")
                                end_time = datetime.strptime(times[1], "%H:%M")
                                self.schedule.append(CalendarEvent(
                                    start=date.replace(hour=start_time.hour, minute=start_time.minute),
                                    end=date.replace(hour=end_time.hour, minute=end_time.minute),
                                    summary=f"Stage {stage}"
                                ))
                    for event in self.schedule:
                        await self.async_create_event(event=event)
                # overwrite schedule
                self.schedule = schedule

                # make sure first item in schedule hasn't passed
                first_item_is_past = self.schedule[0].end < datetime.now()
                while first_item_is_past:
                    if self.schedule[0].end < datetime.now():
                        self.schedule.pop(0)
                    else:
                        first_item_is_past = False

            # update attributes
            self._available = True
        except Exception as e:
            _LOGGER.error(f"Error updating loadshedding sensor: {e}")
            self._available = False

