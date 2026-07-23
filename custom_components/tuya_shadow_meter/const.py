"""Constants for Tuya Cloud."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "tuya_shadow_meter"
PLATFORMS = [Platform.SENSOR]

CONF_ENDPOINT = "endpoint"
CONF_DEVICE_IDS = "device_ids"
CONF_TERMINAL_ID = "terminal_id"
CONF_TOKEN_INFO = "token_info"
CONF_USER_CODE = "user_code"

TUYA_CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
TUYA_SCHEMA = "haauthorize"
TUYA_RESPONSE_CODE = "code"
TUYA_RESPONSE_MSG = "msg"
TUYA_RESPONSE_QR_CODE = "qrcode"
TUYA_RESPONSE_RESULT = "result"
TUYA_RESPONSE_SUCCESS = "success"
