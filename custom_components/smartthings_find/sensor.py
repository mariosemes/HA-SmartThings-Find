import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .utils import get_battery_level

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up SmartThings Find sensor entities."""
    devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for device in devices:
        entities += [DeviceBatterySensor(hass, coordinator, device)]
    async_add_entities(entities)


class DeviceBatterySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Device battery sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = '%'

    def __init__(self, hass: HomeAssistant, coordinator, device):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"stf_device_battery_{device['data']['dvceID']}"
        self._attr_name = f"{device['data']['modelName']} Battery"
        self.hass = hass
        self.device = device['data']
        self.device_id = device['data']['dvceID']
        self._attr_device_info = device['ha_dev_info']

    @property
    def available(self) -> bool:
        """Show unavailable if no data was received or last update failed."""
        if not self.coordinator.last_update_success:
            return False
        if not self.coordinator.data:
            return False
        tag_data = self.coordinator.data.get(self.device_id)
        if not tag_data:
            _LOGGER.info(f"battery sensor: tag_data none for '{self.name}'; rendering state unavailable")
            return False
        if not tag_data.get('update_success', False):
            _LOGGER.info(f"Last update for battery sensor '{self.name}' failed; rendering state unavailable")
            return False
        return True

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        ops = self.coordinator.data.get(self.device_id, {}).get('ops', [])
        return get_battery_level(self.name, ops)
