import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN

@config_entries.HANDLERS.register(DOMAIN)
class OekostromATPriceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Oekostrom AT Price."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Oekostrom AT Price", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
            })
        )

    async def async_step_import(self, user_input=None):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(user_input)

    async def async_step_reauth(self, user_input=None):
        """Handle reauthentication."""
        if user_input is not None:
            return self.async_create_entry(title="Oekostrom AT Price", data=user_input)

        return self.async_show_form(
            step_id="reauth", data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
            })
        )
