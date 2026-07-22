"""Config flow for Tuya shadow meter."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import callback

from .const import (
    CONF_CLOUD_ACCESS_ID,
    CONF_CLOUD_ACCESS_SECRET,
    CONF_CLOUD_APP_USER_ID,
    CONF_CLOUD_REGION,
    DOMAIN,
)
from .coordinator import TuyaOpenApiClient


class TuyaShadowMeterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya shadow meter."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> TuyaShadowMeterOptionsFlow:
        """Create the options flow."""
        return TuyaShadowMeterOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(_validate_openapi, user_input)
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "cannot_connect"
            else:
                device_id = user_input[CONF_DEVICE_ID]
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Tuya Shadow Meter", data=user_input
                )
        else:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=_openapi_schema(user_input),
            errors=errors,
        )


class TuyaShadowMeterOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Tuya shadow meter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage OpenAPI shadow options."""
        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(_validate_openapi, user_input)
            except Exception:  # pylint: disable=broad-except
                return self.async_show_form(
                    step_id="init",
                    data_schema=_openapi_schema(user_input),
                    errors={"base": "cannot_connect"},
                )
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_openapi_schema(defaults),
        )


def _openapi_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return OpenAPI credentials schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, "")
            ): str,
            vol.Required(
                CONF_CLOUD_ACCESS_ID,
                default=defaults.get(CONF_CLOUD_ACCESS_ID, ""),
            ): str,
            vol.Required(
                CONF_CLOUD_ACCESS_SECRET,
                default=defaults.get(CONF_CLOUD_ACCESS_SECRET, ""),
            ): str,
            vol.Required(
                CONF_CLOUD_APP_USER_ID,
                default=defaults.get(CONF_CLOUD_APP_USER_ID, ""),
            ): str,
            vol.Required(
                CONF_CLOUD_REGION,
                default=defaults.get(CONF_CLOUD_REGION, "cn"),
            ): vol.In(["cn", "us", "eu", "in"]),
        }
    )


def _validate_openapi(data: dict[str, Any]) -> None:
    """Validate OpenAPI credentials by reading the target device shadow."""
    client = TuyaOpenApiClient.from_entry_data(data)
    if client is None:
        raise ValueError("missing OpenAPI credentials")
    properties = client.get_shadow_properties(data[CONF_DEVICE_ID])
    if not properties:
        raise ValueError("empty shadow properties")
