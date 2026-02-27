import logging
from homeassistant.components.device_tracker.config_entry import TrackerEntity as DeviceTrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .utils import get_sub_location, get_battery_level

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up SmartThings Find device tracker entities."""
    devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for device in devices:
        if 'subType' in device['data'] and device['data']['subType'] == 'CANAL2':
            entities += [SmartThingsDeviceTracker(hass, coordinator, device, "left")]
            entities += [SmartThingsDeviceTracker(hass, coordinator, device, "right")]
        entities += [SmartThingsDeviceTracker(hass, coordinator, device)]
    async_add_entities(entities)

class SmartThingsDeviceTracker(CoordinatorEntity, DeviceTrackerEntity):
    """Representation of a SmartTag device tracker."""

    def __init__(self, hass: HomeAssistant, coordinator, device, subDeviceName=None):
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self.hass = hass
        self.device = device['data']
        self.device_id = device['data']['dvceID']
        self.subDeviceName = subDeviceName

        # Cached sub-location computed once per coordinator update
        self._sub_op = {}
        self._sub_loc = {}

        self._attr_unique_id = f"stf_device_tracker_{device['data']['dvceID']}{'_' + subDeviceName if subDeviceName else ''}"
        self._attr_name = device['data']['modelName'] + (' ' + subDeviceName.capitalize() if subDeviceName else '')
        self._attr_device_info = device['ha_dev_info']
        self._attr_latitude = None
        self._attr_longitude = None

        if 'icons' in device['data'] and 'coloredIcon' in device['data']['icons']:
            self._attr_entity_picture = device['data']['icons']['coloredIcon']

    @callback
    def _handle_coordinator_update(self) -> None:
        """Cache sub-location once per coordinator cycle, then write state."""
        if self.subDeviceName and self.coordinator.data:
            data = self.coordinator.data.get(self.device_id) or {}
            self._sub_op, self._sub_loc = get_sub_location(
                data.get('ops', []), self.subDeviceName
            )
        self.async_write_ha_state()

    def async_write_ha_state(self):
        if not self.enabled:
            _LOGGER.debug(f"Ignoring state write request for disabled entity '{self.entity_id}'")
            return
        return super().async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return true if the device is available."""
        if not self.coordinator.last_update_success:
            return False
        if not self.coordinator.data:
            return False
        tag_data = self.coordinator.data.get(self.device_id)
        if not tag_data:
            _LOGGER.info(f"tag_data none for '{self.name}'; rendering state unavailable")
            return False
        if not tag_data.get('update_success', False):
            _LOGGER.info(f"Last update for '{self.name}' failed; rendering state unavailable")
            return False
        return True

    @property
    def source_type(self) -> str:
        return SourceType.GPS

    @property
    def latitude(self):
        """Return the latitude of the device."""
        if self.subDeviceName:
            return self._sub_loc.get('latitude')
        data = self.coordinator.data.get(self.device_id, {})
        if data.get('location_found'):
            return data.get('used_loc', {}).get('latitude')
        return None

    @property
    def longitude(self):
        """Return the longitude of the device."""
        if self.subDeviceName:
            return self._sub_loc.get('longitude')
        data = self.coordinator.data.get(self.device_id, {})
        if data.get('location_found'):
            return data.get('used_loc', {}).get('longitude')
        return None

    @property
    def location_accuracy(self):
        """Return the location accuracy of the device."""
        if self.subDeviceName:
            return self._sub_loc.get('gps_accuracy')
        data = self.coordinator.data.get(self.device_id, {})
        if data.get('location_found'):
            return data.get('used_loc', {}).get('gps_accuracy')
        return None

    @property
    def battery_level(self):
        """Return the battery level of the device."""
        if self.subDeviceName:
            return None
        data = self.coordinator.data.get(self.device_id, {})
        return get_battery_level(self.name, data.get('ops', []))

    @property
    def extra_state_attributes(self):
        tag_data = self.coordinator.data.get(self.device_id, {})
        device_data = self.device
        if self.subDeviceName:
            attrs = tag_data | self._sub_op | self._sub_loc
        else:
            attrs = dict(tag_data)  # shallow copy — don't mutate coordinator data
        used_loc = attrs.get('used_loc')
        attrs['last_seen'] = used_loc.get('gps_date') if used_loc else None
        return attrs | device_data
