"""Coordinator and Tuya SDK bridge for the two-channel meter."""

from __future__ import annotations

from datetime import timedelta
import hashlib
import hmac
import time
import logging
from typing import Any

import requests
from tuya_sharing import Manager, SharingDeviceListener, SharingTokenListener
from tuya_sharing.device import CustomerDevice
from tuya_sharing.exceptions import ApiRequestException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICE_ID,
    CONF_CLOUD_ACCESS_ID,
    CONF_CLOUD_ACCESS_SECRET,
    CONF_CLOUD_APP_USER_ID,
    CONF_CLOUD_REGION,
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
OPENAPI_ENDPOINTS = {
    "cn": "https://openapi.tuyacn.com",
    "us": "https://openapi.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "in": "https://openapi.tuyain.com",
}


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
        self.openapi = TuyaOpenApiClient.from_entry_data(
            {**entry.data, **entry.options}
        )

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

        if self.openapi is not None:
            properties = self.openapi.get_shadow_properties(self.device.id)
            if properties:
                return properties

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
            update_interval=timedelta(seconds=60)
            if hub.openapi is not None
            else timedelta(hours=6),
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


class TuyaOpenApiClient:
    """Small Tuya OpenAPI client for cloud shadow properties."""

    def __init__(
        self,
        access_id: str,
        access_secret: str,
        app_user_id: str,
        region: str,
    ) -> None:
        """Initialize the client."""
        self.access_id = access_id
        self.access_secret = access_secret
        self.app_user_id = app_user_id
        self.base_url = OPENAPI_ENDPOINTS[region]
        self.access_token = ""
        self.expire_at = 0.0

    @classmethod
    def from_entry_data(cls, data: dict[str, Any]) -> TuyaOpenApiClient | None:
        """Create a client from config entry data if credentials are present."""
        access_id = data.get(CONF_CLOUD_ACCESS_ID)
        access_secret = data.get(CONF_CLOUD_ACCESS_SECRET)
        app_user_id = data.get(CONF_CLOUD_APP_USER_ID)
        region = data.get(CONF_CLOUD_REGION, "cn")

        if not access_id or not access_secret or not app_user_id:
            return None

        return cls(access_id, access_secret, app_user_id, region)

    def get_shadow_properties(self, device_id: str) -> dict[str, Any]:
        """Return the device's cloud shadow properties."""
        self._ensure_access_token()
        response = self._request(
            "GET",
            SHADOW_PROPERTIES_PATH.format(device_id=device_id),
        )
        properties = response.get("result", {}).get("properties", [])
        return {
            prop["code"]: prop.get("value")
            for prop in properties
            if "code" in prop and "value" in prop
        }

    def _ensure_access_token(self) -> None:
        """Refresh the access token if needed."""
        if self.access_token and self.expire_at - 60 > time.time():
            return

        response = self._request("GET", "/v1.0/token?grant_type=1", use_token=False)
        result = response.get("result", {})
        self.access_token = result["access_token"]
        self.expire_at = time.time() + int(result.get("expire_time", 0))

    def _request(
        self,
        method: str,
        path: str,
        *,
        use_token: bool = True,
        body: str = "",
    ) -> dict[str, Any]:
        """Make a signed Tuya OpenAPI request."""
        token = self.access_token if use_token else ""
        timestamp = str(int(time.time() * 1000))
        payload = (
            self.access_id
            + token
            + timestamp
            + method
            + "\n"
            + hashlib.sha256(body.encode("utf-8")).hexdigest()
            + "\n\n/"
            + path.lstrip("/")
        )
        signature = hmac.new(
            self.access_secret.encode("latin-1"),
            payload.encode("latin-1"),
            hashlib.sha256,
        ).hexdigest().upper()
        headers = {
            "client_id": self.access_id,
            "sign": signature,
            "t": timestamp,
            "sign_method": "HMAC-SHA256",
        }
        if token:
            headers["access_token"] = token

        response = requests.request(
            method,
            self.base_url + path,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise UpdateFailed(
                f"Tuya OpenAPI error {data.get('code')}: {data.get('msg')}"
            )
        return data
