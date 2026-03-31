"""Device tracker platform for SmartThings Find."""
import logging
from homeassistant.components.device_tracker.config_entry import TrackerEntity as DeviceTrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SmartThings Find device tracker entities."""
    devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for device in devices:
        entities.append(SmartThingsDeviceTracker(coordinator, device))
    async_add_entities(entities)


class SmartThingsDeviceTracker(CoordinatorEntity, DeviceTrackerEntity):
    """Representation of a Samsung Find device tracker."""

    def __init__(self, coordinator, device):
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device["device_id"]
        self._attr_unique_id = f"stf_device_tracker_{self._device_id}"
        self._attr_name = device["dev_name"]
        self._attr_device_info = device["ha_dev_info"]

        # Set entity picture from device icon
        icon_url = device.get("icon_url")
        if icon_url:
            self._attr_entity_picture = icon_url

    @property
    def available(self) -> bool:
        """Return true if the device is available."""
        if not self.coordinator.last_update_success:
            return False
        if not self.coordinator.data:
            return False
        tag_data = self.coordinator.data.get(self._device_id)
        if not tag_data:
            return False
        if not tag_data.get("update_success", False):
            return False
        return True

    @property
    def source_type(self) -> str:
        return SourceType.GPS

    @property
    def latitude(self):
        """Return the latitude of the device."""
        data = self.coordinator.data.get(self._device_id, {})
        if data.get("location_found"):
            loc = data.get("location")
            return loc.get("latitude") if loc else None
        return None

    @property
    def longitude(self):
        """Return the longitude of the device."""
        data = self.coordinator.data.get(self._device_id, {})
        if data.get("location_found"):
            loc = data.get("location")
            return loc.get("longitude") if loc else None
        return None

    @property
    def location_accuracy(self):
        """Return the location accuracy of the device."""
        data = self.coordinator.data.get(self._device_id, {})
        if data.get("location_found"):
            loc = data.get("location")
            return loc.get("gps_accuracy") if loc else None
        return None

    @property
    def battery_level(self):
        """Return the battery level of the device."""
        data = self.coordinator.data.get(self._device_id, {})
        return data.get("battery")

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        data = self.coordinator.data.get(self._device_id, {})
        loc = data.get("location") or {}
        attrs = {
            "last_seen": loc.get("gps_date"),
            "device_id": self._device_id,
            "device_type": self._device.get("data", {}).get("type"),
            "location_found": data.get("location_found", False),
        }
        # Include raw geolocation data for advanced users
        raw = data.get("raw", {})
        if raw:
            attrs["find_method"] = raw.get("method")
            attrs["find_node"] = raw.get("findNode", {}).get("host")
            attrs["rssi"] = raw.get("rssi")
            attrs["speed"] = raw.get("speed")
        return attrs
