"""V-Guard Smart buttons (one-shot commands)."""

from __future__ import annotations

import time

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER


@dataclass(frozen=True)
class VGuardButtonDescription(ButtonEntityDescription):
    command: str = ""


BUTTONS = (
    VGuardButtonDescription(
        key="battery_type_unlock",
        name="Battery Type Unlock (30 min)",
        command="VG105:1",
        icon="mdi:lock-open-variant",
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(VGuardButton(coordinator, entry, d) for d in BUTTONS)


class VGuardButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, entry: ConfigEntry, description: VGuardButtonDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data.get("serial", entry.entry_id))},
            name=entry.data.get("product_name", "V-Guard Inverter"),
            manufacturer=MANUFACTURER,
            model=entry.data.get("product_name", ""),
        )
        self._attr_name = f"{entry.title} {description.name}"

    @property
    def available(self):
        data = self.coordinator.data or {}
        if data.get("missing"):
            return False
        ts = data.get("captured_at")
        return bool(ts) and (time.time() - ts) < 900

    async def async_press(self):
        try:
            await self.coordinator.api.publish(self.entity_description.command)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"V-Guard publish failed: {err}") from err
        await self.coordinator.async_request_refresh()
