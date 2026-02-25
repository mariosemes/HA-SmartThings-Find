from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlowWithConfigEntry
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed
from .const import (
    DOMAIN,
    CONF_JSESSIONID,
    CONF_SESSION_CREATED_AT,
    CONF_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_DEFAULT,
    CONF_ACTIVE_MODE_SMARTTAGS,
    CONF_ACTIVE_MODE_SMARTTAGS_DEFAULT,
    CONF_ACTIVE_MODE_OTHERS,
    CONF_ACTIVE_MODE_OTHERS_DEFAULT
)
from .utils import fetch_csrf, get_login_url
import logging
from datetime import datetime, timezone

_LOGGER = logging.getLogger(__name__)

class SmartThingsFindConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartThings Find."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    reauth_entry: ConfigEntry | None = None

    async def _validate_jsessionid(self, jsessionid: str) -> bool:
        """Validate a JSESSIONID by attempting to fetch a CSRF token from STF."""
        temp_id = f"__config_flow_{self.flow_id}__"
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}
        self.hass.data[DOMAIN][temp_id] = {}
        session = async_get_clientsession(self.hass)
        session.cookie_jar.update_cookies({"JSESSIONID": jsessionid})
        try:
            await fetch_csrf(self.hass, session, temp_id)
            return True
        except ConfigEntryAuthFailed:
            return False
        finally:
            self.hass.data[DOMAIN].pop(temp_id, None)

    async def async_step_user(self, user_input=None):
        """Show login URL and JSESSIONID input form."""
        errors = {}
        if user_input is not None:
            jsessionid = user_input[CONF_JSESSIONID].strip()
            try:
                valid = await self._validate_jsessionid(jsessionid)
                if valid:
                    data = {
                        CONF_JSESSIONID: jsessionid,
                        CONF_SESSION_CREATED_AT: datetime.now(timezone.utc).isoformat(),
                    }
                    if self.reauth_entry:
                        return self.async_update_reload_and_abort(
                            self.reauth_entry,
                            data=data
                        )
                    return self.async_create_entry(title="SmartThings Find", data=data)
                else:
                    errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.error(f"Unexpected error during login: {e}", exc_info=True)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_JSESSIONID): str
            }),
            description_placeholders={"login_url": get_login_url()},
            errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        """Trigger reauthentication."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_user()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self.async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return SmartThingsFindOptionsFlowHandler(config_entry)


class SmartThingsFindOptionsFlowHandler(OptionsFlowWithConfigEntry):
    """Handle an options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""

        if user_input is not None:

            res = self.async_create_entry(title="", data=user_input)

            # Reload the integration entry to make sure the newly set options take effect
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
            return res

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.options.get(
                        CONF_UPDATE_INTERVAL, CONF_UPDATE_INTERVAL_DEFAULT
                    ),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=30)),
                vol.Optional(
                    CONF_ACTIVE_MODE_SMARTTAGS,
                    default=self.options.get(
                        CONF_ACTIVE_MODE_SMARTTAGS, CONF_ACTIVE_MODE_SMARTTAGS_DEFAULT
                    ),
                ): bool,
                vol.Optional(
                    CONF_ACTIVE_MODE_OTHERS,
                    default=self.options.get(
                        CONF_ACTIVE_MODE_OTHERS, CONF_ACTIVE_MODE_OTHERS_DEFAULT
                    ),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)