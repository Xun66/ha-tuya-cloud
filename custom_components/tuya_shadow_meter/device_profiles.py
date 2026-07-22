"""Supported Tuya device profiles."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from tuya_sharing.device import CustomerDevice


@dataclass(frozen=True, kw_only=True)
class TuyaDeviceProfile:
    """Describe a supported Tuya device model."""

    product_id: str
    name_matches: tuple[str, ...]
    dp_id_to_code: Mapping[int, str]


TWO_CIRCUIT_METER_PROFILE = TuyaDeviceProfile(
    product_id="79a7z01v3n35kytb",
    name_matches=("双路", "Double Digital Meter"),
    dp_id_to_code=MappingProxyType(
        {
            101: "sync_request",
            102: "sync_response",
            103: "device_state1",
            104: "add_ele1",
            105: "cur_power1",
            106: "cur_current1",
            107: "cur_voltage1",
            108: "total_energy1",
            109: "today_acc_energy1",
            110: "power_type1",
            111: "warn_power1",
            112: "today_energy_add1",
            113: "device_state2",
            114: "add_ele2",
            115: "cur_power2",
            116: "cur_current2",
            117: "cur_voltage2",
            118: "total_energy2",
            119: "today_acc_energy2",
            120: "power_type2",
            121: "warn_power2",
            122: "today_energy_add2",
            123: "all_energy",
            124: "net_state",
        }
    ),
)

SUPPORTED_DEVICE_PROFILES = MappingProxyType(
    {
        TWO_CIRCUIT_METER_PROFILE.product_id: TWO_CIRCUIT_METER_PROFILE,
    }
)


def get_supported_device_profile(
    device: CustomerDevice,
) -> TuyaDeviceProfile | None:
    """Return the supported profile for a Tuya device."""
    product_id = getattr(device, "product_id", "")
    profile = SUPPORTED_DEVICE_PROFILES.get(product_id)
    if profile is not None:
        return profile

    product_name = getattr(device, "product_name", "") or ""
    name = getattr(device, "name", "") or ""
    for profile in SUPPORTED_DEVICE_PROFILES.values():
        if any(match in product_name or match in name for match in profile.name_matches):
            return profile

    return None


def get_supported_mq_profile(
    device: CustomerDevice,
    data: dict[str, Any],
) -> TuyaDeviceProfile | None:
    """Return the supported profile for a raw Tuya MQTT report."""
    product_key = data.get("productKey")
    if product_key is not None:
        return SUPPORTED_DEVICE_PROFILES.get(product_key)

    return get_supported_device_profile(device)
