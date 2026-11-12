"""V-Guard Smart binary sensors."""

from __future__ import annotations

import time

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([VGuardOnlineSensor(coordinator, entry)])


class VGuardOnlineSensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entity_description = BinarySensorEntityDescription(key="online", name="Online", device_class=BinarySensorDeviceClass.CONNECTIVITY)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_online"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_name = f"{entry.title} Online"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data.get("serial", entry.entry_id))},
            name=entry.data.get("product_name", "V-Guard Inverter"),
            manufacturer=MANUFACTURER,
            model=entry.data.get("product_name", ""),
        )

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        if data.get("missing"):
            return False
        ts = data.get("captured_at")
        return bool(ts) and (time.time() - ts) < 900

    @property
    def extra_state_attributes(self):
        fields = (self.coordinator.data or {}).get("fields") or {}
        return {
            "wifi_ssid": fields.get("VG136"),
            "mac": fields.get("VG132"),
            "device_time": fields.get("VG109"),
        }
