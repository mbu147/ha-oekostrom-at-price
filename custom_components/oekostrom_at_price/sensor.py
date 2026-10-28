import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed

from .api import OekostromClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    # Own session: the portal uses cookies that must not leak into the shared one.
    client = OekostromClient(
        async_create_clientsession(hass), entry.data["username"], entry.data["password"]
    )

    async def _update():
        try:
            return await client.async_get_current_price()
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=DOMAIN, update_method=_update, update_interval=timedelta(hours=6)
    )
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([OekostromATPriceSensor(coordinator, entry)])


class OekostromATPriceSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Oekostrom AT Price"
    _attr_native_unit_of_measurement = "ct/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:currency-eur"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_arbeitspreis"

    @property
    def native_value(self):
        return round(self.coordinator.data["Amount"], 4)

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data
        return {
            "net_price": d.get("NetAmount"),
            "base_fee_gross_per_year": d.get("BaseAmount"),
            "tariff": d.get("Cot"),
            "valid_from": d.get("BDate"),
            "valid_to": d.get("EDate"),
        }
