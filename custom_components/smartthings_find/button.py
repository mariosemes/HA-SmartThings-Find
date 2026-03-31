"""Button platform for SmartThings Find (ring device)."""
import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SmartThings Find button entities."""
    devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    entities = []
    for device in devices:
        entities.append(RingButton(hass, device, entry.entry_id))
    async_add_entities(entities)


class RingButton(ButtonEntity):
    """Button entity to make a Samsung Find device ring."""

    def __init__(self, hass: HomeAssistant, device, entry_id: str):
        """Initialize the button."""
        self._device_id = device["device_id"]
        self._entry_id = entry_id
        self._attr_unique_id = f"stf_ring_button_{self._device_id}"
        self._attr_name = f"{device['dev_name']} Ring"
        self._attr_icon = "mdi:nfc-search-variant"
        self._attr_device_info = device["ha_dev_info"]

        icon_url = device.get("icon_url")
        if icon_url:
            self._attr_entity_picture = icon_url

    async def async_press(self):
        """Handle the button press."""
        api_client = self.hass.data[DOMAIN][self._entry_id]["api_client"]
        success = await api_client.ring_device(self._device_id)
        if success:
            _LOGGER.info("Successfully rang device %s", self.name)
        else:
            _LOGGER.error("Failed to ring device %s", self.name)
