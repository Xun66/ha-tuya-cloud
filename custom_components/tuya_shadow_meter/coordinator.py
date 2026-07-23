"""Coordinator and Tuya sharing MQTT bridge for supported devices."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from tuya_sharing import Manager, SharingDeviceListener
from tuya_sharing.customerapi import ApiRequestException, SharingTokenListener
from tuya_sharing.device import CustomerDevice

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICE_IDS,
    CONF_ENDPOINT,
    CONF_TERMINAL_ID,
    CONF_TOKEN_INFO,
    CONF_USER_CODE,
    DOMAIN,
    TUYA_CLIENT_ID,
)
from .device_profiles import (
    get_supported_device_profile,
    get_supported_mq_profile,
)

_LOGGER = logging.getLogger(__name__)

AUTH_ERROR_CODES = {
    "-9999999",
    "1010",
    "1011",
    "1012",
    "1013",
    "1014",
    "1015",
    "1016",
    "1106",
    "2406",
}
AUTH_ERROR_WORDS = (
    "auth",
    "invalid sign",
    "login",
    "permission",
    "sign invalid",
    "token",
    "unauthorized",
)


class TuyaCloudAuthError(Exception):
    """Raised when Tuya sharing credentials need reauthentication."""


@dataclass(frozen=True)
class TuyaDeviceUpdate:
    """A device update delivered from the Tuya sharing SDK."""

    device: CustomerDevice
    updated_status_properties: list[str] | None = None
    dp_timestamps: dict[str, int] | None = None


class TuyaCloudHub(SharingDeviceListener, SharingTokenListener):
    """Wrap Tuya sharing SDK for Home Assistant."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the hub."""
        self.hass = hass
        self.entry = entry
        self.manager: Manager | None = None
        self.coordinator: TuyaCloudCoordinator | None = None
        self.devices: dict[str, CustomerDevice] = {}
        self.data: dict[str, dict[str, Any]] = {}
        self.dp_timestamps: dict[str, dict[str, int]] = {}
        self._logged_raw_updates: set[str] = set()

    async def async_initialize(self) -> None:
        """Load devices and start Tuya sharing MQTT."""
        await self.hass.async_add_executor_job(self._initialize)

    async def async_unload(self) -> None:
        """Unload the hub for reload/shutdown."""
        await self.hass.async_add_executor_job(self._stop_mq)

    async def async_remove(self) -> None:
        """Remove the hub and expire the Tuya terminal session."""
        await self.hass.async_add_executor_job(self._remove)

    async def async_get_supported_devices(self) -> dict[str, CustomerDevice]:
        """Return supported devices visible to this Tuya account."""
        return await self.hass.async_add_executor_job(self._get_supported_devices)

    def update_token(self, token_info: dict[str, Any]) -> None:
        """Persist refreshed Tuya sharing tokens."""
        self.hass.loop.call_soon_threadsafe(self._async_update_token, token_info)

    def update_device(
        self,
        device: CustomerDevice,
        updated_status_properties: list[str] | None = None,
        dp_timestamps: dict[str, int] | None = None,
    ) -> None:
        """Receive a device update from Tuya sharing MQTT."""
        if not self._is_supported_device(device):
            return

        self.hass.loop.call_soon_threadsafe(
            self._async_handle_device_update,
            TuyaDeviceUpdate(device, updated_status_properties, dp_timestamps),
        )

    def add_device(self, device: CustomerDevice) -> None:
        """Receive a newly bound device event from Tuya sharing MQTT."""
        if not self._is_supported_device(device):
            return
        if CONF_DEVICE_IDS not in self.entry.options:
            return
        if not self._is_enabled_device(device.id):
            return

        setattr(device, "set_up", True)
        self.hass.loop.call_soon_threadsafe(
            self._async_handle_device_update,
            TuyaDeviceUpdate(device),
        )

    def remove_device(self, device_id: str) -> None:
        """Receive a removed-device event from Tuya sharing MQTT."""
        if device_id not in self.devices:
            return
        self.hass.loop.call_soon_threadsafe(self._async_remove_device, device_id)

    def _initialize(self) -> None:
        """Initialize Tuya manager and MQTT in an executor thread."""
        token_info = self.entry.data[CONF_TOKEN_INFO]
        self.manager = Manager(
            TUYA_CLIENT_ID,
            self.entry.data[CONF_USER_CODE],
            self.entry.data[CONF_TERMINAL_ID],
            self.entry.data[CONF_ENDPOINT],
            token_info,
            self,
        )
        try:
            self.manager.update_device_cache()
        except ApiRequestException as err:
            if _is_auth_error(err):
                raise TuyaCloudAuthError(err.error_message) from err
            raise UpdateFailed(
                f"Failed to load Tuya devices: {err.error_message}"
            ) from err

        for device in self.manager.device_map.values():
            if not self._is_supported_device(device):
                continue
            if not self._is_enabled_device(device.id):
                continue
            setattr(device, "set_up", True)
            self.devices[device.id] = device
            self.data[device.id] = dict(device.status)

        if not self.devices:
            raise UpdateFailed("No supported Tuya devices found")

        self.manager.add_device_listener(self)
        self.manager.refresh_mq()
        if self.manager.mq is not None:
            self.manager.mq.add_message_listener(self._on_raw_mq_message)

    def _stop_mq(self) -> None:
        """Stop the MQTT thread."""
        if self.manager is None:
            return
        if self.manager.mq is not None:
            self.manager.mq.stop()
        try:
            self.manager.remove_device_listener(self)
        except KeyError:
            pass

    def _remove(self) -> None:
        """Expire the Tuya terminal session."""
        manager = self.manager
        self._stop_mq()
        if manager is not None:
            manager.unload()

    def _get_supported_devices(self) -> dict[str, CustomerDevice]:
        """Refresh the Tuya cache and return supported devices."""
        if self.manager is None:
            return {}

        try:
            self.manager.update_device_cache()
        except ApiRequestException as err:
            if _is_auth_error(err):
                raise TuyaCloudAuthError(err.error_message) from err
            raise
        return {
            device.id: device
            for device in self.manager.device_map.values()
            if self._is_supported_device(device)
        }

    def _async_update_token(self, token_info: dict[str, Any]) -> None:
        """Update stored token info in Home Assistant."""
        data = dict(self.entry.data)
        data[CONF_TOKEN_INFO] = token_info
        self.hass.config_entries.async_update_entry(self.entry, data=data)

    def _async_handle_device_update(self, update: TuyaDeviceUpdate) -> None:
        """Merge a Tuya device update into coordinator data."""
        device = update.device
        self.devices[device.id] = device
        current = dict(self.data.get(device.id, {}))
        if update.updated_status_properties:
            for code in update.updated_status_properties:
                if code in device.status:
                    current[code] = device.status[code]
        else:
            current.update(device.status)
        self.data[device.id] = current

        if update.dp_timestamps:
            current_timestamps = dict(self.dp_timestamps.get(device.id, {}))
            current_timestamps.update(update.dp_timestamps)
            self.dp_timestamps[device.id] = current_timestamps

        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(dict(self.data))

    def _on_raw_mq_message(self, msg: dict[str, Any]) -> None:
        """Receive raw Tuya MQTT and map supported dpIds directly."""
        if msg.get("protocol") != 4:
            return

        data = msg.get("data", {})
        device_id = data.get("devId")
        device = self.devices.get(device_id)
        if device is None:
            return

        profile = get_supported_mq_profile(device, data)
        if profile is None:
            return

        updates: dict[str, Any] = {}
        timestamps: dict[str, int] = {}
        for item in data.get("status", []):
            code = profile.dp_id_to_code.get(item.get("dpId"))
            if code is None or "value" not in item:
                continue
            updates[code] = item["value"]
            if timestamp := item.get("t"):
                timestamps[code] = timestamp

        if not updates:
            return

        if device_id not in self._logged_raw_updates:
            _LOGGER.info(
                "Received Tuya MQTT status for %s: %s",
                device_id,
                ", ".join(updates),
            )
            self._logged_raw_updates.add(device_id)

        self.hass.loop.call_soon_threadsafe(
            self._async_handle_raw_status,
            device_id,
            updates,
            timestamps,
        )

    def _async_handle_raw_status(
        self,
        device_id: str,
        updates: dict[str, Any],
        timestamps: dict[str, int],
    ) -> None:
        """Merge raw MQTT status values into coordinator data."""
        current = dict(self.data.get(device_id, {}))
        current.update(updates)
        self.data[device_id] = current

        if timestamps:
            current_timestamps = dict(self.dp_timestamps.get(device_id, {}))
            current_timestamps.update(timestamps)
            self.dp_timestamps[device_id] = current_timestamps

        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(dict(self.data))

    def _async_remove_device(self, device_id: str) -> None:
        """Remove a device from coordinator data."""
        self.devices.pop(device_id, None)
        self.data.pop(device_id, None)
        self.dp_timestamps.pop(device_id, None)
        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(dict(self.data))

    def _is_enabled_device(self, device_id: str) -> bool:
        """Return whether a supported device is enabled for this entry."""
        device_ids = self.entry.options.get(CONF_DEVICE_IDS)
        return device_ids is None or device_id in device_ids

    @staticmethod
    def _is_supported_device(device: CustomerDevice) -> bool:
        """Return whether the Tuya device matches a supported profile."""
        return get_supported_device_profile(device) is not None


class TuyaCloudCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinate supported device state."""

    def __init__(self, hass: HomeAssistant, hub: TuyaCloudHub) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self.hub = hub
        self.hub.coordinator = self

    async def async_start(self) -> None:
        """Initialize data and MQTT."""
        await self.hub.async_initialize()
        self.async_set_updated_data(dict(self.hub.data))

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Return the latest in-memory device data."""
        return dict(self.hub.data)


def _is_auth_error(err: ApiRequestException) -> bool:
    """Return whether a Tuya API error looks like expired credentials."""
    error_code = str(err.error_code)
    if error_code in AUTH_ERROR_CODES:
        return True

    message = str(err.error_message).lower()
    return any(word in message for word in AUTH_ERROR_WORDS)
