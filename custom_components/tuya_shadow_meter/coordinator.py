"""Coordinator and Tuya OpenAPI bridge for the two-channel meter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
import hmac
import time
import logging
from typing import Any

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_CLOUD_ACCESS_ID,
    CONF_CLOUD_ACCESS_SECRET,
    CONF_CLOUD_APP_USER_ID,
    CONF_CLOUD_REGION,
    CONF_DEVICE_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

SHADOW_PROPERTIES_PATH = "/v2.0/cloud/thing/{device_id}/shadow/properties"
OPENAPI_ENDPOINTS = {
    "cn": "https://openapi.tuyacn.com",
    "us": "https://openapi.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "in": "https://openapi.tuyain.com",
}


@dataclass
class TuyaMeterDevice:
    """Minimal device information for Home Assistant."""

    id: str
    name: str
    product_id: str
    product_name: str
    uuid: str | None = None


class TuyaMeterHub:
    """Wrap Tuya OpenAPI for Home Assistant."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the hub."""
        self.hass = hass
        self.entry = entry
        self.config = {**entry.data, **entry.options}
        self.openapi = TuyaOpenApiClient.from_entry_data(
            self.config
        )
        if self.openapi is None:
            raise UpdateFailed("Missing Tuya OpenAPI credentials")

        self.device: TuyaMeterDevice | None = None
        self.data: dict[str, Any] = {}

    async def async_initialize(self) -> None:
        """Load device info and initial shadow data."""
        self.device = await self.hass.async_add_executor_job(self._read_device)
        self.data = await self.async_refresh()

    async def async_refresh(self) -> dict[str, Any]:
        """Refresh the device properties."""
        device_id = self.config[CONF_DEVICE_ID]
        self.data = await self.hass.async_add_executor_job(
            self.openapi.get_shadow_properties, device_id
        )
        return self.data

    async def async_unload(self) -> None:
        """Unload the hub."""

    async def async_remove(self) -> None:
        """Remove the hub."""

    def _read_device(self) -> TuyaMeterDevice:
        """Read device information."""
        device_id = self.config[CONF_DEVICE_ID]
        details = self.openapi.get_device(device_id)
        return TuyaMeterDevice(
            id=details.get("id", device_id),
            name=details.get("name", "Tuya Shadow Meter"),
            product_id=details.get("product_id", ""),
            product_name=details.get("product_name", "Tuya Shadow Meter"),
            uuid=details.get("uuid"),
        )


class TuyaMeterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate meter state."""

    def __init__(self, hass: HomeAssistant, hub: TuyaMeterHub) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.hub = hub

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the current meter properties."""
        if self.hub.device is None:
            await self.hub.async_initialize()
            return dict(self.hub.data)

        return await self.hub.async_refresh()


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

    def get_device(self, device_id: str) -> dict[str, Any]:
        """Return device information."""
        self._ensure_access_token()
        response = self._request("GET", f"/v2.0/cloud/thing/{device_id}")
        return response.get("result", {})

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
