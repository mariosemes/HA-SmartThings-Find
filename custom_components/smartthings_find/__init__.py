"""SmartThings Find integration — Samsung Find API."""
from datetime import timedelta
import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    CONF_AUTH_TOKEN,
    CONF_USER_ID,
    CONF_COUNTRY_CODE,
    CONF_ACTIVE_MODE_OTHERS,
    CONF_ACTIVE_MODE_OTHERS_DEFAULT,
    CONF_ACTIVE_MODE_SMARTTAGS,
    CONF_ACTIVE_MODE_SMARTTAGS_DEFAULT,
    CONF_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_DEFAULT,
)
from .api import SamsungFindApiClient, get_device_name, get_device_icon, get_battery_from_device

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.BUTTON, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate config entry from v1 (old JSESSIONID API) to v2 (new JWT API)."""
    if config_entry.version == 1:
        _LOGGER.info("Migrating SmartThings Find config entry from v1 to v2")
        new_data = {
            CONF_AUTH_TOKEN: "",
            CONF_USER_ID: "",
            CONF_COUNTRY_CODE: "US",
        }
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2
        )
        _LOGGER.info("Migration complete — re-authentication required with new Samsung Find API")
        return True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN][entry.entry_id] = {}

    auth_token = entry.data.get(CONF_AUTH_TOKEN, "")
    user_id = entry.data.get(CONF_USER_ID, "")
    country_code = entry.data.get(CONF_COUNTRY_CODE, "US")

    if not auth_token or not user_id:
        raise ConfigEntryAuthFailed("No authentication credentials. Please re-authenticate.")

    session = async_get_clientsession(hass)
    api_client = SamsungFindApiClient(
        session=session,
        auth_token=auth_token,
        user_id=user_id,
        country_code=country_code,
    )

    try:
        valid = await api_client.validate()
        if not valid:
            raise ConfigEntryAuthFailed("Authentication failed with Samsung Find API")
    except ConfigEntryAuthFailed:
        raise

    active_smarttags = entry.options.get(CONF_ACTIVE_MODE_SMARTTAGS, CONF_ACTIVE_MODE_SMARTTAGS_DEFAULT)
    active_others = entry.options.get(CONF_ACTIVE_MODE_OTHERS, CONF_ACTIVE_MODE_OTHERS_DEFAULT)

    # Load all devices and fetch friendly names in parallel
    devices_raw = await api_client.get_all_devices()

    details_results = await asyncio.gather(
        *(api_client.get_device_details(dev.get("deviceId", "")) for dev in devices_raw),
        return_exceptions=True,
    )

    devices = []
    for dev, details_result in zip(devices_raw, details_results):
        device_id = dev.get("deviceId", "")
        details = details_result if isinstance(details_result, dict) else {}
        dev_name = get_device_name(dev, details)
        icon_url = get_device_icon(details)
        identifier = (DOMAIN, device_id)

        ha_dev = device_registry.async_get(hass).async_get_device({identifier})
        if ha_dev and ha_dev.disabled:
            _LOGGER.debug("Ignoring disabled device: '%s'", dev_name)
            continue

        ha_dev_info = DeviceInfo(
            identifiers={identifier},
            manufacturer="Samsung",
            name=dev_name,
            model=details.get("deviceModel") or dev.get("metadata", {}).get("vendor", {}).get("modelName", ""),
            configuration_url="https://samsungfind.samsung.com/",
        )
        devices.append({
            "data": dev,
            "details": details,
            "ha_dev_info": ha_dev_info,
            "device_id": device_id,
            "dev_name": dev_name,
            "icon_url": icon_url,
        })
        _LOGGER.debug("Adding device: %s (%s)", dev_name, device_id)

    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, CONF_UPDATE_INTERVAL_DEFAULT)
    coordinator = SmartThingsFindCoordinator(
        hass, api_client, devices, update_interval, entry,
        active_smarttags=active_smarttags, active_others=active_others,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id].update({
        "api_client": api_client,
        "coordinator": coordinator,
        "devices": devices,
    })

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_success = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_success:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_success


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
    devices = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("devices", [])

    return {
        "auth": {
            "user_id": entry.data.get(CONF_USER_ID),
            "country_code": entry.data.get(CONF_COUNTRY_CODE),
        },
        "devices": [
            {
                "name": d.get("dev_name"),
                "id": d.get("device_id"),
                "type": d["data"].get("type"),
                "model": d["data"].get("metadata", {}).get("vendor", {}).get("modelName"),
            }
            for d in devices
        ],
        "last_coordinator_update": (
            coordinator.last_update_success if coordinator else None
        ),
    }


class SmartThingsFindCoordinator(DataUpdateCoordinator):
    """Manage fetching Samsung Find data."""

    def __init__(self, hass, api_client, devices, update_interval, config_entry,
                 active_smarttags=True, active_others=False):
        self.api_client = api_client
        self.devices = devices
        self._active_smarttags = active_smarttags
        self._active_others = active_others
        super().__init__(
            hass, _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        try:
            _LOGGER.debug("Updating locations for %d devices...", len(self.devices))

            # Request location updates for active-mode devices
            active_requests = []
            for device in self.devices:
                dev_type = device["data"].get("type", "")
                active = (
                    (dev_type == "TAG" and self._active_smarttags)
                    or (dev_type != "TAG" and self._active_others)
                )
                if active:
                    active_requests.append(
                        self.api_client.request_location_update(device["device_id"])
                    )

            if active_requests:
                await asyncio.gather(*active_requests, return_exceptions=True)

            # Fetch locations in parallel
            results = await asyncio.gather(
                *(self.api_client.get_device_location(d["device_id"]) for d in self.devices),
                return_exceptions=True,
            )

            for result in results:
                if isinstance(result, ConfigEntryAuthFailed):
                    raise result

            tags = {}
            for device, result in zip(self.devices, results):
                device_id = device["device_id"]
                if isinstance(result, Exception):
                    _LOGGER.error("Error fetching '%s': %s", device.get("dev_name"), result)
                    tags[device_id] = {
                        "dev_name": device.get("dev_name"),
                        "dev_id": device_id,
                        "update_success": False,
                        "location_found": False,
                        "location": None,
                        "battery": None,
                        "raw": {},
                    }
                else:
                    result["dev_name"] = device.get("dev_name")
                    if result.get("battery") is None:
                        result["battery"] = get_battery_from_device(device["data"])
                    tags[device_id] = result

            _LOGGER.debug("Fetched %d locations", len(tags))
            return tags

        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
