"""Config flow for Tuya Cloud."""

from __future__ import annotations

from typing import Any

from tuya_sharing import LoginControl
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
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


class HATuyaCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya Cloud."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._login_control = LoginControl()
        self._user_code = ""
        self._qr_code = ""

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HATuyaCloudOptionsFlow:
        """Create the options flow."""
        return HATuyaCloudOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user-code step."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            success, response = await self._async_get_qr_code(
                user_input[CONF_USER_CODE].strip()
            )
            if success:
                return await self.async_step_scan()

            errors["base"] = "login_error"
            placeholders.update(
                {
                    TUYA_RESPONSE_MSG: response.get(TUYA_RESPONSE_MSG, "Unknown error"),
                    TUYA_RESPONSE_CODE: response.get(TUYA_RESPONSE_CODE, "0"),
                }
            )
        else:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USER_CODE,
                        default=user_input.get(CONF_USER_CODE, ""),
                    ): str,
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the QR-code scan step."""
        if user_input is None:
            return self.async_show_form(
                step_id="scan",
                data_schema=_qr_schema(self._qr_code),
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
                data_schema=_qr_schema(self._qr_code),
                description_placeholders={
                    TUYA_RESPONSE_MSG: info.get(TUYA_RESPONSE_MSG, "Unknown error"),
                    TUYA_RESPONSE_CODE: info.get(TUYA_RESPONSE_CODE, "0"),
                },
            )

        await self.async_set_unique_id(info["uid"])
        self._abort_if_unique_id_configured()
        entry_data = _entry_data_from_login(self._user_code, info)
        return self.async_create_entry(
            title=info.get("username") or "Tuya Cloud",
            data=entry_data,
        )

    async def _async_get_qr_code(
        self, user_code: str
    ) -> tuple[bool, dict[str, Any]]:
        """Request a QR-code login token."""
        response = await self.hass.async_add_executor_job(
            self._login_control.qr_code,
            TUYA_CLIENT_ID,
            TUYA_SCHEMA,
            user_code,
        )
        success = response.get(TUYA_RESPONSE_SUCCESS, False)
        if success:
            self._user_code = user_code
            self._qr_code = response[TUYA_RESPONSE_RESULT][TUYA_RESPONSE_QR_CODE]
        return success, response


class HATuyaCloudOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Tuya Cloud."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show guidance for this MQ-only integration."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )


def _qr_schema(qr_code: str) -> vol.Schema:
    """Return a QR-code selector schema."""
    return vol.Schema(
        {
            vol.Optional("QR"): selector.QrCodeSelector(
                config=selector.QrCodeSelectorConfig(
                    data=f"tuyaSmart--qrLogin?token={qr_code}",
                    scale=5,
                    error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                )
            )
        }
    )


def _entry_data_from_login(user_code: str, info: dict[str, Any]) -> dict[str, Any]:
    """Return config entry data from a successful Tuya QR login."""
    return {
        CONF_USER_CODE: user_code,
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
