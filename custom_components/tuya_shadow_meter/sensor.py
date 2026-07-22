"""Sensors for supported Tuya devices."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import TuyaCloudCoordinator
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class TuyaCloudSensorDescription(SensorEntityDescription):
    """Describe a Tuya cloud sensor."""

    scale: int | None = None
    value_fn: Callable[[Any], Any] | None = None


SENSORS: tuple[TuyaCloudSensorDescription, ...] = (
    TuyaCloudSensorDescription(
        key="device_state1",
        name="Channel 1 state",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:state-machine",
    ),
    TuyaCloudSensorDescription(
        key="cur_power1",
        name="Channel 1 power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
        suggested_display_precision=1,
    ),
    TuyaCloudSensorDescription(
        key="cur_current1",
        name="Channel 1 current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=3,
        suggested_display_precision=3,
    ),
    TuyaCloudSensorDescription(
        key="cur_voltage1",
        name="Channel 1 voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
        suggested_display_precision=1,
    ),
    TuyaCloudSensorDescription(
        key="total_energy1",
        name="Channel 1 total energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
        suggested_display_precision=3,
    ),
    TuyaCloudSensorDescription(
        key="today_acc_energy1",
        name="Channel 1 energy today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
        suggested_display_precision=3,
    ),
    TuyaCloudSensorDescription(
        key="power_type1",
        name="Channel 1 power state",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:alert-circle-outline",
    ),
    TuyaCloudSensorDescription(
        key="warn_power1",
        name="Channel 1 warning power threshold",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        scale=0,
    ),
    TuyaCloudSensorDescription(
        key="device_state2",
        name="Channel 2 state",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:state-machine",
    ),
    TuyaCloudSensorDescription(
        key="cur_power2",
        name="Channel 2 power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
        suggested_display_precision=1,
    ),
    TuyaCloudSensorDescription(
        key="cur_current2",
        name="Channel 2 current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=3,
        suggested_display_precision=3,
    ),
    TuyaCloudSensorDescription(
        key="cur_voltage2",
        name="Channel 2 voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
        suggested_display_precision=1,
    ),
    TuyaCloudSensorDescription(
        key="total_energy2",
        name="Channel 2 total energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
        suggested_display_precision=3,
    ),
    TuyaCloudSensorDescription(
        key="today_acc_energy2",
        name="Channel 2 energy today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
        suggested_display_precision=3,
    ),
    TuyaCloudSensorDescription(
        key="power_type2",
        name="Channel 2 power state",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:alert-circle-outline",
    ),
    TuyaCloudSensorDescription(
        key="warn_power2",
        name="Channel 2 warning power threshold",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        scale=0,
    ),
    TuyaCloudSensorDescription(
        key="all_energy",
        name="Total energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
        suggested_display_precision=3,
    ),
    TuyaCloudSensorDescription(
        key="net_state",
        name="Cloud connection state",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:cloud-check-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya cloud sensors."""
    coordinator: TuyaCloudCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TuyaCloudSensor(coordinator, device_id, description)
        for device_id in coordinator.hub.devices
        for description in SENSORS
    )


class TuyaCloudSensor(CoordinatorEntity[TuyaCloudCoordinator], SensorEntity):
    """A Tuya cloud sensor."""

    entity_description: TuyaCloudSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TuyaCloudCoordinator,
        device_id: str,
        description: TuyaCloudSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_{description.key}"
        self._attr_name = description.name

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        device_data = self.coordinator.data.get(self._device_id, {})
        value = device_data.get(self.entity_description.key)
        if value is None:
            return None

        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(value)

        scale = self.entity_description.scale
        if scale is not None and isinstance(value, (int, float)):
            return round(value / (10**scale), scale)

        return value

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        device_data = self.coordinator.data.get(self._device_id, {})
        return (
            super().available
            and self.entity_description.key in device_data
            and self._device_id in self.coordinator.hub.devices
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information."""
        device = self.coordinator.hub.devices.get(self._device_id)
        if device is None:
            return {
                "identifiers": {(DOMAIN, self._device_id)},
            }

        return {
            "identifiers": {(DOMAIN, device.id)},
            "name": device.name,
            "manufacturer": "Tuya",
            "model": device.product_name,
            "sw_version": getattr(device, "uuid", None),
        }
