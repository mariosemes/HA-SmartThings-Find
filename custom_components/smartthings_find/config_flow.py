"""Config flow for SmartThings Find integration."""
from typing import Any
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlowWithConfigEntry,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_AUTH_TOKEN,
    CONF_USER_ID,
    CONF_COUNTRY_CODE,
    CONF_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_DEFAULT,
    CONF_ACTIVE_MODE_SMARTTAGS,
    CONF_ACTIVE_MODE_SMARTTAGS_DEFAULT,
    CONF_ACTIVE_MODE_OTHERS,
    CONF_ACTIVE_MODE_OTHERS_DEFAULT,
)
from .api import SamsungFindApiClient, decode_jwt_payload, get_login_url

_LOGGER = logging.getLogger(__name__)


class SmartThingsFindConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartThings Find."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    reauth_entry: ConfigEntry | None = None

    async def _validate_credentials(self, auth_token: str, user_id: str, country_code: str) -> bool:
        """Validate credentials by making a test API call."""
        session = async_get_clientsession(self.hass)
        client = SamsungFindApiClient(
            session=session,
            auth_token=auth_token,
            user_id=user_id,
            country_code=country_code,
        )
        return await client.validate()

    async def async_step_user(self, user_input=None):
        """Show login URL and credential input form."""
        errors = {}
        if user_input is not None:
            auth_token = user_input[CONF_AUTH_TOKEN].strip()
            user_id = user_input[CONF_USER_ID].strip()
            country_code = user_input.get(CONF_COUNTRY_CODE, "US").strip().upper()

            try:
                payload = decode_jwt_payload(auth_token)
                if "exp" not in payload:
                    errors["base"] = "invalid_token"
            except ValueError:
                errors["base"] = "invalid_token"

            if not errors:
                try:
                    valid = await self._validate_credentials(auth_token, user_id, country_code)
                    if valid:
                        data = {
                            CONF_AUTH_TOKEN: auth_token,
                            CONF_USER_ID: user_id,
                            CONF_COUNTRY_CODE: country_code,
                        }
                        if self.reauth_entry:
                            return self.async_update_reload_and_abort(
                                self.reauth_entry,
                                data=data,
                            )
                        return self.async_create_entry(title="Samsung Find", data=data)
                    else:
                        errors["base"] = "invalid_auth"
                except Exception as e:
                    _LOGGER.error("Unexpected error during validation: %s", e, exc_info=True)
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AUTH_TOKEN): str,
                    vol.Required(CONF_USER_ID): str,
                    vol.Optional(CONF_COUNTRY_CODE, default="US"): str,
                }
            ),
            description_placeholders={"login_url": get_login_url()},
            errors=errors,
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
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
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
        if user_input is not None:
            res = self.async_create_entry(title="", data=user_input)
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
