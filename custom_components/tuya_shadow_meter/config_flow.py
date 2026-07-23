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
    CONF_DEVICE_IDS,
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
from .coordinator import TuyaCloudCoordinator

ACTION_MANAGE_DEVICES = "manage_devices"
ACTION_REAUTHORIZE = "reauthorize"
CONF_ACTION = "action"

QR_SCAN_HELP_LINES = (
    "Use the Smart Life or Tuya app to scan this QR code.",
    "After scanning, return here and submit this step.",
    "If the QR code expires, submit again to generate a new one.",
)
USER_CODE_HELP_LINES = (
    (
        "Enter the User Code from the Smart Life or Tuya app. It is usually under "
        "Me/Profile > Settings > Account and Security > User Code."
    ),
    (
        "⚠️ Initial sensor values may be unavailable for about one minute. Opening the "
        "device page in the Tuya app can trigger faster updates."
    ),
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
            data_schema=_user_code_schema(user_input.get(CONF_USER_CODE, "")),
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

    async def async_step_reauth(
        self, entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Start QR-code reauthentication."""
        self._user_code = entry_data[CONF_USER_CODE]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the User Code before reauth QR generation."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            success, response = await self._async_get_qr_code(
                user_input[CONF_USER_CODE].strip()
            )
            if success:
                return await self.async_step_reauth_scan()

            errors["base"] = "login_error"
            placeholders.update(
                {
                    TUYA_RESPONSE_MSG: response.get(TUYA_RESPONSE_MSG, "Unknown error"),
                    TUYA_RESPONSE_CODE: response.get(TUYA_RESPONSE_CODE, "0"),
                }
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_user_code_schema(self._user_code),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reauth_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the QR-code scan step for reauth."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_scan",
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
                step_id="reauth_scan",
                errors={"base": "login_error"},
                data_schema=_qr_schema(self._qr_code),
                description_placeholders={
                    TUYA_RESPONSE_MSG: info.get(TUYA_RESPONSE_MSG, "Unknown error"),
                    TUYA_RESPONSE_CODE: info.get(TUYA_RESPONSE_CODE, "0"),
                },
            )

        await self.async_set_unique_id(info["uid"])
        self._abort_if_unique_id_mismatch()
        return self.async_update_reload_and_abort(
            self._get_reauth_entry(),
            data_updates=_entry_data_from_login(self._user_code, info),
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
        self._login_control = LoginControl()
        self._user_code = config_entry.data.get(CONF_USER_CODE, "")
        self._qr_code = ""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose what to configure."""
        if user_input is not None:
            action = user_input[CONF_ACTION]
            if action == ACTION_MANAGE_DEVICES:
                return await self.async_step_devices()
            if action == ACTION_REAUTHORIZE:
                return await self.async_step_reauth_confirm()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACTION): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {
                                    "value": ACTION_MANAGE_DEVICES,
                                    "label": "Manage devices",
                                },
                                {
                                    "value": ACTION_REAUTHORIZE,
                                    "label": "Re-scan authorization",
                                },
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage enabled supported devices."""
        errors = {}
        devices = await self._async_get_supported_devices()
        if not devices:
            if user_input is not None:
                return self.async_create_entry(title="", data=dict(self._entry.options))
            return self.async_show_form(
                step_id="devices",
                data_schema=vol.Schema(
                    {
                        vol.Optional("no_more_devices"): selector.ConstantSelector(
                            selector.ConstantSelectorConfig(
                                label="No more device can be added.",
                                value="",
                            )
                        )
                    }
                ),
            )

        if user_input is not None:
            if user_input[CONF_DEVICE_IDS]:
                return self.async_create_entry(
                    title="",
                    data={
                        **self._entry.options,
                        CONF_DEVICE_IDS: user_input[CONF_DEVICE_IDS],
                    },
                )
            errors["base"] = "no_devices_selected"

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_IDS,
                        default=self._enabled_device_ids(devices),
                    ): _device_selector(devices),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the User Code before manual reauthorization."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            success, response = await self._async_get_qr_code(
                user_input[CONF_USER_CODE].strip()
            )
            if success:
                return await self.async_step_reauth_scan()

            errors["base"] = "login_error"
            placeholders.update(
                {
                    TUYA_RESPONSE_MSG: response.get(TUYA_RESPONSE_MSG, "Unknown error"),
                    TUYA_RESPONSE_CODE: response.get(TUYA_RESPONSE_CODE, "0"),
                }
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_user_code_schema(self._user_code),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reauth_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual reauthorization QR scan."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_scan",
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
                step_id="reauth_scan",
                errors={"base": "login_error"},
                data_schema=_qr_schema(self._qr_code),
                description_placeholders={
                    TUYA_RESPONSE_MSG: info.get(TUYA_RESPONSE_MSG, "Unknown error"),
                    TUYA_RESPONSE_CODE: info.get(TUYA_RESPONSE_CODE, "0"),
                },
            )

        if self._entry.unique_id is not None and info["uid"] != self._entry.unique_id:
            return self.async_abort(reason="wrong_account")

        self.hass.config_entries.async_update_entry(
            self._entry,
            data={
                **self._entry.data,
                **_entry_data_from_login(self._user_code, info),
            },
        )
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(self._entry.entry_id)
        )
        return self.async_create_entry(title="", data=dict(self._entry.options))

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

    async def _async_get_supported_devices(self) -> dict[str, Any]:
        """Return supported devices currently visible to the loaded integration."""
        coordinator: TuyaCloudCoordinator | None = self.hass.data.get(DOMAIN, {}).get(
            self._entry.entry_id
        )
        if coordinator is None:
            return {}
        return await coordinator.hub.async_get_supported_devices()

    def _enabled_device_ids(self, devices: dict[str, Any]) -> list[str]:
        """Return enabled devices, defaulting to devices loaded by this entry."""
        device_ids = self._entry.options.get(CONF_DEVICE_IDS)
        if device_ids is not None:
            return list(device_ids)
        coordinator: TuyaCloudCoordinator | None = self.hass.data.get(DOMAIN, {}).get(
            self._entry.entry_id
        )
        if coordinator is not None:
            return list(coordinator.hub.devices)
        return list(devices)


def _qr_schema(qr_code: str) -> vol.Schema:
    """Return a QR-code selector schema."""
    return vol.Schema(
        {
            **_constant_text_fields("qr_instruction", QR_SCAN_HELP_LINES),
            vol.Optional("qr_code"): selector.QrCodeSelector(
                config=selector.QrCodeSelectorConfig(
                    data=f"tuyaSmart--qrLogin?token={qr_code}",
                    scale=5,
                    error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                )
            )
        }
    )


def _user_code_schema(user_code: str) -> vol.Schema:
    """Return a User Code form schema with visible help text."""
    return vol.Schema(
        {
            **_constant_text_fields("user_code_instruction", USER_CODE_HELP_LINES),
            vol.Required(CONF_USER_CODE, default=user_code): str,
        }
    )


def _constant_text_fields(prefix: str, lines: tuple[str, ...]) -> dict[Any, Any]:
    """Return visible constant text fields, one field per rendered line."""
    return {
        vol.Optional(f"{prefix}_{index}"): selector.ConstantSelector(
            selector.ConstantSelectorConfig(label=line, value="")
        )
        for index, line in enumerate(lines, start=1)
    }


def _device_selector(devices: dict[str, Any]) -> selector.SelectSelector:
    """Return a selector for Tuya devices."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {
                    "value": device_id,
                    "label": _device_label(device),
                }
                for device_id, device in devices.items()
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
            multiple=True,
        )
    )


def _device_label(device: Any) -> str:
    """Return a readable device label."""
    name = getattr(device, "name", "") or device.id
    product_name = getattr(device, "product_name", "") or ""
    if product_name:
        return f"{name} ({product_name})"
    return name


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
