"""Coordinator and Tuya SDK bridge for the two-channel meter."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from tuya_sharing import Manager, SharingDeviceListener, SharingTokenListener
from tuya_sharing.device import CustomerDevice
from tuya_sharing.exceptions import ApiRequestException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICE_ID,
    CONF_ENDPOINT,
    CONF_TERMINAL_ID,
    CONF_TOKEN_INFO,
    CONF_USER_CODE,
    DOMAIN,
    SUPPORTED_PRODUCT_ID,
    SUPPORTED_PRODUCT_NAME,
    TUYA_CLIENT_ID,
)

_LOGGER = logging.getLogger(__name__)

SHADOW_PROPERTIES_PATH = "/v2.0/cloud/thing/{device_id}/shadow/properties"


class TuyaMeterHub(SharingDeviceListener, SharingTokenListener):
    """Wrap the Tuya sharing SDK for Home Assistant."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the hub."""
        self.hass = hass
        self.entry = entry
        self.manager = Manager(
            TUYA_CLIENT_ID,
            entry.data[CONF_USER_CODE],
            entry.data[CONF_TERMINAL_ID],
            entry.data[CONF_ENDPOINT],
            entry.data[CONF_TOKEN_INFO],
            self,
        )
        self.device: CustomerDevice | None = None
        self.coordinator: TuyaMeterCoordinator | None = None
        self.data: dict[str, Any] = {}

    async def async_initialize(self, coordinator: TuyaMeterCoordinator) -> None:
        """Load device data and start cloud push."""
        self.coordinator = coordinator
        await self.hass.async_add_executor_job(
            update_minimal_device_cache, self.manager
        )
        self.device = self._select_device()

        if self.device is None:
            raise UpdateFailed("No supported two-channel Tuya meter was found")

        self.data = await self.hass.async_add_executor_job(self._read_properties)
        self.manager.add_device_listener(self)
        await self.hass.async_add_executor_job(self.manager.refresh_mq)

    async def async_refresh(self) -> dict[str, Any]:
        """Refresh the device properties."""
        if self.device is None:
            await self.hass.async_add_executor_job(
                update_minimal_device_cache, self.manager
            )
            self.device = self._select_device()
            if self.device is None:
                raise UpdateFailed("No supported two-channel Tuya meter was found")

        self.data = await self.hass.async_add_executor_job(self._read_properties)
        return self.data

    async def async_unload(self) -> None:
        """Stop cloud push and detach listeners."""
        try:
            self.manager.remove_device_listener(self)
        except KeyError:
            pass

        if self.manager.mq is not None:
            await self.hass.async_add_executor_job(self.manager.mq.stop)

    async def async_remove(self) -> None:
        """Revoke the Tuya terminal token."""
        await self.async_unload()
        await self.hass.async_add_executor_job(self.manager.unload)

    def _select_device(self) -> CustomerDevice | None:
        """Select the configured or first supported meter device."""
        configured_device_id = self.entry.data.get(CONF_DEVICE_ID)
        if configured_device_id:
            device = self.manager.device_map.get(configured_device_id)
            return device if device and _is_supported_device(device) else None

        for device in self.manager.device_map.values():
            if _is_supported_device(device):
                return device

        return None

    def _read_properties(self) -> dict[str, Any]:
        """Read properties using the best API available for this login mode."""
        assert self.device is not None

        try:
            response = self.manager.customer_api.get(
                SHADOW_PROPERTIES_PATH.format(device_id=self.device.id)
            )
            properties = response.get("result", {}).get("properties", [])
            if properties:
                return {
                    prop["code"]: prop.get("value")
                    for prop in properties
                    if "code" in prop and "value" in prop
                }
        except ApiRequestException as err:
            _LOGGER.debug("Shadow property read failed, using SDK cache: %s", err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Unexpected shadow property read failure: %s", err)

        return dict(getattr(self.device, "status", {}) or {})

    def update_device(
        self,
        device: CustomerDevice,
        updated_status_properties: list[str] | None = None,
        dp_timestamps: dict | None = None,
    ) -> None:
        """Handle SDK device updates from the MQTT thread."""
        if self.device is None or device.id != self.device.id:
            return

        self.device = device
        self.data.update(getattr(device, "status", {}) or {})
        self.hass.loop.call_soon_threadsafe(self._async_publish_update)

    def add_device(self, device: CustomerDevice) -> None:
        """Handle newly shared devices."""
        if self.device is None and _is_supported_device(device):
            self.device = device
            self.data.update(getattr(device, "status", {}) or {})
            self.hass.loop.call_soon_threadsafe(self._async_publish_update)

    def remove_device(self, device_id: str) -> None:
        """Handle removed devices."""
        if self.device and device_id == self.device.id:
            self.device = None
            self.data = {}
            self.hass.loop.call_soon_threadsafe(self._async_publish_update)

    def update_token(self, token_info: dict[str, Any]) -> None:
        """Persist refreshed Tuya token info."""
        self.hass.loop.call_soon_threadsafe(self._async_update_token, token_info)

    @callback
    def _async_update_token(self, token_info: dict[str, Any]) -> None:
        """Update the config entry with refreshed token info."""
        new_data = dict(self.entry.data)
        new_data[CONF_TOKEN_INFO] = token_info
        self.hass.config_entries.async_update_entry(self.entry, data=new_data)

    @callback
    def _async_publish_update(self) -> None:
        """Publish the latest device data to the coordinator."""
        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(dict(self.data))


class TuyaMeterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate meter state."""

    def __init__(self, hass: HomeAssistant, hub: TuyaMeterHub) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=6),
        )
        self.hub = hub

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the current meter properties."""
        if self.hub.coordinator is None:
            await self.hub.async_initialize(self)
            return dict(self.hub.data)

        return await self.hub.async_refresh()


def _is_supported_device(device: CustomerDevice) -> bool:
    """Return whether this device looks like the supported meter."""
    product_id = getattr(device, "product_id", "")
    product_name = getattr(device, "product_name", "") or getattr(device, "name", "")
    status = getattr(device, "status", {}) or {}

    return (
        product_id == SUPPORTED_PRODUCT_ID
        or SUPPORTED_PRODUCT_NAME in product_name
        or {"cur_power1", "cur_power2", "all_energy"}.issubset(status)
    )


def update_minimal_device_cache(manager: Manager) -> None:
    """Update device cache without querying generic Tuya specifications."""
    manager.device_map.clear()
    homes = manager.home_repository.query_homes()
    manager.user_homes = homes

    for home in homes:
        response = manager.customer_api.get(
            "/v1.0/m/life/ha/home/devices", {"homeId": home.id}
        )
        if not response.get("success", False):
            continue

        for item in response.get("result", []):
            device = CustomerDevice(**item)
            device.status = _normalize_status(getattr(device, "status", {}) or {})
            device.set_up = True
            device.support_local = False
            device.function = {}
            device.status_range = {}
            manager.device_map[device.id] = device


def _normalize_status(status: Any) -> dict[str, Any]:
    """Normalize Tuya status payloads into a code-value mapping."""
    if isinstance(status, dict):
        return dict(status)

    if isinstance(status, list):
        return {
            item["code"]: item.get("value")
            for item in status
            if isinstance(item, dict) and "code" in item and "value" in item
        }

    return {}
