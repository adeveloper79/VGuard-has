"""V-Guard Smart sensors."""

from __future__ import annotations

from dataclasses import dataclass
import time

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER


@dataclass(frozen=True)
class VGuardSensorDescription(SensorEntityDescription):
    vg: str = ""
    scale: float = 1.0


SENSORS = (
    VGuardSensorDescription(key="grid_voltage", vg="VG014", name="Grid voltage", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=1.0, icon="mdi:transmission-tower"),
    VGuardSensorDescription(key="output_voltage", vg="VG015", name="Output voltage", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=1.0, icon="mdi:sine-wave"),
    VGuardSensorDescription(key="battery_voltage", vg="VG016", name="Battery voltage", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, scale=1.0, icon="mdi:car-battery"),
    VGuardSensorDescription(key="frequency_hz", vg="VG019", name="Frequency", native_unit_of_measurement="Hz", device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, scale=1.0, icon="mdi:sine-wave"),
    VGuardSensorDescription(key="load_current", vg="VG018", name="Load current", native_unit_of_measurement="A", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=1.0, icon="mdi:current-ac"),
    VGuardSensorDescription(key="apparent_power", vg="VG020", name="Apparent power", native_unit_of_measurement="VA", device_class=None, state_class=SensorStateClass.MEASUREMENT, scale=1.0, icon="mdi:gauge"),
    VGuardSensorDescription(key="wifi_rssi", vg="VG011", name="WiFi RSSI", native_unit_of_measurement="dBm", device_class=SensorDeviceClass.SIGNAL_STRENGTH, state_class=SensorStateClass.MEASUREMENT, scale=1.0, icon="mdi:wifi"),
    VGuardSensorDescription(key="aux_discharge", vg="VG017", name="Aux discharge (÷10)", native_unit_of_measurement="A", device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT, scale=10.0, icon="mdi:current-dc"),
    VGuardSensorDescription(key="energy_counter_a", vg="VG110", name="Energy counter A (raw)", native_unit_of_measurement=None, device_class=None, state_class=SensorStateClass.MEASUREMENT, scale=1.0, icon="mdi:counter"),
    VGuardSensorDescription(key="energy_counter_b", vg="VG042", name="Energy counter B (raw)", native_unit_of_measurement=None, device_class=None, state_class=SensorStateClass.MEASUREMENT, scale=1.0, icon="mdi:counter"),
)


def _num(v, scale=1.0):
    try:
        return round(float(v) / scale, 3)
    except (TypeError, ValueError):
        return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(VGuardSensor(coordinator, entry, desc) for desc in SENSORS)


class VGuardSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, description: VGuardSensorDescription):
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
        self._attr_icon = description.icon

    @property
    def available(self):
        data = self.coordinator.data or {}
        if data.get("missing"):
            return False
        ts = data.get("captured_at")
        return bool(ts) and (time.time() - ts) < 900

    @property
    def native_value(self):
        fields = (self.coordinator.data or {}).get("fields") or {}
        return _num(fields.get(self.entity_description.vg), self.entity_description.scale)

    @property
    def extra_state_attributes(self):
        fields = (self.coordinator.data or {}).get("fields") or {}
        attrs = {k.lower(): v for k, v in fields.items()}
        attrs["serial"] = self._entry.data.get("serial")
        attrs["frame_captured_at"] = (self.coordinator.data or {}).get("captured_at")
        return attrs
