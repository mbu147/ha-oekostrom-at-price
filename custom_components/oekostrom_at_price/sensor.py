import requests
from bs4 import BeautifulSoup
import logging
from homeassistant.helpers.entity import Entity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def login_to_oekostrom(username, password):
    login_url = "https://mein.oekostrom.at/login"
    session = requests.Session()
    payload = {
        "username": username,
        "password": password
    }
    response = session.post(login_url, data=payload)
    if response.status_code == 200:
        return session
    else:
        _LOGGER.error("Login failed")
        return None

def fetch_price(session):
    url = "https://mein.oekostrom.at/a-p/"
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        arbeitspreis = soup.find("span", {"id": "arbeitspreis"}).text
        return arbeitspreis
    else:
        _LOGGER.error("Failed to fetch price")
        return None

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    async_add_entities([OekostromATPriceSensor(hass, config)])

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the Oekostrom AT Price platform via config entry."""
    async_add_entities([OekostromATPriceSensor(hass, entry.data)])
    return True

class OekostromATPriceSensor(Entity):
    """Representation of the Oekostrom AT price sensor."""

    def __init__(self, hass, config):
        self._hass = hass
        self._state = None
        self._name = "Oekostrom AT Price"
        self._unique_id = "oekostrom_at_price"
        self._session = login_to_oekostrom(config.get("username"), config.get("password"))

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the current state of the sensor."""
        return self._state

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    async def async_update(self):
        """Fetch the latest price and update the sensor state."""
        _LOGGER.debug("Updating Oekostrom AT price sensor...")
        if self._session:
            arbeitspreis = fetch_price(self._session)
            if arbeitspreis is not None:
                self._state = arbeitspreis
                _LOGGER.info(f"Price successfully updated: {self._state}")
            else:
                _LOGGER.warning("Price could not be updated.")
        else:
            _LOGGER.error("No valid session")
