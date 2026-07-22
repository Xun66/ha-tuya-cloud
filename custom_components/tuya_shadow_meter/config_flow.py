"""Config flow for Tuya shadow meter."""

from __future__ import annotations

from typing import Any

from tuya_sharing import LoginControl, Manager
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CLOUD_ACCESS_ID,
    CONF_CLOUD_ACCESS_SECRET,
    CONF_CLOUD_APP_USER_ID,
    CONF_CLOUD_REGION,
    CONF_ENDPOINT,
    CONF_TERMINAL_ID,
    CONF_TOKEN_INFO,
    CONF_USER_CODE,
    DOMAIN,
    TUYA_CLIENT_ID,
    TUYA_RESPONSE_CODE,
    TUYA_RESPONSE_MSG,
    TUYA_RESPONSE_QR_CODE,
    TUYA_RESPONSE_RESULT,
    TUYA_RESPONSE_SUCCESS,
    TUYA_SCHEMA,
)
from .coordinator import _is_supported_device, update_minimal_device_cache


class TuyaShadowMeterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya shadow meter."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> TuyaShadowMeterOptionsFlow:
        """Create the options flow."""
        return TuyaShadowMeterOptionsFlow(config_entry)

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._login_control = LoginControl()
        self._qr_code = ""
        self._user_code = ""
        self._device_id = ""
        self._cloud_data: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            self._user_code = user_input[CONF_USER_CODE]
            self._device_id = user_input.get(CONF_DEVICE_ID, "")
            self._cloud_data = {
                CONF_CLOUD_ACCESS_ID: user_input.get(CONF_CLOUD_ACCESS_ID, ""),
                CONF_CLOUD_ACCESS_SECRET: user_input.get(
                    CONF_CLOUD_ACCESS_SECRET, ""
                ),
                CONF_CLOUD_APP_USER_ID: user_input.get(CONF_CLOUD_APP_USER_ID, ""),
                CONF_CLOUD_REGION: user_input.get(CONF_CLOUD_REGION, "cn"),
            }
            success, response = await self._async_get_qr_code(self._user_code)
            if success:
                return await self.async_step_scan()

            errors["base"] = "login_error"
            placeholders = {
                TUYA_RESPONSE_MSG: response.get(TUYA_RESPONSE_MSG, "Unknown error"),
                TUYA_RESPONSE_CODE: response.get(TUYA_RESPONSE_CODE, "0"),
            }
        else:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USER_CODE, default=user_input.get(CONF_USER_CODE, "")
                    ): str,
                    vol.Optional(
                        CONF_DEVICE_ID, default=user_input.get(CONF_DEVICE_ID, "")
                    ): str,
                    vol.Optional(
                        CONF_CLOUD_ACCESS_ID,
                        default=user_input.get(CONF_CLOUD_ACCESS_ID, ""),
                    ): str,
                    vol.Optional(
                        CONF_CLOUD_ACCESS_SECRET,
                        default=user_input.get(CONF_CLOUD_ACCESS_SECRET, ""),
                    ): str,
                    vol.Optional(
                        CONF_CLOUD_APP_USER_ID,
                        default=user_input.get(CONF_CLOUD_APP_USER_ID, ""),
                    ): str,
                    vol.Optional(
                        CONF_CLOUD_REGION,
                        default=user_input.get(CONF_CLOUD_REGION, "cn"),
                    ): vol.In(["cn", "us", "eu", "in"]),
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle QR-code scanning."""
        if user_input is None:
            return self.async_show_form(
                step_id="scan",
                data_schema=vol.Schema(
                    {
                        vol.Optional("QR"): selector.QrCodeSelector(
                            config=selector.QrCodeSelectorConfig(
                                data=f"tuyaSmart--qrLogin?token={self._qr_code}",
                                scale=5,
                                error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                            )
                        )
                    }
                ),
            )

        success, info = await self.hass.async_add_executor_job(
            self._login_control.login_result,
            self._qr_code,
            TUYA_CLIENT_ID,
            self._user_code,
        )
        if not success:
            await self._async_get_qr_code(self._user_code)
            return self.async_show_form(
                step_id="scan",
                errors={"base": "login_error"},
                data_schema=vol.Schema(
                    {
                        vol.Optional("QR"): selector.QrCodeSelector(
                            config=selector.QrCodeSelectorConfig(
                                data=f"tuyaSmart--qrLogin?token={self._qr_code}",
                                scale=5,
                                error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                            )
                        )
                    }
                ),
                description_placeholders={
                    TUYA_RESPONSE_MSG: info.get(TUYA_RESPONSE_MSG, "Unknown error"),
                    TUYA_RESPONSE_CODE: info.get(TUYA_RESPONSE_CODE, "0"),
                },
            )

        entry_data = {
            CONF_USER_CODE: self._user_code,
            CONF_TOKEN_INFO: {
                "t": info["t"],
                "uid": info["uid"],
                "expire_time": info["expire_time"],
                "access_token": info["access_token"],
                "refresh_token": info["refresh_token"],
            },
            CONF_TERMINAL_ID: info[CONF_TERMINAL_ID],
            CONF_ENDPOINT: info[CONF_ENDPOINT],
        }
        entry_data.update(
            {
                key: value
                for key, value in getattr(self, "_cloud_data", {}).items()
                if value
            }
        )

        try:
            device_id = await self.hass.async_add_executor_job(
                self._find_supported_device_id, entry_data
            )
        except Exception:  # pylint: disable=broad-except
            return self.async_show_form(
                step_id="scan",
                errors={"base": "cannot_connect"},
                data_schema=vol.Schema({}),
            )

        if device_id is None:
            return self.async_show_form(
                step_id="scan",
                errors={"base": "unsupported_device"},
                data_schema=vol.Schema({}),
            )

        entry_data[CONF_DEVICE_ID] = device_id
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title="Tuya Shadow Meter", data=entry_data)

    async def _async_get_qr_code(self, user_code: str) -> tuple[bool, dict[str, Any]]:
        """Get a QR code from Tuya."""
        response = await self.hass.async_add_executor_job(
            self._login_control.qr_code,
            TUYA_CLIENT_ID,
            TUYA_SCHEMA,
            user_code,
        )
        if success := response.get(TUYA_RESPONSE_SUCCESS, False):
            self._qr_code = response[TUYA_RESPONSE_RESULT][TUYA_RESPONSE_QR_CODE]
        return success, response

    def _find_supported_device_id(self, entry_data: dict[str, Any]) -> str | None:
        """Find the configured or first supported device."""
        manager = Manager(
            TUYA_CLIENT_ID,
            entry_data[CONF_USER_CODE],
            entry_data[CONF_TERMINAL_ID],
            entry_data[CONF_ENDPOINT],
            entry_data[CONF_TOKEN_INFO],
        )
        update_minimal_device_cache(manager)

        if self._device_id:
            device = manager.device_map.get(self._device_id)
            return device.id if device and _is_supported_device(device) else None

        for device in manager.device_map.values():
            if _is_supported_device(device):
                return device.id

        return None


class TuyaShadowMeterOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Tuya shadow meter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage OpenAPI shadow options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CLOUD_ACCESS_ID,
                        default=defaults.get(CONF_CLOUD_ACCESS_ID, ""),
                    ): str,
                    vol.Optional(
                        CONF_CLOUD_ACCESS_SECRET,
                        default=defaults.get(CONF_CLOUD_ACCESS_SECRET, ""),
                    ): str,
                    vol.Optional(
                        CONF_CLOUD_APP_USER_ID,
                        default=defaults.get(CONF_CLOUD_APP_USER_ID, ""),
                    ): str,
                    vol.Optional(
                        CONF_CLOUD_REGION,
                        default=defaults.get(CONF_CLOUD_REGION, "cn"),
                    ): vol.In(["cn", "us", "eu", "in"]),
                }
            ),
        )
