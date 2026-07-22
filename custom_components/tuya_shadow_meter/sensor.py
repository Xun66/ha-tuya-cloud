"""Sensors for the Tuya two-channel electricity meter."""

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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import TuyaMeterCoordinator
from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class TuyaMeterSensorDescription(SensorEntityDescription):
    """Describe a Tuya meter sensor."""

    scale: int | None = None
    value_fn: Callable[[Any], Any] | None = None


SENSORS: tuple[TuyaMeterSensorDescription, ...] = (
    TuyaMeterSensorDescription(
        key="device_state1",
        translation_key="device_state1",
        icon="mdi:state-machine",
    ),
    TuyaMeterSensorDescription(
        key="cur_power1",
        translation_key="cur_power1",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
    ),
    TuyaMeterSensorDescription(
        key="cur_current1",
        translation_key="cur_current1",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=3,
    ),
    TuyaMeterSensorDescription(
        key="cur_voltage1",
        translation_key="cur_voltage1",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
    ),
    TuyaMeterSensorDescription(
        key="total_energy1",
        translation_key="total_energy1",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
    ),
    TuyaMeterSensorDescription(
        key="today_acc_energy1",
        translation_key="today_acc_energy1",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
    ),
    TuyaMeterSensorDescription(
        key="power_type1",
        translation_key="power_type1",
        icon="mdi:alert-circle-outline",
    ),
    TuyaMeterSensorDescription(
        key="warn_power1",
        translation_key="warn_power1",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        scale=0,
    ),
    TuyaMeterSensorDescription(
        key="device_state2",
        translation_key="device_state2",
        icon="mdi:state-machine",
    ),
    TuyaMeterSensorDescription(
        key="cur_power2",
        translation_key="cur_power2",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
    ),
    TuyaMeterSensorDescription(
        key="cur_current2",
        translation_key="cur_current2",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=3,
    ),
    TuyaMeterSensorDescription(
        key="cur_voltage2",
        translation_key="cur_voltage2",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
    ),
    TuyaMeterSensorDescription(
        key="total_energy2",
        translation_key="total_energy2",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
    ),
    TuyaMeterSensorDescription(
        key="today_acc_energy2",
        translation_key="today_acc_energy2",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
    ),
    TuyaMeterSensorDescription(
        key="power_type2",
        translation_key="power_type2",
        icon="mdi:alert-circle-outline",
    ),
    TuyaMeterSensorDescription(
        key="warn_power2",
        translation_key="warn_power2",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        scale=0,
    ),
    TuyaMeterSensorDescription(
        key="all_energy",
        translation_key="all_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=3,
    ),
    TuyaMeterSensorDescription(
        key="net_state",
        translation_key="net_state",
        icon="mdi:cloud-check-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya meter sensors."""
    coordinator: TuyaMeterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TuyaMeterSensor(coordinator, description) for description in SENSORS
    )


class TuyaMeterSensor(CoordinatorEntity[TuyaMeterCoordinator], SensorEntity):
    """A Tuya meter sensor."""

    entity_description: TuyaMeterSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TuyaMeterCoordinator,
        description: TuyaMeterSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        device = coordinator.hub.device
        assert device is not None
        self._device_id = device.id
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        value = self.coordinator.data.get(self.entity_description.key)
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
        return (
            super().available
            and self.entity_description.key in self.coordinator.data
            and self.coordinator.hub.device is not None
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information."""
        device = self.coordinator.hub.device
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
