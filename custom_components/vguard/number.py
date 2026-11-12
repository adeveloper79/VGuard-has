"""V-Guard Smart numbers (sliders)."""

from __future__ import annotations

import time

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER


@dataclass(frozen=True)
class VGuardNumberDescription(NumberEntityDescription):
    vg: str = ""
    invert: bool = False  # performance slider: shows 8 - VG035, writes VG035:(8 - n)


NUMBERS = (
    VGuardNumberDescription(
        key="battery_backup_level",
        vg="VG035",
        name="Battery Backup level",
        icon="mdi:battery-charging-outline",
        mode=NumberMode.SLIDER,
        native_min_value=1,
        native_max_value=7,
        native_step=1,
    ),
    VGuardNumberDescription(
        key="performance_level",
        vg="VG035",
        name="Performance level",
        icon="mdi:speedometer",
        mode=NumberMode.SLIDER,
        native_min_value=1,
        native_max_value=7,
        native_step=1,
        invert=True,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(VGuardNumber(coordinator, entry, d) for d in NUMBERS)


class VGuardNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, entry: ConfigEntry, description: VGuardNumberDescription):
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

    def _frame_value(self):
        fields = (self.coordinator.data or {}).get("fields") or {}
        v = fields.get(self.entity_description.vg)
        try:
            return float(str(v).strip())
        except (TypeError, ValueError):
            return None

    @property
    def native_value(self):
        v = self._frame_value()
        if v is None:
            return None
        return (8.0 - v) if self.entity_description.invert else v

    async def async_set_native_value(self, value: float):
        step = int(round(value))
        if step < 1 or step > 7:
            raise HomeAssistantError("Level must be between 1 and 7")
        if self.entity_description.invert:
            step = 8 - step
        try:
            await self.coordinator.api.publish(f"{self.entity_description.vg}:{step}")
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"V-Guard publish failed: {err}") from err
        await self.coordinator.async_request_refresh()
