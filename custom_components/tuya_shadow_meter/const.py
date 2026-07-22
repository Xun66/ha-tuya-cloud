"""Constants for the Tuya shadow meter integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "tuya_shadow_meter"
PLATFORMS = [Platform.SENSOR]

CONF_DEVICE_ID = "device_id"
CONF_CLOUD_ACCESS_ID = "cloud_access_id"
CONF_CLOUD_ACCESS_SECRET = "cloud_access_secret"
CONF_CLOUD_APP_USER_ID = "cloud_app_user_id"
CONF_CLOUD_REGION = "cloud_region"

SUPPORTED_PRODUCT_ID = "79a7z01v3n35kytb"
SUPPORTED_PRODUCT_NAME = "双路"
