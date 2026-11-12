"""V-Guard Smart switches (NOUS-published on/off commands)."""

from __future__ import annotations

import time

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER


@dataclass(frozen=True)
class VGuardSwitchDescription(SwitchEntityDescription):
    vg: str = ""


SWITCHES = (
    VGuardSwitchDescription(key="turbo_charging", vg="VG099", name="Turbo Charging", icon="mdi:battery-charging-high"),
    VGuardSwitchDescription(key="appliance_mode", vg="VG036", name="Appliance Mode", icon="mdi:power-plug"),
    VGuardSwitchDescription(key="holiday_mode", vg="VG100", name="Holiday Mode", icon="mdi:palm-tree"),
    VGuardSwitchDescription(key="extra_backup", vg="VG072", name="Extra Backup Mode", icon="mdi:battery-clock"),
    VGuardSwitchDescription(key="force_cut", vg="VG038", name="Grid Force Cut", icon="mdi:transmission-tower-off"),
    VGuardSwitchDescription(key="day_time_load_usage", vg="VG185", name="Day-time Load Usage", icon="mdi:weather-sunny"),
    VGuardSwitchDescription(key="advanced_low_battery_alarm", vg="VG071", name="Advance Low Battery Alarm", icon="mdi:battery-alert"),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(VGuardSwitch(coordinator, entry, d) for d in SWITCHES)


class VGuardSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, entry: ConfigEntry, description: VGuardSwitchDescription):
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
            return int(float(str(v).strip()))
        except (TypeError, ValueError):
            return None

    @property
    def is_on(self):
        v = self._frame_value()
        if v is None:
            return None
        if self.entity_description.key == "advanced_low_battery_alarm":
            return v == 1100
        return bool(v)

    async def async_turn_on(self, **kwargs):
        await self._publish("1")

    async def async_turn_off(self, **kwargs):
        await self._publish("0")

    async def _publish(self, bit: str):
        try:
            await self.coordinator.api.publish(f"{self.entity_description.vg}:{bit}")
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"V-Guard publish failed: {err}") from err
        await self.coordinator.async_request_refresh()
