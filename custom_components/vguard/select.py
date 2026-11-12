"""V-Guard Smart selects (numeric options mapped via frame)."""

from __future__ import annotations

import time

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER


@dataclass(frozen=True)
class VGuardSelectDescription(SelectEntityDescription):
    vg: str = ""
    options_map: tuple = ()  # ((label, command_value), ...)


SELECTS = (
    VGuardSelectDescription(
        key="reserve_power",
        vg="VG035",
        name="Reserve Power at",
        icon="mdi:clock-time-six",
        options_map=(
            ("No cut", "0"),
            ("06:00 PM", "1"),
            ("07:00 PM", "2"),
            ("08:00 PM", "3"),
            ("09:00 PM", "4"),
            ("10:00 PM", "5"),
            ("11:00 PM", "6"),
            ("00:00 AM", "7"),
        ),
    ),
    VGuardSelectDescription(
        key="force_cut_duration",
        vg="VG037",
        name="Force Cut Duration",
        icon="mdi:timer-outline",
        options_map=(
            ("Off", "0"),
            ("30 min", "30"),
            ("1 hour", "60"),
            ("2 hours", "120"),
            ("3 hours", "180"),
            ("4 hours", "240"),
        ),
    ),
    VGuardSelectDescription(
        key="load_alarm_threshold",
        vg="VG050",
        name="Load Exceeds Alarm (%)",
        icon="mdi:alarm-bell",
        options_map=(
            ("50%", "50"),
            ("60%", "60"),
            ("70%", "70"),
            ("80%", "80"),
            ("90%", "90"),
            ("100%", "100"),
        ),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(VGuardSelect(coordinator, entry, d) for d in SELECTS)


class VGuardSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, entry: ConfigEntry, description: VGuardSelectDescription):
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
        self._attr_options = [label for label, _ in description.options_map]

    @property
    def available(self):
        data = self.coordinator.data or {}
        if data.get("missing"):
            return False
        ts = data.get("captured_at")
        return bool(ts) and (time.time() - ts) < 900

    def _frame_value(self) -> str | None:
        fields = (self.coordinator.data or {}).get("fields") or {}
        v = fields.get(self.entity_description.vg)
        if v is None:
            return None
        try:
            return str(int(float(str(v).strip())))
        except (TypeError, ValueError):
            return None

    @property
    def current_option(self):
        raw = self._frame_value()
        if raw is None:
            return None
        for label, value in self.entity_description.options_map:
            if value == raw:
                return label
        return None

    async def async_select_option(self, option: str):
        values = dict(self.entity_description.options_map)
        try:
            command_value = values[option]
        except KeyError:
            raise HomeAssistantError(f"Unknown option {option!r} for {self.entity_description.key}")
        try:
            await self.coordinator.api.publish(f"{self.entity_description.vg}:{command_value}")
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"V-Guard publish failed: {err}") from err
        await self.coordinator.async_request_refresh()
