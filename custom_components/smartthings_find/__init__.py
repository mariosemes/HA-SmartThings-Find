from datetime import timedelta, datetime, timezone
import asyncio
import logging
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    CONF_JSESSIONID,
    CONF_SESSION_CREATED_AT,
    CONF_ACTIVE_MODE_OTHERS,
    CONF_ACTIVE_MODE_OTHERS_DEFAULT,
    CONF_ACTIVE_MODE_SMARTTAGS,
    CONF_ACTIVE_MODE_SMARTTAGS_DEFAULT,
    CONF_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_DEFAULT
)
from .utils import fetch_csrf, get_devices, get_device_location, create_stf_session

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.BUTTON, Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the SmartThings Find component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartThings Find from a config entry."""
    
    hass.data[DOMAIN][entry.entry_id] = {}

    # Load the jsessionid from the config and create a dedicated session for STF.
    # We use our own session (not the shared HA session) so:
    #   - the cookie jar is isolated from other integrations
    #   - the JSESSIONID cookie is properly scoped to smartthingsfind.samsung.com
    #   - a browser User-Agent is sent so Samsung doesn't reject requests as bots
    jsessionid = entry.data[CONF_JSESSIONID]
    session = create_stf_session(jsessionid)

    active_smarttags = entry.options.get(CONF_ACTIVE_MODE_SMARTTAGS, CONF_ACTIVE_MODE_SMARTTAGS_DEFAULT)
    active_others = entry.options.get(CONF_ACTIVE_MODE_OTHERS, CONF_ACTIVE_MODE_OTHERS_DEFAULT)

    hass.data[DOMAIN][entry.entry_id].update({
        CONF_ACTIVE_MODE_SMARTTAGS:  active_smarttags,
        CONF_ACTIVE_MODE_OTHERS: active_others,
    })

    # This raises ConfigEntryAuthFailed-exception if failed. So if we
    # can continue after fetch_csrf, we know that authentication was ok
    await fetch_csrf(hass, session, entry.entry_id)

    # Log session age so we can empirically learn how long JSESSIONID stays valid
    session_created_at = entry.data.get(CONF_SESSION_CREATED_AT)
    if session_created_at:
        created = datetime.fromisoformat(session_created_at)
        age = datetime.now(timezone.utc) - created
        _LOGGER.info(
            f"Session age: {age.days}d {age.seconds // 3600}h "
            f"(authenticated at {created.strftime('%Y-%m-%d %H:%M UTC')})"
        )
    else:
        _LOGGER.info("Session age unknown (no timestamp stored yet)")
    
    # Load all SmartThings-Find devices from the users account
    devices = await get_devices(hass, session, entry.entry_id)
    
    # Create an update coordinator. This is responsible to regularly
    # fetch data from STF and update the device_tracker and sensor
    # entities
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, CONF_UPDATE_INTERVAL_DEFAULT)
    coordinator = SmartThingsFindCoordinator(hass, session, devices, update_interval)

    # This is what makes the whole integration slow to load (around 10-15
    # seconds for my 15 devices) but it is the right way to do it. Only if
    # it succeeds, the integration will be marked as successfully loaded.
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id].update({
        CONF_JSESSIONID: jsessionid,
        "session": session,
        "coordinator": coordinator,
        "devices": devices
    })

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_success = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_success:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        # Close the dedicated session we created for this entry
        session: aiohttp.ClientSession = entry_data.get("session")
        if session and not session.closed:
            await session.close()
    else:
        _LOGGER.error(f"Unload failed: {unload_success}")
    return unload_success


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    """Return diagnostics for a config entry (Settings → Devices & Services → Download Diagnostics)."""
    session_created_at = entry.data.get(CONF_SESSION_CREATED_AT)
    session_age = None
    if session_created_at:
        created = datetime.fromisoformat(session_created_at)
        age = datetime.now(timezone.utc) - created
        session_age = f"{age.days}d {age.seconds // 3600}h"

    coordinator: SmartThingsFindCoordinator = (
        hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
    )

    return {
        "session": {
            "authenticated_at": session_created_at,
            "session_age": session_age,
        },
        "devices": [
            {
                "name": d["data"].get("modelName"),
                "id": d["data"].get("dvceID"),
                "type": d["data"].get("deviceTypeCode"),
                "model": d["data"].get("modelID"),
            }
            for d in hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("devices", [])
        ],
        "last_coordinator_update": (
            coordinator.last_update_success if coordinator else None
        ),
    }


class SmartThingsFindCoordinator(DataUpdateCoordinator):
    """Class to manage fetching SmartThings Find data."""

    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession, devices, update_interval : int):
        """Initialize the coordinator."""
        self.session = session
        self.devices = devices
        self.hass = hass
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval)  # Update interval for all entities
        )

    async def _async_update_data(self):
        """Fetch data from SmartThings Find."""
        try:
            _LOGGER.debug("Updating locations...")
            results = await asyncio.gather(
                *(
                    get_device_location(self.hass, self.session, device['data'], self.config_entry.entry_id)
                    for device in self.devices
                ),
                return_exceptions=True,
            )
            # Auth failures must propagate before we do anything else
            for result in results:
                if isinstance(result, ConfigEntryAuthFailed):
                    raise result
            tags = {}
            for device, result in zip(self.devices, results):
                dev_id = device['data']['dvceID']
                if isinstance(result, Exception):
                    # Shouldn't happen after our get_device_location fix, but be safe
                    _LOGGER.error("Unexpected error fetching '%s': %s", device['data'].get('modelName'), result)
                    tags[dev_id] = {
                        "dev_name": device['data'].get('modelName'),
                        "dev_id": dev_id,
                        "update_success": False,
                        "location_found": False,
                        "used_op": None,
                        "used_loc": None,
                        "ops": [],
                    }
                else:
                    tags[dev_id] = result
            _LOGGER.debug("Fetched %d locations", len(tags))
            return tags
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")